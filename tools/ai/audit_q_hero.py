"""Audit the Q-version hero asset package.

The checks are intentionally structural and deterministic. They cannot decide
whether the character is aesthetically correct, but they catch the failure modes
that break engine import: missing files, wrong dimensions, no alpha, edge/grid
residue, large per-frame anchor jumps, and likely duplicated characters.
"""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image


FACE_EMOTIONS = ("neutral", "happy", "angry", "sad", "surprised", "shy", "hurt")
ANIM_GROUPS = (
    "walk-down",
    "walk-up",
    "walk-left",
    "walk-right",
    "battle-idle",
    "battle-attack",
    "battle-hurt",
)

SPRITE_SIZE = (512, 512)
PORTRAIT_SIZE = (1024, 1024)
FACE_SIZE = (1024, 1024)


@dataclass
class ImageStats:
    path: str
    size: tuple[int, int] | None = None
    mode: str | None = None
    has_alpha: bool = False
    transparent_pct: float = 0.0
    opaque_pct: float = 0.0
    edge_opaque_pct: float = 0.0
    opaque_magenta_pct: float = 0.0
    bbox: tuple[int, int, int, int] | None = None
    bbox_width: int = 0
    bbox_height: int = 0
    bbox_center_x: float = 0.0
    bbox_center_y: float = 0.0
    error: str | None = None


def _edge_opaque_pct(alpha: Image.Image) -> float:
    width, height = alpha.size
    if width <= 0 or height <= 0:
        return 0.0
    px = alpha.load()
    edge_total = (2 * width) + (2 * height) - 4
    edge_opaque = 0
    for x in range(width):
        edge_opaque += 1 if px[x, 0] > 0 else 0
        edge_opaque += 1 if px[x, height - 1] > 0 else 0
    for y in range(1, height - 1):
        edge_opaque += 1 if px[0, y] > 0 else 0
        edge_opaque += 1 if px[width - 1, y] > 0 else 0
    return edge_opaque * 100.0 / edge_total


def image_stats(path: Path) -> ImageStats:
    stats = ImageStats(path=str(path))
    if not path.exists():
        stats.error = "missing"
        return stats

    try:
        with Image.open(path) as img:
            stats.size = img.size
            stats.mode = img.mode
            stats.has_alpha = "A" in img.getbands()
            if not stats.has_alpha:
                return stats

            rgba = img.convert("RGBA")
            alpha = rgba.getchannel("A")
            hist = alpha.histogram()
            total = alpha.size[0] * alpha.size[1]
            transparent = hist[0]
            opaque = total - transparent
            stats.transparent_pct = transparent * 100.0 / total
            stats.opaque_pct = opaque * 100.0 / total
            stats.edge_opaque_pct = _edge_opaque_pct(alpha)
            magenta = 0
            for r, g, b, a in rgba.getdata():
                if a > 0 and r > 220 and b > 180 and g < 80:
                    magenta += 1
            stats.opaque_magenta_pct = magenta * 100.0 / total
            stats.bbox = alpha.getbbox()
            if stats.bbox:
                x0, y0, x1, y1 = stats.bbox
                stats.bbox_width = x1 - x0
                stats.bbox_height = y1 - y0
                stats.bbox_center_x = (x0 + x1) / 2.0
                stats.bbox_center_y = (y0 + y1) / 2.0
    except Exception as exc:  # pragma: no cover - defensive CLI reporting
        stats.error = f"{type(exc).__name__}: {exc}"
    return stats


def _check_required_image(
    path: Path,
    expected_size: tuple[int, int],
    label: str,
) -> tuple[list[str], list[str], ImageStats]:
    errors: list[str] = []
    warnings: list[str] = []
    stats = image_stats(path)

    if stats.error:
        errors.append(f"{label}: {stats.error}: {path}")
        return errors, warnings, stats
    if stats.size != expected_size:
        errors.append(f"{label}: expected {expected_size}, got {stats.size}: {path}")
    if not stats.has_alpha:
        errors.append(f"{label}: PNG has no alpha channel: {path}")
    elif stats.transparent_pct <= 1.0:
        errors.append(f"{label}: almost no transparent background ({stats.transparent_pct:.2f}%): {path}")
    return errors, warnings, stats


