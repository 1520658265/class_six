from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ObjectSpriteQuality:
    passed: bool
    transparent_ratio: float
    foreground_ratio: float
    semi_alpha_ratio: float
    corner_opaque_ratio: float
    border_opaque_ratio: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RpgSpriteUsability:
    passed: bool
    source_size: tuple[int, int]
    runtime_size: tuple[int, int]
    bbox: tuple[int, int, int, int] | None
    runtime_bbox: tuple[int, int, int, int] | None
    bbox_aspect: float
    expected_aspect: float
    bbox_canvas_ratio: float
    runtime_bbox_width_ratio: float
    runtime_bbox_height_ratio: float
    runtime_bbox_fill_ratio: float
    runtime_foreground_ratio: float
    runtime_visible_pixels: int
    unique_color_count: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "source_size": list(self.source_size),
            "runtime_size": list(self.runtime_size),
            "bbox": list(self.bbox) if self.bbox else None,
            "runtime_bbox": list(self.runtime_bbox) if self.runtime_bbox else None,
            "bbox_aspect": self.bbox_aspect,
            "expected_aspect": self.expected_aspect,
            "bbox_canvas_ratio": self.bbox_canvas_ratio,
            "runtime_bbox_width_ratio": self.runtime_bbox_width_ratio,
            "runtime_bbox_height_ratio": self.runtime_bbox_height_ratio,
            "runtime_bbox_fill_ratio": self.runtime_bbox_fill_ratio,
            "runtime_foreground_ratio": self.runtime_foreground_ratio,
            "runtime_visible_pixels": self.runtime_visible_pixels,
            "unique_color_count": self.unique_color_count,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class SpriteRepackResult:
    passed: bool
    source_size: tuple[int, int]
    runtime_size: tuple[int, int]
    source_bbox: tuple[int, int, int, int] | None
    placed_bbox: tuple[int, int, int, int] | None
    scale: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "source_size": list(self.source_size),
            "runtime_size": list(self.runtime_size),
            "source_bbox": list(self.source_bbox) if self.source_bbox else None,
            "placed_bbox": list(self.placed_bbox) if self.placed_bbox else None,
            "scale": self.scale,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def clean_object_sprite_background(
    image_path: str | Path,
    output_path: str | Path | None = None,
    *,
    binary_alpha: bool = True,
) -> ObjectSpriteQuality:
    """Remove fake transparency/checker/noisy edge backgrounds from an object sprite."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return ObjectSpriteQuality(
            passed=False,
            transparent_ratio=0.0,
            foreground_ratio=0.0,
            semi_alpha_ratio=1.0,
            corner_opaque_ratio=1.0,
            border_opaque_ratio=1.0,
            errors=["PIL or numpy is not available for sprite cleanup"],
        )

    src = Path(image_path)
    dst = Path(output_path) if output_path else src
    with Image.open(src).convert("RGBA") as img:
        arr = np.array(img)

    if arr.size == 0:
        return ObjectSpriteQuality(
            passed=False,
            transparent_ratio=0.0,
            foreground_ratio=0.0,
            semi_alpha_ratio=0.0,
            corner_opaque_ratio=1.0,
            border_opaque_ratio=1.0,
            errors=["image is empty"],
        )

    bg_mask = _edge_connected_background_mask(arr)
    arr[bg_mask, 3] = 0

    if binary_alpha:
        alpha = arr[:, :, 3]
        arr[:, :, 3] = np.where(alpha >= 96, 255, 0).astype("uint8")

    _remove_small_foreground_noise(arr)
    arr[arr[:, :, 3] == 0, :3] = 0

    Image.fromarray(arr, "RGBA").save(dst, "PNG")
    return validate_object_sprite_quality(dst)


def fit_object_sprite_to_runtime_canvas(
    image_path: str | Path,
    footprint: tuple[int, int],
    tile_size: tuple[int, int],
    output_path: str | Path | None = None,
    *,
    anchor: str = "bottom_center",
    category: str = "",
    max_colors: int = 64,
) -> SpriteRepackResult:
    """Crop the generated subject and repack it onto the runtime footprint canvas."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        runtime_size = (footprint[0] * tile_size[0], footprint[1] * tile_size[1])
        return SpriteRepackResult(
            passed=False,
            source_size=(0, 0),
            runtime_size=runtime_size,
            source_bbox=None,
            placed_bbox=None,
            scale=0.0,
            errors=["PIL or numpy is not available for sprite repacking"],
        )

    src = Path(image_path)
    dst = Path(output_path) if output_path else src
    runtime_size = (footprint[0] * tile_size[0], footprint[1] * tile_size[1])
    with Image.open(src).convert("RGBA") as img:
        source_size = img.size
        bbox = img.getchannel("A").getbbox()
        if bbox is None:
            return SpriteRepackResult(
                passed=False,
                source_size=source_size,
                runtime_size=runtime_size,
                source_bbox=None,
                placed_bbox=None,
                scale=0.0,
                errors=["sprite has no visible foreground"],
            )
        cropped = img.crop(bbox)

    bbox_w = max(1, bbox[2] - bbox[0])
    bbox_h = max(1, bbox[3] - bbox[1])
    target_ratio = _target_runtime_coverage(category)
    usable_w = max(1, int(round(runtime_size[0] * target_ratio[0])))
    usable_h = max(1, int(round(runtime_size[1] * target_ratio[1])))
    scale = min(usable_w / bbox_w, usable_h / bbox_h)
    new_w = max(1, min(runtime_size[0], int(round(bbox_w * scale))))
    new_h = max(1, min(runtime_size[1], int(round(bbox_h * scale))))

    resample = _resize_filter(downscaling=(new_w < bbox_w or new_h < bbox_h))
    resized = cropped.resize((new_w, new_h), resample)
    cropped.close()
    resized = _normalize_runtime_sprite_pixels(resized, max_colors=max_colors)

    canvas = Image.new("RGBA", runtime_size, (0, 0, 0, 0))
    paste_x = _anchored_x(runtime_size[0], new_w, anchor)
    paste_y = _anchored_y(runtime_size[1], new_h, anchor)
    canvas.paste(resized, (paste_x, paste_y), resized)
    resized.close()

    arr = np.array(canvas)
    alpha = arr[:, :, 3]
    runtime_bbox = _alpha_bbox_from_array(alpha)
    if runtime_bbox is None:
        canvas.close()
        return SpriteRepackResult(
            passed=False,
            source_size=source_size,
            runtime_size=runtime_size,
            source_bbox=bbox,
            placed_bbox=None,
            scale=scale,
            errors=["repacked sprite has no visible foreground"],
        )
    arr[alpha == 0, :3] = 0
    Image.fromarray(arr, "RGBA").save(dst, "PNG")
    canvas.close()

    warnings: list[str] = []
    if source_size == runtime_size:
        warnings.append("source sprite was already runtime-sized; repacked in place")

    return SpriteRepackResult(
        passed=True,
        source_size=source_size,
        runtime_size=runtime_size,
        source_bbox=bbox,
        placed_bbox=runtime_bbox,
        scale=scale,
        warnings=warnings,
    )


