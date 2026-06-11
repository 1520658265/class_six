from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


CASES = {
    "grass_3x3_patch": {"grid": [3, 3], "tile_size": 64},
    "grass_to_plaza_3x3_patch": {"grid": [3, 3], "tile_size": 64},
    "road_cross_3x3_patch": {"grid": [3, 3], "tile_size": 64},
    "track_curve_4x4_patch": {"grid": [4, 4], "tile_size": 64},
}


def find_raw(raw_dir: Path, case_id: str) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = raw_dir / f"{case_id}{ext}"
        if path.exists():
            return path
    return None


def mean_abs_diff(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / len(stat.mean))


def border_metrics(tiles: list[list[Image.Image]], tile_size: int) -> dict:
    horizontal = []
    vertical = []
    rows = len(tiles)
    cols = len(tiles[0]) if rows else 0
    for y in range(rows):
        for x in range(cols - 1):
            left_edge = tiles[y][x].crop((tile_size - 1, 0, tile_size, tile_size))
            right_edge = tiles[y][x + 1].crop((0, 0, 1, tile_size))
            horizontal.append(mean_abs_diff(left_edge, right_edge))
    for y in range(rows - 1):
        for x in range(cols):
            top_edge = tiles[y][x].crop((0, tile_size - 1, tile_size, tile_size))
            bottom_edge = tiles[y + 1][x].crop((0, 0, tile_size, 1))
            vertical.append(mean_abs_diff(top_edge, bottom_edge))
    all_values = horizontal + vertical
    return {
        "mean_border_delta": round(sum(all_values) / len(all_values), 2) if all_values else 0.0,
        "max_border_delta": round(max(all_values), 2) if all_values else 0.0,
        "horizontal": [round(v, 2) for v in horizontal],
        "vertical": [round(v, 2) for v in vertical],
    }


def save_grid_overlay(img: Image.Image, out_path: Path, grid: tuple[int, int], tile_size: int) -> None:
    overlay = img.convert("RGBA")
    px = overlay.load()
    width, height = overlay.size
    for x in range(tile_size, width, tile_size):
        for y in range(height):
            px[x, y] = (255, 0, 0, 180)
    for y in range(tile_size, height, tile_size):
        for x in range(width):
            px[x, y] = (255, 0, 0, 180)
    overlay.save(out_path)


