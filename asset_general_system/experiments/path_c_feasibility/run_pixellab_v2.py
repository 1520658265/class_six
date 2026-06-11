from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
TOOLS_AI = REPO / "tools" / "ai"
if str(TOOLS_AI) not in sys.path:
    sys.path.insert(0, str(TOOLS_AI))

from pixellab_v2_client import PixelLabV2Client, PixelLabV2Error, format_balance  # noqa: E402


# 生成模式配置
# mode: "image" = 单图生成 (create_pixen), "tileset" = Wang瓦片集 (create_tileset)
CASES = {
    # 暂时注释掉单图生成，只测试 tileset
    # "grass_3x3_patch": {
    #     "mode": "image",
    #     "size": (192, 192),
    #     "prompt": "grass_3x3_patch.txt",
    # },
    # "grass_to_plaza_3x3_patch": {
    #     "mode": "image",
    #     "size": (192, 192),
    #     "prompt": "grass_to_plaza_3x3_patch.txt",
    # },
    # "road_cross_3x3_patch": {
    #     "mode": "image",
    #     "size": (192, 192),
    #     "prompt": "road_cross_3x3_patch.txt",
    # },
    # "track_curve_4x4_patch": {
    #     "mode": "image",
    #     "size": (256, 256),
    #     "prompt": "track_curve_4x4_patch.txt",
    # },
    # Tileset 示例（草地→广场过渡 Wang 瓦片集）
    "grass_plaza_tileset": {
        "mode": "tileset",
        "tile_size": 32,
        "prompt": "grass_plaza_tileset.txt",  # 包含 lower/upper/transition 三段描述
    },
}


def adapt_prompt_image(prompt: str) -> str:
    """适配单图生成的 prompt"""
    return (
        prompt
        + "\n\nPixelLab-specific requirements:\n"
        + "- Generate pixel art directly at the requested canvas size.\n"
        + "- This is opaque terrain art, so no transparent background.\n"
        + "- Keep the entire canvas filled with terrain pixels.\n"
        + "- Do not add an outer transparent margin.\n"
    )


def parse_tileset_prompt(prompt_text: str) -> dict[str, str]:
    """
    解析 tileset prompt，期望格式:
    [LOWER]
    草地描述...
    [UPPER]
    广场描述...
    [TRANSITION]
    过渡描述...
    """
    sections = {"lower": "", "upper": "", "transition": ""}
    current_section = None

    for line in prompt_text.splitlines():
        line = line.strip()
        if line == "[LOWER]":
            current_section = "lower"
        elif line == "[UPPER]":
            current_section = "upper"
        elif line == "[TRANSITION]":
            current_section = "transition"
        elif current_section and line:
            sections[current_section] += line + " "

    # 清理尾部空格
    return {k: v.strip() for k, v in sections.items()}


def generate_image(client: PixelLabV2Client, case_id: str, spec: dict, prompt_dir: Path) -> dict:
    """生成单图 (create_pixen)"""
    prompt_text = (prompt_dir / spec["prompt"]).read_text(encoding="utf-8")
    prompt = adapt_prompt_image(prompt_text)
    width, height = spec["size"]

    print(f"[image] {case_id}: {width}x{height}")
    result = client.create_pixen(
        description=prompt,
        width=width,
        height=height,
        no_background=False,
        outline="selective outline",
        detail="highly detailed",
        view="high top-down",
        direction="south",
    )

    return {
        "type": "image",
        "image": result.image,
        "size": [width, height],
        "usage": result.usage,
        "raw_response_keys": sorted(result.raw_response.keys()),
    }