def validate_rpg_sprite_usability(
    image_path: str | Path,
    footprint: tuple[int, int],
    tile_size: tuple[int, int],
    *,
    category: str = "",
) -> RpgSpriteUsability:
    """Validate whether a cleaned sprite is usable when placed back on an RPG tilemap."""
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        runtime_size = (footprint[0] * tile_size[0], footprint[1] * tile_size[1])
        return RpgSpriteUsability(
            passed=False,
            source_size=(0, 0),
            runtime_size=runtime_size,
            bbox=None,
            runtime_bbox=None,
            bbox_aspect=0.0,
            expected_aspect=_safe_aspect(runtime_size),
            bbox_canvas_ratio=0.0,
            runtime_bbox_width_ratio=0.0,
            runtime_bbox_height_ratio=0.0,
            runtime_bbox_fill_ratio=0.0,
            runtime_foreground_ratio=0.0,
            runtime_visible_pixels=0,
            unique_color_count=0,
            errors=["PIL or numpy is not available for RPG sprite usability validation"],
        )

    runtime_size = (footprint[0] * tile_size[0], footprint[1] * tile_size[1])
    with Image.open(image_path).convert("RGBA") as img:
        source_size = img.size
        alpha = img.getchannel("A")
        bbox = alpha.getbbox()
        runtime = img.resize(runtime_size, Image.NEAREST)
        runtime_arr = np.array(runtime)
        runtime.close()
        arr = np.array(img)

    errors: list[str] = []
    warnings: list[str] = []
    expected_aspect = _safe_aspect(runtime_size)
    if bbox is None:
        return RpgSpriteUsability(
            passed=False,
            source_size=source_size,
            runtime_size=runtime_size,
            bbox=None,
            runtime_bbox=None,
            bbox_aspect=0.0,
            expected_aspect=expected_aspect,
            bbox_canvas_ratio=0.0,
            runtime_bbox_width_ratio=0.0,
            runtime_bbox_height_ratio=0.0,
            runtime_bbox_fill_ratio=0.0,
            runtime_foreground_ratio=0.0,
            runtime_visible_pixels=0,
            unique_color_count=0,
            errors=["sprite has no visible foreground"],
        )

    x0, y0, x1, y1 = bbox
    bbox_w = max(1, x1 - x0)
    bbox_h = max(1, y1 - y0)
    bbox_aspect = bbox_w / bbox_h
    bbox_canvas_ratio = (bbox_w * bbox_h) / max(1, source_size[0] * source_size[1])

    runtime_alpha = runtime_arr[:, :, 3]
    runtime_bbox = _alpha_bbox_from_array(runtime_alpha)
    runtime_visible_pixels = int((runtime_alpha > 10).sum())
    runtime_foreground_ratio = float(runtime_visible_pixels / max(1, runtime_alpha.size))
    visible_rgb = runtime_arr[runtime_alpha > 10, :3]
    unique_color_count = int(len({tuple(pixel) for pixel in visible_rgb.reshape(-1, 3).tolist()})) if len(visible_rgb) else 0
    runtime_bbox_width_ratio = 0.0
    runtime_bbox_height_ratio = 0.0
    runtime_bbox_fill_ratio = 0.0
    if runtime_bbox is not None:
        rx0, ry0, rx1, ry1 = runtime_bbox
        runtime_bbox_w = max(1, rx1 - rx0)
        runtime_bbox_h = max(1, ry1 - ry0)
        runtime_bbox_width_ratio = runtime_bbox_w / max(1, runtime_size[0])
        runtime_bbox_height_ratio = runtime_bbox_h / max(1, runtime_size[1])
        runtime_bbox_fill_ratio = runtime_visible_pixels / max(1, runtime_bbox_w * runtime_bbox_h)

    min_foreground_ratio = _min_runtime_foreground_ratio(category)
    min_visible_pixels = max(24, int(runtime_alpha.size * min_foreground_ratio))
    if runtime_visible_pixels < min_visible_pixels:
        errors.append(
            f"runtime sprite is not readable enough after scaling ({runtime_visible_pixels} visible pixels)"
        )

    min_canvas_ratio = _min_bbox_canvas_ratio(category)
    if bbox_canvas_ratio < min_canvas_ratio:
        errors.append("subject is too small on the source canvas")
    elif bbox_canvas_ratio < max(0.18, min_canvas_ratio * 1.5):
        warnings.append("subject uses little of the source canvas")
    if bbox_canvas_ratio > 0.92:
        warnings.append("subject nearly fills the source canvas; transparent margins may be too small")

    min_width_ratio, min_height_ratio = _min_runtime_bbox_ratios(category)
    if runtime_bbox_width_ratio < min_width_ratio:
        errors.append(
            f"runtime silhouette is too narrow for its footprint ({runtime_bbox_width_ratio:.2f} width coverage)"
        )
    if runtime_bbox_height_ratio < min_height_ratio:
        errors.append(
            f"runtime silhouette is too short for its footprint ({runtime_bbox_height_ratio:.2f} height coverage)"
        )

    min_fill_ratio = _min_runtime_bbox_fill_ratio(category)
    if runtime_bbox_fill_ratio < min_fill_ratio:
        errors.append(
            f"runtime silhouette is too sparse/thin to read as an RPG sprite ({runtime_bbox_fill_ratio:.2f} fill)"
        )

    strict_aspect_categories = {"building", "large_prop", "thin_prop", "text_sign", "facade_overlay"}
    if category in strict_aspect_categories and expected_aspect > 0:
        aspect_match = min(bbox_aspect, expected_aspect) / max(bbox_aspect, expected_aspect)
        threshold = 0.75 if category == "building" else 0.60
        if aspect_match < threshold:
            errors.append(
                f"visible silhouette aspect {bbox_aspect:.2f} does not match footprint aspect {expected_aspect:.2f}"
            )

    max_colors = _max_runtime_color_count(category)
    if unique_color_count > max_colors:
        errors.append(
            f"runtime sprite has too many unique colors/noisy pixels for clean pixel art ({unique_color_count})"
        )
    elif unique_color_count > int(max_colors * 0.75):
        warnings.append("runtime sprite color count is high; may read as noisy render")

    return RpgSpriteUsability(
        passed=not errors,
        source_size=source_size,
        runtime_size=runtime_size,
        bbox=bbox,
        runtime_bbox=runtime_bbox,
        bbox_aspect=bbox_aspect,
        expected_aspect=expected_aspect,
        bbox_canvas_ratio=bbox_canvas_ratio,
        runtime_bbox_width_ratio=runtime_bbox_width_ratio,
        runtime_bbox_height_ratio=runtime_bbox_height_ratio,
        runtime_bbox_fill_ratio=runtime_bbox_fill_ratio,
        runtime_foreground_ratio=runtime_foreground_ratio,
        runtime_visible_pixels=runtime_visible_pixels,
        unique_color_count=unique_color_count,
        errors=errors,
        warnings=warnings,
    )