def audit_animation_group(
    sprite_dir: Path,
    anim_name: str,
    *,
    edge_error_pct: float = 0.5,
    edge_warn_pct: float = 0.05,
    center_tolerance_px: float = 56.0,
    bbox_ratio_limit: float = 1.45,
    opaque_ratio_limit: float = 1.45,
    magenta_error_pct: float = 0.1,
    magenta_warn_pct: float = 0.02,
) -> tuple[list[str], list[str], list[ImageStats]]:
    """Audit one 4-frame animation group in a sprite directory."""
    if anim_name in {"battle-attack", "battle-hurt"}:
        bbox_ratio_limit = max(bbox_ratio_limit, 1.85)
        opaque_ratio_limit = max(opaque_ratio_limit, 1.65)

    errors: list[str] = []
    warnings: list[str] = []
    stats_list: list[ImageStats] = []

    for frame in range(1, 5):
        path = sprite_dir / f"{anim_name}-{frame}.png"
        frame_errors, frame_warnings, stats = _check_required_image(
            path,
            SPRITE_SIZE,
            f"{anim_name}-{frame}",
        )
        errors.extend(frame_errors)
        warnings.extend(frame_warnings)
        stats_list.append(stats)
        if stats.error or not stats.has_alpha:
            continue
        if stats.edge_opaque_pct > edge_error_pct:
            errors.append(
                f"{anim_name}-{frame}: edge residue too high "
                f"({stats.edge_opaque_pct:.2f}% > {edge_error_pct:.2f}%)"
            )
        elif stats.edge_opaque_pct > edge_warn_pct:
            warnings.append(
                f"{anim_name}-{frame}: edge residue warning "
                f"({stats.edge_opaque_pct:.2f}% > {edge_warn_pct:.2f}%)"
            )
        if stats.opaque_magenta_pct > magenta_error_pct:
            errors.append(
                f"{anim_name}-{frame}: opaque magenta residue too high "
                f"({stats.opaque_magenta_pct:.3f}% > {magenta_error_pct:.3f}%)"
            )
        elif stats.opaque_magenta_pct > magenta_warn_pct:
            warnings.append(
                f"{anim_name}-{frame}: opaque magenta residue warning "
                f"({stats.opaque_magenta_pct:.3f}% > {magenta_warn_pct:.3f}%)"
            )

    valid = [s for s in stats_list if not s.error and s.has_alpha and s.bbox]
    if len(valid) != 4:
        return errors, warnings, stats_list

    center_x = [s.bbox_center_x for s in valid]
    center_y = [s.bbox_center_y for s in valid]
    median_x = statistics.median(center_x)
    median_y = statistics.median(center_y)
    max_dx = max(abs(x - median_x) for x in center_x)
    max_dy = max(abs(y - median_y) for y in center_y)
    if max_dx > center_tolerance_px or max_dy > center_tolerance_px:
        errors.append(
            f"{anim_name}: frame anchor jump too large "
            f"(dx={max_dx:.1f}px, dy={max_dy:.1f}px, limit={center_tolerance_px:.1f}px)"
        )

    widths = [max(1, s.bbox_width) for s in valid]
    heights = [max(1, s.bbox_height) for s in valid]
    width_ratio = max(widths) / min(widths)
    height_ratio = max(heights) / min(heights)
    if width_ratio > bbox_ratio_limit:
        errors.append(
            f"{anim_name}: bbox width ratio too large "
            f"({width_ratio:.2f} > {bbox_ratio_limit:.2f}); likely duplicate character or bad crop"
        )
    if height_ratio > bbox_ratio_limit:
        errors.append(
            f"{anim_name}: bbox height ratio too large "
            f"({height_ratio:.2f} > {bbox_ratio_limit:.2f})"
        )

    opaque = [max(0.01, s.opaque_pct) for s in valid]
    opaque_ratio = max(opaque) / min(opaque)
    if opaque_ratio > opaque_ratio_limit:
        errors.append(
            f"{anim_name}: opaque-area ratio too large "
            f"({opaque_ratio:.2f} > {opaque_ratio_limit:.2f}); likely duplicated character"
        )

    return errors, warnings, stats_list


def audit_package(root: Path) -> dict:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    stats: list[ImageStats] = []

    portrait_errors, portrait_warnings, portrait_stats = _check_required_image(
        root / "portrait-q.png",
        PORTRAIT_SIZE,
        "portrait-q",
    )
    errors.extend(portrait_errors)
    warnings.extend(portrait_warnings)
    stats.append(portrait_stats)

    for emotion in FACE_EMOTIONS:
        label = f"face-q-{emotion}"
        face_errors, face_warnings, face_stats = _check_required_image(
            root / f"{label}.png",
            FACE_SIZE,
            label,
        )
        errors.extend(face_errors)
        warnings.extend(face_warnings)
        stats.append(face_stats)
        if face_stats.has_alpha and face_stats.edge_opaque_pct > 35.0:
            warnings.append(
                f"{label}: close-up touches frame heavily "
                f"({face_stats.edge_opaque_pct:.2f}% edge opaque)"
            )

    sprite_dir = root / "sprites"
    for anim_name in ANIM_GROUPS:
        group_errors, group_warnings, group_stats = audit_animation_group(sprite_dir, anim_name)
        errors.extend(group_errors)
        warnings.extend(group_warnings)
        stats.extend(group_stats)

    return {
        "root": str(root),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": [asdict(s) for s in stats],
    }


def print_text_report(report: dict) -> None:
    print(f"[INFO] audit root: {report['root']}")
    print(f"[INFO] status: {'OK' if report['ok'] else 'FAIL'}")
    print(f"[INFO] errors: {len(report['errors'])}")
    for item in report["errors"]:
        print(f"  ERROR: {item}")
    print(f"[INFO] warnings: {len(report['warnings'])}")
    for item in report["warnings"]:
        print(f"  WARN: {item}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        default=str(Path(__file__).resolve().parent / "out" / "hero01_q"),
        help="Q hero output root. Default: tools/ai/out/hero01_q",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report")
    args = parser.parse_args()

    report = audit_package(Path(args.root))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text_report(report)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
