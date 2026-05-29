"""Retry only sheet B with shorter prompt."""
import base64, json, sys, urllib.request
from pathlib import Path

AI_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AI_DIR))

from ai_config import get_service_config  # noqa: E402

OUT = Path(__file__).parent

PROMPT_B = (
    "Chinese rural road pixel-art tileset, 2D top-down RPG, 32x32 per tile, "
    "4 columns x 3 rows = 12 tiles, 1px black gridline between tiles. "
    "Row1: dead-end road pointing down, dead-end up, dead-end left, dead-end right. "
    "Row2: stone-paved horizontal path, stone-paved vertical path, "
    "muddy road with puddle, dirt road with cart wheel tracks. "
    "Row3: road covered in fallen autumn leaves, road edge with wildflowers, "
    "small wooden bridge, road junction with wooden signpost. "
    "Warm brown dirt #8B6F47, grey pebbles, muted green grass #7A8B5C, "
    "hard pixel edges, no anti-aliasing, no gradients, no shadows, 16-bit JRPG style."
)

config = get_service_config(
    "road_tileset",
    env_prefix="ROAD_TILESET",
    default_host="bobdong.cn",
    default_model="gpt-image-2",
)
api_url = f"https://{config['api_host']}/v1/images/generations"
payload = {"model": config["model"], "prompt": PROMPT_B, "n": 1, "size": "1024x1024"}
req = urllib.request.Request(
    api_url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {config['api_key']}", "Content-Type": "application/json"},
    method="POST",
)

for attempt in range(1, 4):
    print(f"[sheet_b] attempt {attempt}/3")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        break
    except Exception as e:
        print(f"[sheet_b] failed: {e}", file=sys.stderr)
        body = None

if not body:
    sys.exit(1)

(OUT / "road_sheet_b_variants_response.json").write_text(
    json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8"
)
item = body["data"][0]
out_png = OUT / "road_sheet_b_variants.png"
if item.get("url"):
    urllib.request.urlretrieve(item["url"], out_png)
else:
    out_png.write_bytes(base64.b64decode(item["b64_json"]))
print(f"[sheet_b] saved {out_png} ({out_png.stat().st_size} bytes)")