def validate_object_sprite_quality(image_path: str | Path) -> ObjectSpriteQuality:
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return ObjectSpriteQuality(
            passed=False,
            transparent_ratio=0.0,
            foreground_ratio=0.0,
            semi_alpha_ratio=1.0,
            corner_opaque_ratio=1.0,
            border_opaque_ratio=1.0,
            errors=["PIL or numpy is not available for sprite validation"],
        )

    with Image.open(image_path).convert("RGBA") as img:
        arr = np.array(img)

    h, w = arr.shape[:2]
    alpha = arr[:, :, 3]
    total = max(1, alpha.size)
    transparent_ratio = float((alpha <= 10).sum() / total)
    foreground_ratio = float((alpha > 10).sum() / total)
    semi_alpha_ratio = float(((alpha > 10) & (alpha < 245)).sum() / total)

    border_width = _edge_width(w, h)
    corner = _corner_alpha(alpha, border_width)
    border = _border_alpha(alpha, border_width)
    corner_opaque_ratio = float((corner > 10).sum() / max(1, corner.size))
    border_opaque_ratio = float((border > 10).sum() / max(1, border.size))

    errors: list[str] = []
    warnings: list[str] = []
    if foreground_ratio < 0.01:
        errors.append("sprite has almost no visible foreground")
    if transparent_ratio < 0.05:
        errors.append("sprite has too little transparent area")
    if corner_opaque_ratio > 0.08:
        errors.append("sprite corners are not cleanly transparent")
    if semi_alpha_ratio > 0.08:
        errors.append("sprite has too many semi-transparent/noisy pixels")
    if border_opaque_ratio > 0.45:
        warnings.append("sprite foreground touches too much of the canvas border")

    return ObjectSpriteQuality(
        passed=not errors,
        transparent_ratio=transparent_ratio,
        foreground_ratio=foreground_ratio,
        semi_alpha_ratio=semi_alpha_ratio,
        corner_opaque_ratio=corner_opaque_ratio,
        border_opaque_ratio=border_opaque_ratio,
        errors=errors,
        warnings=warnings,
    )


