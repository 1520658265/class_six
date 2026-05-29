"""
Convert a chroma-keyed JPG (magenta #FF00FF background) to a PNG with alpha.

Default mode is conservative but sprite-sheet aware:
- Border-connected magenta is treated as background.
- Large, high-purity magenta components are also treated as background, even
  when they are separated by frame/grid lines.
- Large white/light-gray cell mattes and straight grid-line remnants are cleaned.
- Small or low-purity pink/purple details inside the art stay opaque.

Usage:
    python jpg_to_png_alpha.py <input.jpg> [-o OUT.png] [--mode auto]
"""

import argparse
import os
import sys
from collections import deque

import numpy as np
from PIL import Image

try:
    from scipy import ndimage
except Exception:  # pragma: no cover - optional speedup
    ndimage = None


def connected_components(mask, strong_mask=None):
    """Label 4-connected True components and collect cheap component stats."""
    if ndimage is not None:
        structure = np.array(((0, 1, 0), (1, 1, 1), (0, 1, 0)), dtype=np.uint8)
        labels, count = ndimage.label(mask, structure=structure)
        if count == 0:
            return labels.astype(np.int32, copy=False), []

        areas = np.bincount(labels.ravel(), minlength=count + 1)
        if strong_mask is None:
            strong_counts = np.zeros(count + 1, dtype=np.int64)
        else:
            strong_counts = np.bincount(
                labels.ravel(),
                weights=strong_mask.ravel().astype(np.uint8),
                minlength=count + 1,
            ).astype(np.int64)

        border_ids = np.unique(np.concatenate((labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1])))
        touches_border = np.zeros(count + 1, dtype=bool)
        touches_border[border_ids] = True
        touches_border[0] = False

        components = []
        for component_id, slc in enumerate(ndimage.find_objects(labels), start=1):
            if slc is None:
                continue
            y_slice, x_slice = slc
            components.append((
                component_id,
                int(areas[component_id]),
                bool(touches_border[component_id]),
                int(strong_counts[component_id]),
                int(x_slice.start),
                int(y_slice.start),
                int(x_slice.stop - 1),
                int(y_slice.stop - 1),
            ))
        return labels.astype(np.int32, copy=False), components

    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    components = []
    component_id = 0

    ys, xs = np.where(mask)
    for sy, sx in zip(ys, xs):
        if labels[sy, sx] != 0:
            continue

        component_id += 1
        area = 0
        strong_count = 0
        touches_border = False
        xmin = w
        xmax = 0
        ymin = h
        ymax = 0
        q = deque([(int(sy), int(sx))])
        labels[sy, sx] = component_id

        while q:
            y, x = q.popleft()
            area += 1
            xmin = min(xmin, x)
            xmax = max(xmax, x)
            ymin = min(ymin, y)
            ymax = max(ymax, y)
            if strong_mask is not None and strong_mask[y, x]:
                strong_count += 1
            if y == 0 or x == 0 or y == h - 1 or x == w - 1:
                touches_border = True

            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and labels[ny, nx] == 0:
                    labels[ny, nx] = component_id
                    q.append((ny, nx))

        components.append((component_id, area, touches_border, strong_count, xmin, ymin, xmax, ymax))

    return labels, components


def dilate_4(mask):
    grow = np.zeros_like(mask)
    grow[1:, :] |= mask[:-1, :]
    grow[:-1, :] |= mask[1:, :]
    grow[:, 1:] |= mask[:, :-1]
    grow[:, :-1] |= mask[:, 1:]
    return grow


def dilate_4_n(mask, passes):
    out = mask
    for _ in range(max(0, passes)):
        out = out | dilate_4(out)
    return out


def add_grid_hints(row_hints, col_hints, xmin, ymin, xmax, ymax):
    row_hints.add(ymin)
    row_hints.add(ymax)
    col_hints.add(xmin)
    col_hints.add(xmax)


def cleanup_light_matte(
    arr,
    transparent,
    min_area,
    min_bbox_ratio,
    min_fill,
    min_value,
    min_channel,
    max_sat,
):
    max_c = arr.max(axis=2).astype(np.int16)
    min_c = arr.min(axis=2).astype(np.int16)
    sat = max_c - min_c
    matte = (
        ~transparent
        & (max_c >= min_value)
        & (min_c >= min_channel)
        & (sat <= max_sat)
    )
    if not matte.any():
        return transparent, 0, []

    neighbor_transparent = dilate_4(transparent)
    labels, components = connected_components(matte, neighbor_transparent)
    selected_labels = []
    selected_bboxes = []
    total_area = transparent.size

    for component_id, area, _touches_border, touch_count, xmin, ymin, xmax, ymax in components:
        if touch_count <= 0 or area < min_area:
            continue
        bbox_area = (xmax - xmin + 1) * (ymax - ymin + 1)
        bbox_ratio = bbox_area / total_area
        fill_ratio = area / bbox_area if bbox_area else 0.0
        if bbox_ratio >= min_bbox_ratio and fill_ratio >= min_fill:
            selected_labels.append(component_id)
            selected_bboxes.append((xmin, ymin, xmax, ymax))

    if not selected_labels:
        return transparent, 0, []

    cleaned = np.isin(labels, selected_labels)
    return transparent | cleaned, int(cleaned.sum()), selected_bboxes