def generate_tileset(client: PixelLabV2Client, case_id: str, spec: dict, prompt_dir: Path) -> dict:
    """生成 Wang 瓦片集 (create_tileset)"""
    prompt_text = (prompt_dir / spec["prompt"]).read_text(encoding="utf-8")
    sections = parse_tileset_prompt(prompt_text)
    tile_size = spec.get("tile_size", 32)

    if not all(sections.values()):
        raise ValueError(f"{case_id}: tileset prompt 必须包含 [LOWER]/[UPPER]/[TRANSITION] 三段")

    print(f"[tileset] {case_id}: tile_size={tile_size}")
    tileset_result = client.create_tileset(
        lower_description=sections["lower"],
        upper_description=sections["upper"],
        transition_description=sections["transition"],
        tile_size=tile_size,
        transition_size=0.5,
        view="high top-down",
        outline="selective outline",
        detail="medium detail",
    )

    # tileset 返回的是 tiles 数组，每个 tile 有自己的 image
    tileset_data = tileset_result.get("tileset", {})
    tiles = tileset_data.get("tiles", [])
    if not tiles:
        raise ValueError(f"tileset API 未返回 tiles: {tileset_result}")

    print(f"[tileset] tiles count: {len(tiles)}, tile_size: {tileset_data.get('tile_size')}")

    # 拼接所有 tiles 成一张 sheet（4x4 grid for 16 tiles）
    from PIL import Image
    import base64, io, math

    tile_w = tileset_data["tile_size"]["width"]
    tile_h = tileset_data["tile_size"]["height"]

    # 计算网格尺寸（假设是方阵）
    n_tiles = len(tiles)
    grid_size = math.ceil(math.sqrt(n_tiles))

    sheet = Image.new("RGBA", (tile_w * grid_size, tile_h * grid_size), (0, 0, 0, 0))

    for i, tile in enumerate(tiles):
        row = i // grid_size
        col = i % grid_size

        image_b64 = tile.get("image", {})
        if isinstance(image_b64, dict):
            image_b64 = image_b64.get("base64", "")

        if not image_b64:
            print(f"[warn] tile {i} ({tile.get('id')}) missing image, skipping")
            continue

        raw = base64.b64decode(image_b64)
        tile_img = Image.open(io.BytesIO(raw)).convert("RGBA")
        sheet.paste(tile_img, (col * tile_w, row * tile_h))

    return {
        "type": "tileset",
        "image": sheet,
        "tile_size": tile_size,
        "tileset_id": tileset_result.get("tileset_id"),
        "tiles_count": len(tiles),
        "usage": tileset_result.get("usage", {}),
        "raw_response_keys": sorted(tileset_result.keys()),
    }


def main() -> int:
    prompt_dir = ROOT / "prompts"
    raw_dir = ROOT / "raw_pixellab"
    raw_dir.mkdir(parents=True, exist_ok=True)

    client = PixelLabV2Client(timeout=180)
    try:
        balance = client.get_balance()
        print(f"[balance] {format_balance(balance)}")
    except Exception as exc:
        print(f"[warn] balance check failed: {exc}")

    manifest = []
    for case_id, spec in CASES.items():
        mode = spec.get("mode", "image")
        out_path = raw_dir / f"{case_id}.png"

        try:
            if mode == "image":
                gen_result = generate_image(client, case_id, spec, prompt_dir)
            elif mode == "tileset":
                gen_result = generate_tileset(client, case_id, spec, prompt_dir)
            else:
                raise ValueError(f"未知 mode: {mode}")

            # 保存图像
            gen_result["image"].save(out_path)

            # 构建 metadata
            metadata = {
                "case_id": case_id,
                "status": "ok",
                "mode": mode,
                "path": str(out_path.relative_to(ROOT)),
                **{k: v for k, v in gen_result.items() if k != "image"},
            }

            (raw_dir / f"{case_id}.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            manifest.append(metadata)
            print(f"[ok] -> {out_path}")

        except PixelLabV2Error as exc:
            print(f"[error] {case_id}: {exc}")
            manifest.append({"case_id": case_id, "status": "failed", "error": str(exc)})
        except Exception as exc:
            print(f"[error] {case_id}: {exc}")
            manifest.append({"case_id": case_id, "status": "failed", "error": str(exc)})

    (raw_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(item.get("status") == "ok" for item in manifest) else 1


if __name__ == "__main__":
    raise SystemExit(main())