def _edge_connected_background_mask(arr):
    import numpy as np

    h, w = arr.shape[:2]
    rgb = arr[:, :, :3].astype("int16")
    alpha = arr[:, :, 3]
    border_width = _edge_width(w, h)
    border = np.concatenate(
        [
            arr[:border_width, :, :].reshape(-1, 4),
            arr[-border_width:, :, :].reshape(-1, 4),
            arr[:, :border_width, :].reshape(-1, 4),
            arr[:, -border_width:, :].reshape(-1, 4),
        ],
        axis=0,
    )
    border_visible = border[border[:, 3] > 12]
    candidate = alpha <= 10

    if len(border_visible):
        palette = _border_palette(border_visible[:, :3])
        if len(palette):
            diff = np.abs(rgb[:, :, None, :] - palette[None, None, :, :]).sum(axis=3)
            candidate |= diff.min(axis=2) <= 42

        border_rgb = border_visible[:, :3].astype("int16")
        border_sat = border_rgb.max(axis=1) - border_rgb.min(axis=1)
        if float((border_sat < 24).mean()) > 0.75:
            sat = rgb.max(axis=2) - rgb.min(axis=2)
            lum = _luminance(rgb)
            border_lum = _luminance(border_rgb.reshape(-1, 1, 3)).reshape(-1)
            low = max(0.0, float(np.percentile(border_lum, 2)) - 25.0)
            high = min(255.0, float(np.percentile(border_lum, 98)) + 25.0)
            candidate |= (sat < 28) & (lum >= low) & (lum <= high)

    return _flood_from_edges(candidate)


