"""Generate Chinese rural road tileset, split into 2 sub-sheets to avoid 524 timeout.

Sheet A (basic 12 tiles, 4x3): straights, cross, T-junctions, corners, dead-ends.
Sheet B (variant 12 tiles, 4x3): stone paths, muddy, cart tracks, leaves, wildflowers, bridge, signpost, isolated.
"""
import base64
import json
import sys
import urllib.request
from pathlib import Path

AI_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AI_DIR))

from ai_config import get_service_config  # noqa: E402

OUT_DIR = Path(__file__).parent

STYLE_TAIL = (
    "Style: traditional Chinese countryside, warm brown dirt #8B6F47, "
    "scattered grey pebbles, muted green grass background #7A8B5C, "
    "hard pixel edges, no anti-aliasing, no gradients, no shadows, "
    "flat 2D top-down, 16-bit JRPG aesthetic, cohesive limited palette, "
    "1px black gridline between tiles for easy slicing in Godot."
)

PROMPT_A = (
    "Chinese rural dirt-road pixel-art tileset for 2D RPG, top-down 32x32 per tile, "
    "4 columns x 3 rows = 12 tiles. "
    "Row1: horizontal straight road, vertical straight road, 4-way cross intersection, isolated single road patch. "
    "Row2: T-junction opening down, T-junction opening up, T-junction opening right, T-junction opening left. "
    "Row3: corner top-left, corner top-right, corner bottom-left, corner bottom-right. "
    + STYLE_TAIL
)

PROMPT_B = (
    "Chinese rural road pixel-art variant tileset for 2D RPG, top-down 32x32 per tile, "
    "4 columns x 3 rows = 12 tiles. "
    "Row1: dead-end pointing down, dead-end pointing up, dead-end pointing left, dead-end pointing right. "
    "Row2: stone paved horizontal path, stone paved vertical path, "
    "muddy road with puddle, dirt road with cart wheel tracks. "
    "Row3: road with fallen autumn leaves, road edge with wildflowers, "
    "small wooden bridge segment, road junction with wooden signpost. "
    + STYLE_TAIL
)


def call_api(prompt: str) -> dict:
    config = get_service_config(
        "road_tileset",
        env_prefix="ROAD_TILESET",
        default_host="bobdong.cn",
        default_model="gpt-image-2",
    )
    api_url = f"https://{config['api_host']}/v1/images/generations"
    payload = {"model": config["model"], "prompt": prompt, "n": 1, "size": "1024x1024"}
    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode("utf-8"))


def save_image(body: dict, out_png: Path) -> None:
    item = body["data"][0]
    if item.get("url"):
        urllib.request.urlretrieve(item["url"], out_png)
    elif item.get("b64_json"):
        out_png.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        raise RuntimeError(f"no url or b64_json: {item}")


def gen(label: str, prompt: str) -> int:
    print(f"[{label}] requesting...")
    try:
        body = call_api(prompt)
    except Exception as e:
        print(f"[{label}] FAILED: {e}", file=sys.stderr)
        return 1
    raw = OUT_DIR / f"road_{label}_response.json"
    raw.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    png = OUT_DIR / f"road_{label}.png"
    save_image(body, png)
    print(f"[{label}] saved {png} ({png.stat().st_size} bytes)")
    return 0


def main() -> int:
    rc = 0
    rc |= gen("sheet_a_basic", PROMPT_A)
    rc |= gen("sheet_b_variants", PROMPT_B)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
