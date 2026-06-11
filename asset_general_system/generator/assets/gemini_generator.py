"""
Gemini 图像生成后端。

复用上级 tools/ai/gen_with_gemini.py 的实现，使用 gemini-3.1-flash-image-preview 模型。
支持 bobdong.cn 代理。
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests

from .image_generation import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageGenerator,
    ImageStyle,
    TransparencyMode,
)

# 导入上级 ai_config（如果存在）
_AI_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "tools" / "ai"
if _AI_CONFIG_PATH.exists() and str(_AI_CONFIG_PATH) not in sys.path:
    sys.path.insert(0, str(_AI_CONFIG_PATH))

try:
    from ai_config import get_service_config
    _HAS_AI_CONFIG = True
except ImportError:
    _HAS_AI_CONFIG = False

    def get_service_config(service_name, env_prefix=None, default_host=None, default_model=None):
        """Fallback config loader."""
        api_key = os.getenv(f"{env_prefix}_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(f"{env_prefix}_API_KEY or GEMINI_API_KEY 环境变量未设置")
        return {
            "api_key": api_key,
            "api_host": os.getenv(f"{env_prefix}_API_HOST", default_host or "generativelanguage.googleapis.com"),
            "model": os.getenv(f"{env_prefix}_MODEL", default_model or "gemini-3.1-flash-image-preview"),
        }


class GeminiImageGenerator(ImageGenerator):
    """
    Gemini 图像生成器。

    使用 gemini-3.1-flash-image-preview 模型。
    支持 bobdong.cn 代理（通过 ai_config.py 配置）。

    环境变量：
    - GEMINI_IMAGE_API_KEY 或 GEMINI_API_KEY: API 密钥
    - GEMINI_IMAGE_API_HOST（可选）: API 代理地址，默认 bobdong.cn
    - GEMINI_IMAGE_MODEL（可选）: 模型名称，默认 gemini-3.1-flash-image-preview
    """

    def __init__(
        self,
        output_dir: Path,
        config: dict | None = None,
    ):
        """
        Args:
            output_dir: 输出目录
            config: 配置字典（可选），包含 api_key, api_host, model
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if config is None:
            config = get_service_config(
                "gemini_image",
                env_prefix="GEMINI_IMAGE",
                default_host="bobdong.cn",
                default_model="gemini-3.1-flash-image-preview",
            )

        self.config = config
        self.max_attempts = int(os.getenv("GEMINI_IMAGE_MAX_ATTEMPTS", "4"))
        self.retry_delay = float(os.getenv("GEMINI_IMAGE_RETRY_DELAY", "2.0"))
        self.timeout = float(os.getenv("GEMINI_IMAGE_TIMEOUT", "300"))
        self.session = requests.Session()
        # The sandbox may inject HTTP_PROXY/HTTPS_PROXY to block network access.
        # AI service routing should come from tools/ai/config.local.json or
        # GEMINI_IMAGE_* settings, not ambient process proxy variables.
        self.session.trust_env = False

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """
        使用 Gemini 生成图像。

        Args:
            request: 生成请求

        Returns:
            生成响应
        """
        # 构建完整 prompt
        full_prompt = self._build_prompt(request)

        # 构建 API endpoint
        endpoint = (
            f"https://{self.config['api_host']}/v1beta/models/"
            f"{self.config['model']}:generateContent?key={self.config['api_key']}"
        )

        # 构建图像配置
        image_config = {"imageSize": "1K"}  # 默认 1K
        aspect_ratio = self._get_aspect_ratio(request.size)
        if aspect_ratio:
            image_config["aspectRatio"] = aspect_ratio

        # 构建请求 payload
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": image_config,
            },
        }

        # 重试机制
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                resp = self.session.post(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    timeout=self.timeout,
                )

                if resp.status_code != 200:
                    last_error = self._redact_sensitive(f"HTTP {resp.status_code}: {resp.text[:500]}")
                    if attempt < self.max_attempts:
                        time.sleep(self.retry_delay * attempt)
                        continue
                    return ImageGenerationResponse(
                        success=False,
                        error=f"Gemini API 失败: {last_error}",
                    )

                # 解析响应
                data = resp.json()
                parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []

                for part in parts:
                    inline = part.get("inlineData") or part.get("inline_data")
                    if inline:
                        # 保存图像
                        output_filename = f"gemini_{int(time.time())}_{request.seed or 0}.png"
                        output_path = self.output_dir / output_filename

                        img_data = base64.b64decode(inline.get("data", ""))
                        output_path.write_bytes(img_data)

                        output_path = self._normalize_output(output_path, request.size, request.style, request.transparency)

                        return ImageGenerationResponse(
                            success=True,
                            image_path=str(output_path),
                            model=self.config['model'],
                            actual_seed=request.seed,
                        )

                # 没有图像
                return ImageGenerationResponse(
                    success=False,
                    error=self._redact_sensitive(f"Gemini 未返回图像: {json.dumps(data, ensure_ascii=False)[:500]}"),
                )

            except requests.exceptions.RequestException as e:
                last_error = self._redact_sensitive(str(e))
                if attempt < self.max_attempts:
                    time.sleep(self.retry_delay * attempt)
                    continue

        return ImageGenerationResponse(
            success=False,
            error=self._redact_sensitive(f"Gemini 请求失败（{self.max_attempts} 次尝试）: {last_error}"),
        )

    def _redact_sensitive(self, text: str) -> str:
        """Remove API credentials from errors before they are persisted."""
        redacted = text.replace(str(self.config.get("api_key", "")), "[REDACTED]") if self.config.get("api_key") else text
        redacted = re.sub(r"([?&]key=)[^&\s)]+", r"\1[REDACTED]", redacted)
        return redacted

    def _build_prompt(self, request: ImageGenerationRequest) -> str:
        """构建 Gemini 友好的 prompt。"""
        parts = [
            "Follow the asset contract exactly. Generate only the requested image asset.",
            request.prompt.strip(),
        ]

        # 风格描述
        if request.style == ImageStyle.PIXEL_ART:
            parts.append(
                "Pixel-art requirement: 16-bit RPG pixel art, crisp hard pixel edges, clean limited palette, readable silhouette at final game size, no blur."
            )
        elif request.style == ImageStyle.HAND_DRAWN:
            parts.append("Style requirement: hand-drawn 2D game asset with clean readable silhouette.")
        elif request.style == ImageStyle.LOW_POLY:
            parts.append("Style requirement: low-poly 3D style.")

        # 透明背景
        if request.transparency == TransparencyMode.REQUIRED:
            target_id = str((request.metadata or {}).get("target_id") or "sprite")
            parts.append(
                "Transparency workflow: output the object on a perfectly flat solid #ff00ff chroma-key field so the pipeline can remove that field after generation."
            )
            parts.append(
                "The #ff00ff field is a temporary technical mask only, not part of the object. It must be perfectly uniform edge-to-edge wherever there is no object."
            )
            parts.append(
                f"The asset object for {target_id} must occupy roughly 70-85% of the useful canvas, centered, not a small icon floating in empty space."
            )
            parts.append(
                "Do not use #ff00ff anywhere inside the object. Do not use checkerboard, transparency grid, gray squares, white background, colored rectangle, floor plane, shadow backdrop, lighting variation, or any other background."
            )
            parts.append("Generate an isolated object sprite only. Contact glow/shadow is allowed only if it belongs to the object and does not require a background plane.")
        elif request.transparency == TransparencyMode.OPAQUE:
            parts.append("Output should be opaque and fill the requested image area.")

        # tile 对齐（用于 tileset）
        if request.tile_aligned and request.tile_size:
            parts.append(
                f"Respect the {request.tile_size[0]}x{request.tile_size[1]} px tile grid and keep the sprite aligned to that grid."
            )

        # 通用约束
        parts.append(f"Requested canvas/aspect target: {request.size[0]}x{request.size[1]} px.")
        parts.append("Clean production game asset. No watermark, no signature, no UI frame.")
        if request.negative_prompt:
            parts.append("Strictly avoid: " + request.negative_prompt)

        return "\n\n".join(parts)

    def _get_aspect_ratio(self, size: tuple[int, int]) -> str:
        """
        把尺寸转换为 Gemini 支持的 aspect ratio。

        Gemini 支持：1:1, 3:4, 4:3, 9:16, 16:9
        """
        width, height = size

        # 计算比例
        ratio = width / height

        if 0.95 <= ratio <= 1.05:
            return "1:1"
        elif 0.7 <= ratio < 0.95:
            return "3:4"
        elif 1.05 < ratio <= 1.4:
            return "4:3"
        elif ratio < 0.7:
            return "9:16"
        else:
            return "16:9"

    def _normalize_output(
        self,
        image_path: Path,
        target_size: tuple[int, int],
        style: ImageStyle | None = None,
        transparency: TransparencyMode = TransparencyMode.REQUIRED,
    ) -> Path:
        """
        后处理：确保透明背景要求并缩放到目标尺寸。

        Gemini 通常返回 1K 图。无论是否要求透明，都必须归一到
        scene art_request 里的 source_canvas 尺寸。
        """
        try:
            from PIL import Image
        except ImportError:
            # 没有 PIL，跳过后处理
            return image_path

        with Image.open(image_path) as source:
            img = source.convert("RGBA")

        if transparency == TransparencyMode.REQUIRED:
            img = self._remove_chroma_key(img, (255, 0, 255))
            img = self._remove_chroma_background_panels(img)
            img = self._remove_background(img)
            img = self._remove_checkerboard_background(img)
            img = self._clear_transparent_rgb(img)

        # 缩放到目标尺寸
        if img.size != target_size:
            resample = Image.NEAREST if style == ImageStyle.PIXEL_ART else Image.LANCZOS
            resized = img.resize(target_size, resample)
            img.close()
            img = resized
            if transparency == TransparencyMode.REQUIRED:
                img = self._remove_chroma_background_panels(img)
                img = self._clear_transparent_rgb(img)

        # 保存
        img.save(image_path, "PNG")
        img.close()
        return image_path

    def _remove_chroma_key(self, img, key_rgb: tuple[int, int, int], threshold: int = 70):
        from PIL import Image
        import numpy as np

        if img.mode != "RGBA":
            img = img.convert("RGBA")
        data = np.array(img)
        key = np.array(key_rgb, dtype=np.int16)
        diff = np.abs(data[:, :, :3].astype(np.int16) - key)
        distance = np.sum(diff, axis=2)
        mask = distance < threshold
        data[mask] = [0, 0, 0, 0]
        return Image.fromarray(data, mode="RGBA")

    def _remove_chroma_background_panels(self, img):
        """Remove large generated magenta/purple chroma panels that are not exact #ff00ff."""
        from collections import deque

        from PIL import Image
        import numpy as np

        if img.mode != "RGBA":
            img = img.convert("RGBA")
        data = np.array(img)
        h, w = data.shape[:2]
        if h == 0 or w == 0:
            return img

        rgb = data[:, :, :3].astype(np.int16)
        alpha = data[:, :, 3]
        r = rgb[:, :, 0]
        g = rgb[:, :, 1]
        b = rgb[:, :, 2]

        visible = alpha > 0
        key_seed = (
            visible
            & (r >= 145)
            & (b >= 145)
            & (g <= 135)
            & ((r - g) >= 45)
            & ((b - g) >= 35)
        )
        key_soft = (
            visible
            & (r >= 115)
            & (b >= 110)
            & (g <= 165)
            & ((r - g) >= 25)
            & ((b - g) >= 22)
        )
        if not key_seed.any():
            return img

        visited = np.zeros((h, w), dtype=bool)
        remove = np.zeros((h, w), dtype=bool)
        canvas_area = h * w
        min_panel_area = max(96, int(canvas_area * 0.006))
        min_seed_area = max(32, int(canvas_area * 0.0015))

        for start_y, start_x in np.argwhere(key_soft):
            if visited[start_y, start_x]:
                continue
            queue = deque([(int(start_y), int(start_x))])
            visited[start_y, start_x] = True
            coords: list[tuple[int, int]] = []
            seed_count = 0

            while queue:
                y, x = queue.popleft()
                coords.append((y, x))
                if key_seed[y, x]:
                    seed_count += 1
                for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and key_soft[ny, nx]:
                        visited[ny, nx] = True
                        queue.append((ny, nx))

            if not coords or seed_count < min_seed_area:
                continue
            area = len(coords)
            if area < min_panel_area:
                continue

            ys = np.fromiter((p[0] for p in coords), dtype=np.int32, count=area)
            xs = np.fromiter((p[1] for p in coords), dtype=np.int32, count=area)
            bbox_area = int((ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1))
            fill_ratio = area / float(max(1, bbox_area))
            seed_ratio = seed_count / float(area)
            colors = rgb[ys, xs, :]
            color_std = float(colors.std(axis=0).max())

            # Generated backdrop panels are large, contiguous, fairly uniform,
            # and usually rectangular with object-shaped holes in them.
            if fill_ratio >= 0.16 and seed_ratio >= 0.45 and color_std <= 55.0:
                remove[ys, xs] = True

        if not remove.any():
            return img

        remove = self._expand_mask(remove, key_soft, iterations=1)
        data[remove] = [0, 0, 0, 0]
        return Image.fromarray(data, mode="RGBA")

    def _expand_mask(self, mask, allowed, iterations: int = 1):
        import numpy as np

        expanded = mask
        for _ in range(iterations):
            grown = expanded.copy()
            grown[1:, :] |= expanded[:-1, :]
            grown[:-1, :] |= expanded[1:, :]
            grown[:, 1:] |= expanded[:, :-1]
            grown[:, :-1] |= expanded[:, 1:]
            expanded = grown & allowed
        return expanded

    def _clear_transparent_rgb(self, img):
        from PIL import Image
        import numpy as np

        if img.mode != "RGBA":
            img = img.convert("RGBA")
        data = np.array(img)
        transparent = data[:, :, 3] == 0
        if transparent.any():
            data[transparent] = [0, 0, 0, 0]
        return Image.fromarray(data, mode="RGBA")

    def _remove_background(self, img):
        """
        移除图像背景（简化版）。

        真实场景应使用 rembg 或 SAM 模型。
        """
        from PIL import Image
        import numpy as np

        data = np.array(img)

        # 简单策略：把接近白色/纯色的像素设为透明
        # 检测四个角落的主色调
        h, w = data.shape[:2]
        corners = [
            data[0, 0],
            data[0, w-1],
            data[h-1, 0],
            data[h-1, w-1],
        ]
        opaque_corners = [corner for corner in corners if len(corner) < 4 or corner[3] > 0]
        if not opaque_corners:
            return img

        # 取平均作为背景色
        bg_color = np.mean(opaque_corners, axis=0).astype(np.uint8)

        # 如果是 RGB，加 alpha 通道
        if data.shape[2] == 3:
            alpha = np.ones((h, w), dtype=np.uint8) * 255
            data = np.dstack([data, alpha])

        # 计算与背景色的距离
        diff = np.abs(data[:, :, :3].astype(np.int16) - bg_color[:3].astype(np.int16))
        distance = np.sum(diff, axis=2)

        # 距离小于阈值的设为透明
        threshold = 100
        mask = distance < threshold
        data[mask] = [0, 0, 0, 0]

        return Image.fromarray(data, mode="RGBA")

    def _remove_checkerboard_background(self, img):
        """Remove common fake transparency checkerboard panels from generated sprites."""
        from PIL import Image
        import numpy as np

        if img.mode != "RGBA":
            img = img.convert("RGBA")
        data = np.array(img)
        rgb = data[:, :, :3].astype(np.int16)
        alpha = data[:, :, 3]
        gray = (
            (alpha > 0)
            & (np.abs(rgb[:, :, 0] - rgb[:, :, 1]) <= 4)
            & (np.abs(rgb[:, :, 1] - rgb[:, :, 2]) <= 4)
            & (rgb[:, :, 0] >= 120)
            & (rgb[:, :, 0] <= 230)
        )
        if gray.mean() < 0.10:
            return img
        data[gray] = [0, 0, 0, 0]
        return Image.fromarray(data, mode="RGBA")

    def get_model_name(self) -> str:
        """返回模型名称。"""
        return f"gemini/{self.config['model']}"

    def supports_style(self, style: ImageStyle) -> bool:
        """Gemini 支持所有风格（通过 prompt 引导）。"""
        return True


class GeminiImagenFastGenerator(GeminiImageGenerator):
    """
    Gemini Fast 模型（相同模型，但可在配置中指定不同参数）。

    注意：gemini-3.1-flash-image-preview 本身已经很快（~3-5 秒），
    这个类主要用于兼容性和将来可能的模型切换。
    """

    def __init__(
        self,
        output_dir: Path,
        config: dict | None = None,
    ):
        if config is None:
            config = get_service_config(
                "gemini_image",
                env_prefix="GEMINI_IMAGE",
                default_host="bobdong.cn",
                default_model="gemini-3.1-flash-image-preview",
            )
        super().__init__(output_dir=output_dir, config=config)