def process_case(root: Path, case_id: str, spec: dict, raw_dir_name: str, output_suffix: str) -> dict:
    raw_dir = root / raw_dir_name
    sliced_dir = root / f"sliced{output_suffix}" / case_id
    recomposed_dir = root / f"recomposed{output_suffix}"
    reports_dir = root / f"reports{output_suffix}"
    sliced_dir.mkdir(parents=True, exist_ok=True)
    recomposed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    raw_path = find_raw(raw_dir, case_id)
    result = {
        "case_id": case_id,
        "status": "missing_raw",
        "raw_path": str(raw_path) if raw_path else None,
        "raw_dir_name": raw_dir_name,
    }
    if not raw_path:
        return result

    grid_w, grid_h = spec["grid"]
    tile_size = spec["tile_size"]
    target_size = (grid_w * tile_size, grid_h * tile_size)

    img = Image.open(raw_path).convert("RGBA")
    original_size = img.size
    normalized = img.resize(target_size, Image.Resampling.LANCZOS)
    normalized_path = recomposed_dir / f"{case_id}_normalized.png"
    normalized.save(normalized_path)

    tiles: list[list[Image.Image]] = []
    tile_paths = []
    for y in range(grid_h):
        row = []
        for x in range(grid_w):
            tile = normalized.crop((x * tile_size, y * tile_size, (x + 1) * tile_size, (y + 1) * tile_size))
            tile_path = sliced_dir / f"{case_id}_r{y}_c{x}.png"
            tile.save(tile_path)
            row.append(tile)
            tile_paths.append(str(tile_path.relative_to(root)))
        tiles.append(row)

    recomposed = Image.new("RGBA", target_size)
    for y, row in enumerate(tiles):
        for x, tile in enumerate(row):
            recomposed.alpha_composite(tile, (x * tile_size, y * tile_size))
    recomposed_path = recomposed_dir / f"{case_id}_recomposed.png"
    recomposed.save(recomposed_path)

    overlay_path = recomposed_dir / f"{case_id}_grid_overlay.png"
    save_grid_overlay(normalized, overlay_path, (grid_w, grid_h), tile_size)

    repeat_path = None
    if grid_w >= 3 and grid_h >= 3:
        center = tiles[grid_h // 2][grid_w // 2]
        repeat = Image.new("RGBA", (tile_size * 4, tile_size * 4))
        for y in range(4):
            for x in range(4):
                repeat.alpha_composite(center, (x * tile_size, y * tile_size))
        repeat_path = recomposed_dir / f"{case_id}_center_repeat_4x4.png"
        repeat.save(repeat_path)

    metrics = border_metrics(tiles, tile_size)
    report = {
        "case_id": case_id,
        "status": "processed",
        "raw_path": str(raw_path.relative_to(root)),
        "raw_dir_name": raw_dir_name,
        "original_size": original_size,
        "normalized_path": str(normalized_path.relative_to(root)),
        "recomposed_path": str(recomposed_path.relative_to(root)),
        "grid_overlay_path": str(overlay_path.relative_to(root)),
        "center_repeat_path": str(repeat_path.relative_to(root)) if repeat_path else None,
        "tile_paths": tile_paths,
        "metrics": metrics,
        "manual_review": {
            "patch_visual_ok": None,
            "sliced_tiles_individually_usable": None,
            "recomposed_edges_ok": None,
            "center_repeat_ok": None,
            "role_structure_ok": None,
            "notes": "",
        },
    }
    (reports_dir / f"{case_id}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def generate_review(root: Path, reports: list[dict], output_suffix: str) -> None:
    cards = []
    for report in reports:
        case_id = report["case_id"]
        if report.get("status") != "processed":
            cards.append(f"<section><h2>{html.escape(case_id)}</h2><p>Missing raw image.</p></section>")
            continue
        metrics = report["metrics"]
        images = [
            ("Normalized", report["normalized_path"]),
            ("Grid overlay", report["grid_overlay_path"]),
            ("Recomposed", report["recomposed_path"]),
        ]
        if report.get("center_repeat_path"):
            images.append(("Center repeated 4x4", report["center_repeat_path"]))
        image_html = "\n".join(
            f"<figure><figcaption>{label}</figcaption><img src='{html.escape(path)}'></figure>"
            for label, path in images
        )
        tile_imgs = "\n".join(
            f"<img class='tile' src='{html.escape(path)}' title='{html.escape(path)}'>"
            for path in report["tile_paths"]
        )
        cards.append(
            f"""
            <section>
              <h2>{html.escape(case_id)}</h2>
              <p class="metrics">mean border delta: <b>{metrics['mean_border_delta']}</b>,
              max border delta: <b>{metrics['max_border_delta']}</b></p>
              <div class="images">{image_html}</div>
              <h3>Sliced tiles</h3>
              <div class="tiles">{tile_imgs}</div>
              <textarea readonly>{html.escape(json.dumps(report['manual_review'], ensure_ascii=False, indent=2))}</textarea>
            </section>
            """
        )

    html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Path C Feasibility Review</title>
  <style>
    body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #f5f3ee; color: #1f2933; }}
    header {{ position: sticky; top: 0; background: #ffffff; border-bottom: 1px solid #d8d3c8; padding: 14px 20px; z-index: 5; }}
    h1 {{ margin: 0 0 6px; font-size: 20px; }}
    p {{ margin: 6px 0; }}
    main {{ padding: 20px; display: grid; gap: 20px; }}
    section {{ background: #fff; border: 1px solid #d8d3c8; border-radius: 8px; padding: 16px; }}
    h2 {{ margin: 0 0 8px; font-size: 18px; }}
    h3 {{ margin: 14px 0 8px; font-size: 14px; }}
    .metrics {{ color: #44515f; }}
    .images {{ display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; }}
    figure {{ margin: 0; }}
    figcaption {{ font-size: 12px; color: #5b6773; margin-bottom: 6px; }}
    img {{ image-rendering: pixelated; border: 1px solid #c8c1b5; background: #fff; max-width: 360px; height: auto; }}
    .tile {{ width: 64px; height: 64px; margin: 0 6px 6px 0; }}
    .tiles {{ display: flex; flex-wrap: wrap; max-width: 640px; }}
    textarea {{ width: 100%; min-height: 150px; margin-top: 12px; font-family: Consolas, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>Path C Feasibility Review</h1>
    <p>目标：验证 AI patch 切成 64x64 tile 后是否仍可拼接、复用、解释为 tilemap。</p>
    <p>重点人工看：边缘断裂、可见网格、文字/边框、风格漂移、center 重复铺是否明显接缝。</p>
  </header>
  <main>
    {''.join(cards)}
  </main>
</body>
</html>
"""
    review_name = f"review{output_suffix}.html" if output_suffix else "review.html"
    (root / review_name).write_text(html_doc, encoding="utf-8")


def generate_contact_sheet(root: Path, reports: list[dict], output_suffix: str) -> None:
    rows = []
    for report in reports:
        if report.get("status") != "processed":
            continue
        rows.append(report)
    if not rows:
        return

    cell_w = 320
    cell_h = 320
    label_h = 34
    cols = 4
    sheet = Image.new("RGB", (cell_w * cols, (cell_h + label_h) * len(rows)), (245, 243, 238))

    try:
        from PIL import ImageDraw

        draw = ImageDraw.Draw(sheet)
    except Exception:
        draw = None

    columns = [
        ("normalized", "normalized_path"),
        ("grid overlay", "grid_overlay_path"),
        ("recomposed", "recomposed_path"),
        ("center repeat", "center_repeat_path"),
    ]

    for row_i, report in enumerate(rows):
        y0 = row_i * (cell_h + label_h)
        if draw:
            draw.text((8, y0 + 8), report["case_id"], fill=(31, 41, 51))
        for col_i, (label, key) in enumerate(columns):
            path_value = report.get(key)
            if not path_value:
                continue
            img_path = root / path_value
            if not img_path.exists():
                continue
            img = Image.open(img_path).convert("RGB")
            img.thumbnail((cell_w - 18, cell_h - 18), Image.Resampling.NEAREST)
            x = col_i * cell_w + (cell_w - img.width) // 2
            y = y0 + label_h + (cell_h - img.height) // 2
            sheet.paste(img, (x, y))
            if draw:
                draw.text((col_i * cell_w + 8, y0 + label_h - 18), label, fill=(78, 91, 106))

    out_path = root / f"reports{output_suffix}" / "contact_sheet.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Path C experiment root")
    parser.add_argument("--raw-dir-name", default="raw", help="Raw image directory under root")
    parser.add_argument("--output-suffix", default="", help="Suffix for sliced/recomposed/reports/review outputs, e.g. _pixellab")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    reports = [
        process_case(root, case_id, spec, args.raw_dir_name, args.output_suffix)
        for case_id, spec in CASES.items()
    ]
    generate_review(root, reports, args.output_suffix)
    generate_contact_sheet(root, reports, args.output_suffix)
    summary = {"cases": reports}
    reports_dir = root / f"reports{args.output_suffix}"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    review_name = f"review{args.output_suffix}.html" if args.output_suffix else "review.html"
    print(f"[OK] review: {root / review_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
