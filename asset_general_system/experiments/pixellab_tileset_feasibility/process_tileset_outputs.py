from __future__ import annotations

import base64
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
SOURCE_TILE_SIZE = 32
TARGET_TILE_SIZE = 64


def load_cases() -> dict:
    data = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))
    global SOURCE_TILE_SIZE, TARGET_TILE_SIZE
    SOURCE_TILE_SIZE = int(data.get("tile_size_source", 32))
    TARGET_TILE_SIZE = int(data.get("tile_size_target", 64))
    return data


def iter_image_fields(value: Any, path: str = ""):
    if isinstance(value, dict):
        if isinstance(value.get("base64"), str):
            yield path or "image", value["base64"]
        for key, child in value.items():
            yield from iter_image_fields(child, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            yield from iter_image_fields(child, f"{path}[{idx}]")


def decode_b64_image(b64: str) -> Image.Image | None:
    try:
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        return None


def find_images(raw_json: dict) -> list[tuple[str, Image.Image]]:
    images = []
    for field_path, b64 in iter_image_fields(raw_json):
        img = decode_b64_image(b64)
        if img is not None:
            images.append((field_path, img))
    return images


def slice_sheet(img: Image.Image, tile_size: int) -> list[Image.Image]:
    width, height = img.size
    tiles = []
    if width < tile_size or height < tile_size:
        return [img]
    cols = width // tile_size
    rows = height // tile_size
    if cols == 0 or rows == 0:
        return [img]
    for y in range(rows):
        for x in range(cols):
            tiles.append(img.crop((x * tile_size, y * tile_size, (x + 1) * tile_size, (y + 1) * tile_size)))
    return tiles


def save_contact_sheet(tiles: list[Image.Image], out_path: Path, tile_size: int = TARGET_TILE_SIZE) -> None:
    if not tiles:
        return
    cols = min(8, max(1, len(tiles)))
    rows = (len(tiles) + cols - 1) // cols
    pad = 8
    label_h = 14
    cell = tile_size + pad
    sheet = Image.new("RGBA", (cols * cell + pad, rows * (cell + label_h) + pad), (245, 243, 238, 255))
    draw = ImageDraw.Draw(sheet)
    for idx, tile in enumerate(tiles):
        x = pad + (idx % cols) * cell
        y = pad + (idx // cols) * (cell + label_h)
        draw.text((x, y), str(idx), fill=(31, 41, 51))
        sheet.alpha_composite(tile, (x, y + label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(out_path)


def save_demo_map(tiles: list[Image.Image], out_path: Path) -> None:
    if not tiles:
        return
    width = 10 * TARGET_TILE_SIZE
    height = 10 * TARGET_TILE_SIZE
    demo = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for y in range(10):
        for x in range(10):
            tile = tiles[(x + y * 3) % len(tiles)]
            demo.alpha_composite(tile, (x * TARGET_TILE_SIZE, y * TARGET_TILE_SIZE))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    demo.save(out_path)


def process_case(case: dict) -> dict:
    case_id = case["case_id"]
    raw_path = ROOT / "raw" / f"{case_id}.json"
    decoded_dir = ROOT / "decoded" / case_id
    tiles_dir = ROOT / "tiles_64" / case_id
    previews_dir = ROOT / "previews" / case_id
    decoded_dir.mkdir(parents=True, exist_ok=True)
    tiles_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        return {
            "case_id": case_id,
            "status": "pending_api",
            "message": f"Missing {raw_path.relative_to(ROOT)}. Run run_pixellab_tileset.py --run-api after quota is available.",
        }

    raw_json = json.loads(raw_path.read_text(encoding="utf-8"))
    images = find_images(raw_json)
    if not images:
        return {
            "case_id": case_id,
            "status": "no_decodable_images",
            "raw_json": str(raw_path.relative_to(ROOT)),
            "response_keys": sorted(raw_json.keys()) if isinstance(raw_json, dict) else [],
        }

    source_images = []
    all_tiles_64 = []
    for image_idx, (field_path, img) in enumerate(images):
        image_path = decoded_dir / f"image_{image_idx:02d}.png"
        img.save(image_path)
        source_images.append({
            "field_path": field_path,
            "path": str(image_path.relative_to(ROOT)),
            "size": list(img.size),
        })
        source_tiles = slice_sheet(img, SOURCE_TILE_SIZE)
        for tile_idx, tile in enumerate(source_tiles):
            tile_64 = tile.resize((TARGET_TILE_SIZE, TARGET_TILE_SIZE), Image.Resampling.NEAREST)
            tile_path = tiles_dir / f"tile_{image_idx:02d}_{tile_idx:03d}.png"
            tile_64.save(tile_path)
            all_tiles_64.append(tile_64)

    contact_path = previews_dir / "contact_sheet.png"
    demo_path = previews_dir / "demo_map.png"
    save_contact_sheet(all_tiles_64, contact_path)
    save_demo_map(all_tiles_64, demo_path)

    return {
        "case_id": case_id,
        "status": "processed",
        "raw_json": str(raw_path.relative_to(ROOT)),
        "source_images": source_images,
        "tile_count_64": len(all_tiles_64),
        "contact_sheet": str(contact_path.relative_to(ROOT)),
        "demo_map": str(demo_path.relative_to(ROOT)),
        "manual_review": {
            "decoding_ok": None,
            "connection_signature_mappable": None,
            "scaled_64_ok": None,
            "demo_edges_ok": None,
            "no_artifacts": None,
            "notes": "",
        },
    }


def generate_review(reports: list[dict]) -> None:
    sections = []
    for report in reports:
        case_id = report["case_id"]
        status = report["status"]
        if status != "processed":
            sections.append(
                f"<section><h2>{case_id}</h2><p class='status'>{status}</p><p>{report.get('message', '')}</p></section>"
            )
            continue
        sections.append(
            f"""
            <section>
              <h2>{case_id}</h2>
              <p class="status">{status} | tiles: {report['tile_count_64']}</p>
              <div class="images">
                <figure><figcaption>contact sheet</figcaption><img src="{report['contact_sheet']}"></figure>
                <figure><figcaption>demo map</figcaption><img src="{report['demo_map']}"></figure>
              </div>
              <textarea readonly>{json.dumps(report['manual_review'], ensure_ascii=False, indent=2)}</textarea>
            </section>
            """
        )
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>PixelLab Tileset Feasibility Review</title>
  <style>
    body {{ margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; background: #f5f3ee; color: #1f2933; }}
    header {{ position: sticky; top: 0; background: #fff; border-bottom: 1px solid #d8d3c8; padding: 14px 20px; }}
    main {{ padding: 20px; display: grid; gap: 20px; }}
    section {{ background: #fff; border: 1px solid #d8d3c8; border-radius: 8px; padding: 16px; }}
    h1 {{ margin: 0 0 6px; font-size: 20px; }}
    h2 {{ margin: 0 0 8px; font-size: 18px; }}
    .status {{ color: #52606d; }}
    .images {{ display: flex; flex-wrap: wrap; gap: 18px; }}
    figure {{ margin: 0; }}
    figcaption {{ font-size: 12px; color: #5b6773; margin-bottom: 6px; }}
    img {{ image-rendering: pixelated; border: 1px solid #c8c1b5; background: #fff; max-width: 640px; height: auto; }}
    textarea {{ width: 100%; min-height: 140px; margin-top: 12px; font-family: Consolas, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>PixelLab Tileset Feasibility Review</h1>
    <p>额度恢复后运行 API，再用本页检查 create_tileset 是否能生成可映射到 tilemap 的 transition family。</p>
  </header>
  <main>{''.join(sections)}</main>
</body>
</html>
"""
    (ROOT / "review.html").write_text(html, encoding="utf-8")


def main() -> int:
    config = load_cases()
    reports = [process_case(case) for case in config["cases"]]
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "summary.json").write_text(json.dumps({"cases": reports}, ensure_ascii=False, indent=2), encoding="utf-8")
    generate_review(reports)
    print(f"[OK] review: {ROOT / 'review.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