def _border_palette(border_rgb):
    import numpy as np

    quantized = (border_rgb.astype("int16") // 12).tolist()
    counts = Counter(tuple(pixel) for pixel in quantized)
    colors = []
    for key, _count in counts.most_common(32):
        colors.append([channel * 12 + 6 for channel in key])
    return np.array(colors, dtype="int16")


def _flood_from_edges(candidate):
    import numpy as np

    h, w = candidate.shape
    background = np.zeros((h, w), dtype=bool)
    queue: deque[tuple[int, int]] = deque()
    for x in range(w):
        if candidate[0, x]:
            queue.append((0, x))
        if candidate[h - 1, x]:
            queue.append((h - 1, x))
    for y in range(h):
        if candidate[y, 0]:
            queue.append((y, 0))
        if candidate[y, w - 1]:
            queue.append((y, w - 1))

    while queue:
        y, x = queue.popleft()
        if background[y, x] or not candidate[y, x]:
            continue
        background[y, x] = True
        if y > 0:
            queue.append((y - 1, x))
        if y < h - 1:
            queue.append((y + 1, x))
        if x > 0:
            queue.append((y, x - 1))
        if x < w - 1:
            queue.append((y, x + 1))
    return background


def _remove_small_foreground_noise(arr) -> None:
    import numpy as np

    alpha = arr[:, :, 3]
    foreground = alpha > 10
    h, w = foreground.shape
    visited = np.zeros((h, w), dtype=bool)
    min_component_area = max(4, int(h * w * 0.0005))

    for start_y in range(h):
        for start_x in range(w):
            if visited[start_y, start_x] or not foreground[start_y, start_x]:
                continue
            pixels: list[tuple[int, int]] = []
            queue: deque[tuple[int, int]] = deque([(start_y, start_x)])
            visited[start_y, start_x] = True
            while queue:
                y, x = queue.popleft()
                pixels.append((y, x))
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < h and 0 <= xx < w and not visited[yy, xx] and foreground[yy, xx]:
                        visited[yy, xx] = True
                        queue.append((yy, xx))
            if len(pixels) < min_component_area:
                ys, xs = zip(*pixels)
                arr[ys, xs, 3] = 0


def _alpha_bbox_from_array(alpha):
    import numpy as np

    ys, xs = np.where(alpha > 10)
    if len(xs) == 0 or len(ys) == 0:
        return None
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _target_runtime_coverage(category: str) -> tuple[float, float]:
    if category == "building":
        return (0.92, 0.90)
    if category in {"facade_overlay", "text_sign"}:
        return (0.94, 0.82)
    if category == "large_prop":
        return (0.88, 0.82)
    if category == "thin_prop":
        return (0.68, 0.92)
    if category == "small_prop":
        return (0.78, 0.78)
    return (0.82, 0.82)


def _min_bbox_canvas_ratio(category: str) -> float:
    if category == "building":
        return 0.28
    if category == "large_prop":
        return 0.16
    if category == "thin_prop":
        return 0.10
    if category in {"small_prop", "facade_overlay", "text_sign"}:
        return 0.12
    return 0.08


def _min_runtime_foreground_ratio(category: str) -> float:
    if category == "building":
        return 0.16
    if category == "large_prop":
        return 0.055
    if category == "thin_prop":
        return 0.040
    if category == "small_prop":
        return 0.060
    if category in {"facade_overlay", "text_sign"}:
        return 0.045
    return 0.025


def _min_runtime_bbox_ratios(category: str) -> tuple[float, float]:
    if category == "building":
        return (0.72, 0.64)
    if category == "large_prop":
        return (0.64, 0.48)
    if category == "thin_prop":
        return (0.30, 0.70)
    if category == "small_prop":
        return (0.45, 0.45)
    if category in {"facade_overlay", "text_sign"}:
        return (0.70, 0.30)
    return (0.25, 0.25)


def _min_runtime_bbox_fill_ratio(category: str) -> float:
    if category == "building":
        return 0.22
    if category == "large_prop":
        return 0.16
    if category == "thin_prop":
        return 0.10
    if category == "small_prop":
        return 0.18
    if category in {"facade_overlay", "text_sign"}:
        return 0.10
    return 0.08


def _max_runtime_color_count(category: str) -> int:
    if category == "building":
        return 96
    if category in {"large_prop", "small_prop", "thin_prop"}:
        return 64
    return 96


def _resize_filter(*, downscaling: bool):
    try:
        from PIL import Image

        if downscaling:
            return Image.Resampling.BOX
        return Image.Resampling.NEAREST
    except AttributeError:
        from PIL import Image

        return Image.BOX if downscaling else Image.NEAREST


def _normalize_runtime_sprite_pixels(img, *, max_colors: int):
    from PIL import Image
    import numpy as np

    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    alpha = arr[:, :, 3]
    if max_colors > 0 and int((alpha > 10).sum()):
        rgb_img = Image.fromarray(arr[:, :, :3], "RGB")
        try:
            quantized = rgb_img.quantize(colors=max(2, max_colors), method=Image.Quantize.MEDIANCUT)
        except AttributeError:
            quantized = rgb_img.quantize(colors=max(2, max_colors), method=Image.MEDIANCUT)
        arr[:, :, :3] = np.array(quantized.convert("RGB"))
        rgb_img.close()
        quantized.close()

    arr[:, :, 3] = np.where(alpha >= 72, 255, 0).astype("uint8")
    arr[arr[:, :, 3] == 0, :3] = 0
    _remove_small_foreground_noise(arr)
    arr[arr[:, :, 3] == 0, :3] = 0
    rgba.close()
    return Image.fromarray(arr, "RGBA")


def _anchored_x(canvas_w: int, sprite_w: int, anchor: str) -> int:
    anchor = anchor.lower()
    if anchor.endswith("_left") or anchor == "left":
        return 0
    if anchor.endswith("_right") or anchor == "right":
        return max(0, canvas_w - sprite_w)
    return max(0, (canvas_w - sprite_w) // 2)


def _anchored_y(canvas_h: int, sprite_h: int, anchor: str) -> int:
    anchor = anchor.lower()
    if anchor.startswith("top"):
        return 0
    if anchor.startswith("bottom") or anchor == "bottom":
        bottom_margin = 0 if sprite_h >= canvas_h else max(0, min(3, canvas_h // 32))
        return max(0, canvas_h - sprite_h - bottom_margin)
    return max(0, (canvas_h - sprite_h) // 2)


def _edge_width(width: int, height: int) -> int:
    return max(2, min(8, min(width, height) // 12))


def _corner_alpha(alpha, border_width: int):
    import numpy as np

    return np.concatenate(
        [
            alpha[:border_width, :border_width].reshape(-1),
            alpha[:border_width, -border_width:].reshape(-1),
            alpha[-border_width:, :border_width].reshape(-1),
            alpha[-border_width:, -border_width:].reshape(-1),
        ]
    )


def _border_alpha(alpha, border_width: int):
    import numpy as np

    return np.concatenate(
        [
            alpha[:border_width, :].reshape(-1),
            alpha[-border_width:, :].reshape(-1),
            alpha[:, :border_width].reshape(-1),
            alpha[:, -border_width:].reshape(-1),
        ]
    )


def _luminance(rgb):
    return (rgb[:, :, 0] * 299 + rgb[:, :, 1] * 587 + rgb[:, :, 2] * 114) / 1000.0


def _safe_aspect(size: tuple[int, int]) -> float:
    return size[0] / max(1, size[1])
