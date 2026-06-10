from __future__ import annotations

import importlib.util
import os
import sys
import time
from pathlib import Path
from typing import Any

from .image_generation import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageGenerator,
    ImageStyle,
    TransparencyMode,
)


class PixAIImageGenerator(ImageGenerator):
    """PixelLab/PixAI backend adapter for scene asset generation."""

    def __init__(self, output_dir: Path, script_path: str | Path | None = None, timeout: int | None = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.script_path = Path(script_path or os.getenv("PIXAI_SCRIPT_PATH") or self.default_script_path())
        if not self.script_path.exists():
            raise FileNotFoundError(f"PixAI script not found: {self.script_path}")
        self.module = self._load_script(self.script_path)
        if not hasattr(self.module, "PixelLabV2Client"):
            raise ImportError(f"PixAI v2 client not found in script: {self.script_path}")
        client_timeout = timeout or int(os.getenv("PIXAI_TIMEOUT", "120"))
        self.client = self.module.PixelLabV2Client(timeout=client_timeout)

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        started = time.perf_counter()
        requested_size = (int(request.size[0]), int(request.size[1]))
        generation_size = _pixen_generation_size(requested_size)
        output_name = f"pixai_{_safe_filename(request.metadata.get('target_id') or 'asset')}_{request.seed or 0}.png"
        output_path = self.output_dir / output_name
        try:
            result = self.client.create_pixen(
                description=self._prompt_for_pixai(request),
                width=generation_size[0],
                height=generation_size[1],
                no_background=request.transparency == TransparencyMode.REQUIRED,
                outline=self._outline_for(request),
                detail=self._detail_for(request),
                view="high top-down",
                direction="south",
            )
            image = result.image.convert("RGBA")
            if image.size != requested_size:
                resized = _resize_pixel_art(image, requested_size)
                image.close()
                image = resized
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, "PNG")
            image.close()
            return ImageGenerationResponse(
                success=True,
                image_path=str(output_path),
                model=self.get_model_name(),
                actual_seed=request.seed,
                generation_time=time.perf_counter() - started,
                metadata={
                    "script_path": str(self.script_path),
                    "api": "create_pixen",
                    "requested_size": list(requested_size),
                    "generation_size": list(generation_size),
                    "resized": generation_size != requested_size,
                    "usage": getattr(result, "usage", {}),
                },
            )
        except SystemExit as exc:
            return ImageGenerationResponse(success=False, error=f"PixAI exited: {exc}")
        except Exception as exc:
            return ImageGenerationResponse(success=False, error=f"PixAI failed: {exc}")

    def get_model_name(self) -> str:
        return "pixai/pixellab-v2-pixen"

    def supports_style(self, style: ImageStyle) -> bool:
        return style == ImageStyle.PIXEL_ART

    def _prompt_for_pixai(self, request: ImageGenerationRequest) -> str:
        lines = [
            request.prompt,
            "",
            "PixelLab generation constraints:",
            "- 16-bit RPG pixel art.",
            "- Crisp hard pixel edges, readable silhouette, no blur.",
            "- No watermark, no signature, no UI frame.",
        ]
        if request.transparency == TransparencyMode.REQUIRED:
            lines.append("- Return a PNG with true alpha transparency outside the asset.")
        else:
            lines.append("- Return an opaque PNG and fill the full canvas with pixel art.")
        negative_prompt = _negative_prompt_for_pixai(request)
        if negative_prompt:
            lines.extend(
                [
                    "",
                    "Avoid these elements:",
                    f"- {negative_prompt}",
                ]
            )
        return "\n".join(lines)

    def _outline_for(self, request: ImageGenerationRequest) -> str:
        category = str(request.metadata.get("category") or "")
        if category == "terrain_tile":
            return "lineless"
        if request.transparency == TransparencyMode.OPAQUE:
            return "selective outline"
        return "single color black outline"

    def _detail_for(self, request: ImageGenerationRequest) -> str:
        return "highly detailed" if max(request.size) >= 128 else "medium detail"

    @staticmethod
    def default_script_path() -> Path:
        return Path(__file__).resolve().parents[3] / "tools" / "ai" / "pixellab_v2_client.py"

    def _load_script(self, script_path: Path):
        spec = importlib.util.spec_from_file_location(f"tools_ai_{script_path.stem}", script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load PixAI script: {script_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(spec.name, None)
            raise
        return module


def _pixen_generation_size(size: tuple[int, int]) -> tuple[int, int]:
    """Return a PixelLab v2 legal size, preserving aspect ratio when clamped."""
    width = max(1, int(size[0]))
    height = max(1, int(size[1]))
    scale = min(512 / width, 512 / height, 1.0)
    scaled_width = _round_to_multiple(width * scale, 4)
    scaled_height = _round_to_multiple(height * scale, 4)
    return (
        min(512, max(32, scaled_width)),
        min(512, max(32, scaled_height)),
    )


def _round_to_multiple(value: float, multiple: int) -> int:
    return max(multiple, int(round(value / multiple)) * multiple)


def _resize_pixel_art(image: Any, size: tuple[int, int]) -> Any:
    try:
        from PIL import Image

        resampling = Image.Resampling.NEAREST
    except AttributeError:
        from PIL import Image

        resampling = Image.NEAREST
    return image.resize(size, resampling)


def _safe_filename(value: object) -> str:
    text = str(value)
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in text)
    return safe or "asset"


def _negative_prompt_for_pixai(request: ImageGenerationRequest) -> str:
    if not request.negative_prompt:
        return ""
    parts = [part.strip() for part in request.negative_prompt.split(",") if part.strip()]
    if request.transparency == TransparencyMode.REQUIRED:
        parts = [
            part for part in parts
            if part.lower() not in _PIXAI_ALPHA_REDUNDANT_NEGATIVES
        ]
    return ", ".join(parts)


_PIXAI_ALPHA_REDUNDANT_NEGATIVES = {
    "background",
    "white background",
    "black background",
    "gray background",
    "solid background",
    "checkerboard background",
    "fake transparency",
    "separate background",
}