def cleanup_grid_lines(
    arr,
    transparent,
    row_hints,
    col_hints,
    band_radius,
    neighbor_radius,
    max_sat,
    max_value,
):
    if not row_hints and not col_hints:
        return transparent, 0

    h, w = transparent.shape
    max_c = arr.max(axis=2).astype(np.int16)
    min_c = arr.min(axis=2).astype(np.int16)
    sat = max_c - min_c
    low_sat_opaque = ~transparent & (sat <= max_sat) & (max_c <= max_value)

    band = np.zeros_like(transparent)
    for y in row_hints:
        y0 = max(0, y - band_radius)
        y1 = min(h, y + band_radius + 1)
        band[y0:y1, :] = True
    for x in col_hints:
        x0 = max(0, x - band_radius)
        x1 = min(w, x + band_radius + 1)
        band[:, x0:x1] = True

    near_transparent = dilate_4_n(transparent, neighbor_radius)
    grid_pixels = low_sat_opaque & band & near_transparent
    if not grid_pixels.any():
        return transparent, 0
    return transparent | grid_pixels, int(grid_pixels.sum())


def chroma_key(
    img,
    tol,
    halo_passes,
    halo_max_sat,
    mode="auto",
    min_component_area=4096,
    min_component_ratio=0.005,
    bg_min_rb=170,
    bg_max_g=150,
    bg_max_rb_delta=90,
    bg_min_purity=0.65,
    halo_min_margin=3,
    halo_max_rb_delta=120,
    matte_cleanup="auto",
    matte_min_area=8192,
    matte_min_bbox_ratio=0.01,
    matte_min_fill=0.35,
    matte_min_value=185,
    matte_min_channel=165,
    matte_max_sat=55,
    grid_cleanup="auto",
    grid_band_radius=8,
    grid_neighbor_radius=3,
    grid_max_sat=90,
    grid_max_value=245,
):
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    r = arr[..., 0].astype(np.int16)
    g = arr[..., 1].astype(np.int16)
    b = arr[..., 2].astype(np.int16)

    # Magenta family: R and B both higher than G.
    candidate = ((r - g) >= tol) & ((b - g) >= tol)

    row_hints = set()
    col_hints = set()

    if mode == "global":
        transparent = candidate.copy()
    else:
        strong_bg = (
            candidate
            & (r >= bg_min_rb)
            & (b >= bg_min_rb)
            & (g <= bg_max_g)
            & (np.abs(r - b) <= bg_max_rb_delta)
        )
        labels, components = connected_components(candidate, strong_bg)
        large_component_min = max(min_component_area, int(candidate.size * min_component_ratio))
        selected_labels = []

        for component_id, area, touches_border, strong_count, xmin, ymin, xmax, ymax in components:
            if touches_border:
                selected_labels.append(component_id)
                add_grid_hints(row_hints, col_hints, xmin, ymin, xmax, ymax)
                continue
            if mode == "auto":
                purity = strong_count / area if area else 0.0
                if area >= large_component_min and purity >= bg_min_purity:
                    selected_labels.append(component_id)
                    add_grid_hints(row_hints, col_hints, xmin, ymin, xmax, ymax)

        if selected_labels:
            transparent = np.isin(labels, selected_labels)
        else:
            transparent = np.zeros_like(candidate)

    cand_count = int(candidate.sum())
    core_count = int(transparent.sum())

    # Halo cleanup: absorb weak magenta matte pixels next to keyed background.
    # Pure low-saturation black/gray lines are left alone because sprite sheets
    # often use them as frame separators or character outlines.
    if halo_passes > 0:
        max_c = np.maximum(np.maximum(r, g), b)
        min_c = np.minimum(np.minimum(r, g), b)
        sat = (max_c - min_c).astype(np.int16)
        absorbable = (
            ((r - g) >= halo_min_margin)
            & ((b - g) >= halo_min_margin)
            & (sat <= halo_max_sat)
            & (np.abs(r - b) <= halo_max_rb_delta)
        )
        for _ in range(halo_passes):
            grow = dilate_4(transparent)
            new_pixels = grow & ~transparent & absorbable
            if not new_pixels.any():
                break
            transparent |= new_pixels

    halo_count = int(transparent.sum()) - core_count

    matte_count = 0
    if matte_cleanup == "auto":
        transparent, matte_count, matte_bboxes = cleanup_light_matte(
            arr,
            transparent,
            matte_min_area,
            matte_min_bbox_ratio,
            matte_min_fill,
            matte_min_value,
            matte_min_channel,
            matte_max_sat,
        )
        for xmin, ymin, xmax, ymax in matte_bboxes:
            add_grid_hints(row_hints, col_hints, xmin, ymin, xmax, ymax)

    grid_count = 0
    if grid_cleanup == "auto":
        transparent, grid_count = cleanup_grid_lines(
            arr,
            transparent,
            row_hints,
            col_hints,
            grid_band_radius,
            grid_neighbor_radius,
            grid_max_sat,
            grid_max_value,
        )

    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[..., :3] = arr
    rgba[..., 3] = np.where(transparent, 0, 255).astype(np.uint8)
    # Wipe RGB on transparent pixels so viewers that ignore alpha (or premultiply
    # with a colored background) don't leak the magenta halo.
    rgba[transparent] = 0

    return Image.fromarray(rgba, "RGBA"), cand_count, core_count, halo_count, matte_count, grid_count


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("-o", "--out", help="Output PNG path. Default: same dir, same stem, .png")
    p.add_argument("--mode", choices=("auto", "edge", "global"), default="auto",
                   help="Background selection mode. auto keeps pink content but handles sprite sheets; edge only keys border-connected magenta; global keys all magenta candidates.")
    p.add_argument("--tolerance", type=int, default=15,
                   help="Min margin by which R and B must exceed G to count as magenta-family core (default 15).")
    p.add_argument("--halo-passes", type=int, default=2,
                   help="Number of 1-pixel dilation passes to absorb JPG magenta halo (default 2).")
    p.add_argument("--halo-max-sat", type=int, default=110,
                   help="Max RGB saturation a weak-magenta halo pixel may have to be absorbed (default 110). Higher values eat more.")
    p.add_argument("--halo-min-margin", type=int, default=3,
                   help="Min margin by which R and B must exceed G for halo cleanup (default 3).")
    p.add_argument("--min-component-area", type=int, default=4096,
                   help="Min pixel area for an isolated magenta component to be background in auto mode (default 4096).")
    p.add_argument("--min-component-ratio", type=float, default=0.005,
                   help="Min image-area ratio for isolated magenta background components in auto mode (default 0.005).")
    p.add_argument("--bg-min-purity", type=float, default=0.65,
                   help="Min pure-magenta fraction for isolated background components in auto mode (default 0.65).")
    p.add_argument("--matte-cleanup", choices=("auto", "off"), default="auto",
                   help="Also remove large white/light-gray rectangular matte areas touching keyed background (default auto).")
    p.add_argument("--matte-min-area", type=int, default=8192,
                   help="Min pixel area for light matte cleanup components (default 8192).")
    p.add_argument("--matte-min-fill", type=float, default=0.35,
                   help="Min component fill ratio inside its bounding box for light matte cleanup (default 0.35).")
    p.add_argument("--grid-cleanup", choices=("auto", "off"), default="auto",
                   help="Remove low-saturation horizontal/vertical grid remnants along detected cell boundaries (default auto).")
    p.add_argument("--grid-band-radius", type=int, default=8,
                   help="Half-width in pixels around detected cell boundaries for grid cleanup (default 8).")
    p.add_argument("--grid-max-sat", type=int, default=90,
                   help="Max RGB saturation for opaque grid remnants (default 90).")
    args = p.parse_args()

    if not os.path.isfile(args.input):
        print(f"[ERROR] not a file: {args.input}", file=sys.stderr)
        return 1

    out_path = args.out or os.path.splitext(args.input)[0] + ".png"

    img = Image.open(args.input)
    w, h = img.size
    print(f"[INFO] load {args.input} ({w}x{h}), mode={args.mode}, tolerance={args.tolerance}")

    out, cand, core, halo, matte, grid = chroma_key(
        img,
        args.tolerance,
        args.halo_passes,
        args.halo_max_sat,
        mode=args.mode,
        min_component_area=args.min_component_area,
        min_component_ratio=args.min_component_ratio,
        bg_min_purity=args.bg_min_purity,
        halo_min_margin=args.halo_min_margin,
        matte_cleanup=args.matte_cleanup,
        matte_min_area=args.matte_min_area,
        matte_min_fill=args.matte_min_fill,
        grid_cleanup=args.grid_cleanup,
        grid_band_radius=args.grid_band_radius,
        grid_max_sat=args.grid_max_sat,
    )
    print(f"[INFO] magenta candidate pixels: {cand}")
    print(f"[INFO] background-core pixels: {core}")
    print(f"[INFO] halo pixels absorbed: {halo}")
    print(f"[INFO] light matte pixels cleaned: {matte}")
    print(f"[INFO] grid pixels cleaned: {grid}")
    print(f"[INFO] candidate without core: {cand - core}  (kept opaque if not in halo)")

    out.save(out_path, "PNG")
    print(f"[OK] -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
