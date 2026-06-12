"""
Grass tile MVP — Gemini → 可平铺 64×64 像素 tile 的最小验证管线。

五阶段：
  0. PIL 程序化生成一张「像素草地种子图」（破 IMAGE_RECITATION 用 + 锁调色板）
  1. Gemini 以种子图为 reference 出 1024 精修纹理
  2. 纯 PIL offset+gaussian-blend 抹接缝 → 真 seamless 1024
  3. k-means 量化 + nearest 下采样 → 64×64 tile
  4. 自铺 4×4 预览，肉眼验接缝

输出全部落在 tools/ai/out/tilegen/grass_v1/。
重跑时加 --skip-gen 复用已有 01_source_1024.png（省 Gemini 调用）。

依赖：requests, Pillow, numpy
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
TOOLS_AI = HERE.parent
sys.path.insert(0, str(TOOLS_AI))
from ai_config import get_service_config  # noqa: E402

DEFAULT_OUT_DIR = TOOLS_AI / "out" / "tilegen" / "grass_v1"

GRASS_PROMPT = """The attached reference image is a top-down RPG world map illustration in the
art style I want to match. Look carefully at the GRASS regions in the reference
(the green areas around the fountain plaza, between buildings, and near the
soccer field).

Your task: produce a square close-up illustration of ONLY a patch of grass,
zoomed in on the same kind of grass as the reference image, painted in the
exact same art style as the reference.

Style to match (from the reference):
- Multiple distinct shades of green visible as confident flat color blocks
  (not blended gradients): brighter sunlit green, mid grass green, slightly
  darker shadow green tufts, occasional yellow-green and darker olive accents
- Painterly stippled texture from many small dab-like brushstrokes that
  suggest individual grass blades, but each dab is its own confident color
- Top-down RPG game illustration aesthetic — pixel-art-adjacent painterly
  style, NOT photorealistic, NOT smooth airbrushed

Composition for this output:
- The output is a CLOSE-UP zoom of one continuous grass area, as if the camera
  zoomed in onto a grass patch of the reference image and cropped a square out
- The whole canvas is filled edge-to-edge with grass texture only
- Subtle natural variation across the canvas (lighter patches, darker tufts,
  occasional small clumps), but no single feature dominates
- The four edges of the canvas should connect smoothly when the artwork is
  repeated as a wallpaper pattern

Strict content constraints — do NOT include any of these:
- No buildings, no roofs, no walls, no fences, no signs, no banners
- No paths, no roads, no stone tiles, no dirt patches, no water
- No trees, no bushes, no flowers, no rocks, no mushrooms
- No characters, no animals, no insects, no shadows of external objects
- No fountains, no statues, no benches, no soccer goals, no playground equipment
- ONLY grass fills every part of the canvas

Forbidden compositional elements:
- No frame, no border, no outline rectangle around the artwork
- No text, no labels, no captions, no signatures, no watermarks anywhere
- No multi-panel composition, no thumbnails, no example variations side by side
- Flat even ambient lighting; no directional shadows from outside the frame,
  no vignette, no bright spots, no dark corners"""

TARGET_TILE_SIZE = 64
PALETTE_COLORS = 16
SEAM_FEATHER_PX = 80          # 接缝混合带宽（1024 图上 80px ≈ 8%）
PREVIEW_REPEAT = 4
GEMINI_IMAGE_SIZE = "1K"
GEMINI_ASPECT = "1:1"
MAX_ATTEMPTS = 4
RETRY_DELAY_SEC = 2.0


# --------------------------------------------------------------------------- #
# Stage 0: Procedural seed image (避 IMAGE_RECITATION + 锁调色板)
# --------------------------------------------------------------------------- #

# 8 色草地调色板（深森林绿 → 浅奶油绿 + 一个阴影色）
SEED_PALETTE = np.array([
    [42,  77,  26],   # 深森林绿
    [58,  99,  36],   # 暗绿
    [76,  122, 40],   # 中绿
    [105, 152, 50],   # 中亮绿
    [140, 180, 65],   # 黄绿
    [170, 200, 90],   # 亮黄绿
    [200, 220, 130],  # 浅奶油绿（高光）
    [50,  75,  28],   # 阴影绿
], dtype=np.uint8)
# 各色出现概率（深绿/暗绿为底，亮色稀疏）
SEED_WEIGHTS = np.array([0.20, 0.25, 0.20, 0.15, 0.10, 0.04, 0.02, 0.04])
SEED_BLOCK_SIZE = 4   # 像素块边长
SEED_SIZE = 384       # 种子图尺寸（够小不喧宾夺主、够大让 Gemini 看清调色板）
SEED_RNG_SEED = 20260611


def stage0_make_seed(out_path: Path, size: int = SEED_SIZE,
                     block_size: int = SEED_BLOCK_SIZE) -> Path:
    """
    程序化生成像素草地种子图。
    每 block_size×block_size 一个色块，从 SEED_PALETTE 按 SEED_WEIGHTS 抽样。
    最后叠一层小幅噪声打破整齐排列。
    """
    rng = np.random.default_rng(seed=SEED_RNG_SEED)
    n = size // block_size

    weights = SEED_WEIGHTS / SEED_WEIGHTS.sum()
    indices = rng.choice(len(SEED_PALETTE), size=(n, n), p=weights)
    block_img = SEED_PALETTE[indices]
    block_img = np.repeat(np.repeat(block_img, block_size, axis=0), block_size, axis=1)

    noise = rng.integers(-6, 6, size=block_img.shape, dtype=np.int16)
    seed_arr = np.clip(block_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(seed_arr).save(out_path)
    print(f"[stage0] -> {out_path} ({size}x{size}, {n}x{n} blocks of {block_size}px)")
    return out_path


# --------------------------------------------------------------------------- #
# Stage 1: Gemini generate base texture (with seed as reference)
# --------------------------------------------------------------------------- #

def _encode_image_part(path: Path) -> dict:
    """读本地图返回 Gemini inlineData 格式。"""
    mime, _ = mimetypes.guess_type(str(path))
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"inlineData": {"mimeType": mime, "data": b64}}


def stage1_generate(out_path: Path, prompt: str, ref_paths: list[Path] | None = None) -> Path:
    """调 Gemini 生成 1024 原始纹理。失败抛异常。带 ref_paths 时作为 multimodal 参考。"""
    config = get_service_config(
        "gemini_image",
        env_prefix="GEMINI_IMAGE",
        default_host="bobdong.cn",
        default_model="gemini-3.1-flash-image-preview",
    )
    endpoint = (
        f"https://{config['api_host']}/v1beta/models/"
        f"{config['model']}:generateContent?key={config['api_key']}"
    )
    parts: list[dict] = []
    for ref in (ref_paths or []):
        if not ref.is_file():
            raise RuntimeError(f"reference 图不存在: {ref}")
        parts.append(_encode_image_part(ref))
    parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "imageSize": GEMINI_IMAGE_SIZE,
                "aspectRatio": GEMINI_ASPECT,
            },
        },
    }
    print(f"[stage1] 调 Gemini ({config['model']} @ {config['api_host']})")
    print(f"[stage1] prompt {len(prompt)} chars, refs={len(ref_paths or [])}, "
          f"size={GEMINI_IMAGE_SIZE}, aspect={GEMINI_ASPECT}")

    resp = None
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=300,
            )
            print(f"[stage1] attempt {attempt}/{MAX_ATTEMPTS} HTTP {resp.status_code}, {len(resp.content)} bytes")
            break
        except requests.exceptions.RequestException as e:
            last_error = e
            print(f"[stage1] attempt {attempt} 失败: {type(e).__name__}: {e}")
            if attempt == MAX_ATTEMPTS:
                raise RuntimeError(f"Gemini 请求 {MAX_ATTEMPTS} 次全失败: {last_error}")
            time.sleep(RETRY_DELAY_SEC * attempt)

    assert resp is not None
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:500]}")

    data = resp.json()
    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(base64.b64decode(inline.get("data", "")))
            print(f"[stage1] -> {out_path}")
            return out_path
    raise RuntimeError(f"Gemini 响应里没有图: {json.dumps(data, ensure_ascii=False)[:500]}")


# --------------------------------------------------------------------------- #
# Stage 2: Make seamless (pure PIL + numpy, no extra Gemini call)
# --------------------------------------------------------------------------- #

def stage2_make_seamless(src: Path, out_path: Path, feather: int = SEAM_FEATHER_PX) -> Path:
    """
    offset-and-blend 抹接缝：
      1. np.roll 把图水平/垂直各偏移半张，原本在边缘的接缝跑到图中央十字带
      2. 用高斯模糊版本作为「接缝填充料」
      3. 中央十字带（宽 feather）按 alpha 渐变混合 blurred → 抹掉接缝
      4. 反向 roll 回去，此时四条边天然能对接

    grass 这种高频纹理，模糊后视觉上几乎看不出接缝带。
    """
    img = Image.open(src).convert("RGB")
    arr = np.array(img, dtype=np.float32)
    h, w = arr.shape[:2]
    print(f"[stage2] 输入 {w}x{h}, feather={feather}px")

    rolled = np.roll(np.roll(arr, h // 2, axis=0), w // 2, axis=1)

    rolled_img = Image.fromarray(rolled.astype(np.uint8))
    blurred_img = rolled_img.filter(ImageFilter.GaussianBlur(radius=feather / 3.0))
    blurred = np.array(blurred_img, dtype=np.float32)

    cy, cx = h // 2, w // 2
    xs = np.arange(w)
    ys = np.arange(h)
    dx = np.abs(xs - cx)
    dy = np.abs(ys - cy)
    alpha_x = np.clip(1.0 - dx / feather, 0.0, 1.0)  # 列方向接缝权重
    alpha_y = np.clip(1.0 - dy / feather, 0.0, 1.0)  # 行方向接缝权重
    alpha = np.maximum(alpha_x[None, :], alpha_y[:, None])  # 取并集 → 十字带
    alpha3 = alpha[:, :, None]

    fixed = alpha3 * blurred + (1.0 - alpha3) * rolled
    result = np.roll(np.roll(fixed, -h // 2, axis=0), -w // 2, axis=1)
    result_img = Image.fromarray(np.clip(result, 0, 255).astype(np.uint8))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_img.save(out_path)
    print(f"[stage2] -> {out_path}")
    return out_path


# --------------------------------------------------------------------------- #
# Stage 3: Concept-art → pixel-tile 规范化
# --------------------------------------------------------------------------- #

def stage3_pixelize(src: Path, out_path: Path, target: int = TARGET_TILE_SIZE,
                    n_colors: int = PALETTE_COLORS,
                    posterize_bits: int = 4,
                    bilateral_d: int = 15,
                    bilateral_sigma: int = 75) -> Path:
    """
    把 Gemini 出的概念画规范化为像素 tile：
      a. cv2 bilateral filter — 保边平滑，把笔触边界拉直成更规整色块边界
                                 （边缘不模糊，平面区域内部抹平）
      b. ImageOps.posterize — 削掉细微渐变，每通道压到 2^bits 级
      c. lanczos 到 2×target — 平滑下采，避免一刀切引入 moiré
      d. nearest 到 target — 硬边缘像素化
      e. PIL.quantize MEDIANCUT + kmeans — 锁死调色板到 n_colors
      f. 最终位图 RGB

    与旧版区别：
    - 旧版只有 lanczos→nearest→量化，平涂感不够
    - 新版前置 bilateral + posterize 强制色块化，像素风更立得住
    """
    import cv2  # 在用时再导入；项目里已确认装着

    img = Image.open(src).convert("RGB")
    print(f"[stage3] 输入 {img.size}, 目标 {target}x{target}, palette={n_colors}")

    arr = np.array(img)
    bilateral = cv2.bilateralFilter(arr, d=bilateral_d,
                                    sigmaColor=bilateral_sigma,
                                    sigmaSpace=bilateral_sigma)
    smoothed = Image.fromarray(bilateral)
    print(f"[stage3]   a. bilateral d={bilateral_d}, sigma={bilateral_sigma}")

    from PIL import ImageOps
    posterized = ImageOps.posterize(smoothed, bits=posterize_bits)
    print(f"[stage3]   b. posterize bits={posterize_bits} ({2**posterize_bits} levels/channel)")

    intermediate = posterized.resize((target * 2, target * 2), Image.LANCZOS)
    small = intermediate.resize((target, target), Image.NEAREST)
    print(f"[stage3]   c+d. lanczos→{target*2}x{target*2}→nearest→{target}x{target}")

    quantized = small.quantize(colors=n_colors,
                               method=Image.Quantize.MEDIANCUT,
                               kmeans=3,
                               dither=Image.Dither.NONE)
    final_rgb = quantized.convert("RGB")
    print(f"[stage3]   e. mediancut+kmeans 量化 → {n_colors} 色")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    final_rgb.save(out_path)
    print(f"[stage3] -> {out_path}")
    return out_path


# --------------------------------------------------------------------------- #
# Stage 4: Preview (tile NxN to verify seam)
# --------------------------------------------------------------------------- #

def stage4_preview(src: Path, out_path: Path, repeat: int = PREVIEW_REPEAT,
                   upscale: int = 4) -> Path:
    """
    把 tile 自铺 repeat×repeat，再整体放大 upscale 倍方便肉眼看。
    放大用 NEAREST 保持像素硬边缘。
    """
    tile = Image.open(src).convert("RGB")
    tw, th = tile.size
    canvas = Image.new("RGB", (tw * repeat, th * repeat))
    for y in range(repeat):
        for x in range(repeat):
            canvas.paste(tile, (x * tw, y * th))

    if upscale > 1:
        canvas = canvas.resize((canvas.width * upscale, canvas.height * upscale), Image.NEAREST)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    print(f"[stage4] -> {out_path} ({canvas.size[0]}x{canvas.size[1]})")
    return out_path


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else "")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                   help=f"输出目录（默认 {DEFAULT_OUT_DIR}）")
    p.add_argument("--skip-gen", action="store_true",
                   help="跳过阶段 1，复用已存在的 01_source_1024.png（省 Gemini 调用）")
    p.add_argument("--use-seed", action="store_true",
                   help="开启程序化噪声 seed 作为 Gemini ref（v1 旧路径，默认关闭）")
    p.add_argument("--user-ref", type=Path, default=None,
                   help="用户提供的参考图路径，作为 Gemini multimodal ref（v3 推荐）")
    p.add_argument("--feather", type=int, default=SEAM_FEATHER_PX,
                   help=f"接缝混合带宽像素（默认 {SEAM_FEATHER_PX}）")
    p.add_argument("--target", type=int, default=TARGET_TILE_SIZE,
                   help=f"最终 tile 边长（默认 {TARGET_TILE_SIZE}）")
    p.add_argument("--colors", type=int, default=PALETTE_COLORS,
                   help=f"调色板颜色数（默认 {PALETTE_COLORS}）")
    p.add_argument("--repeat", type=int, default=PREVIEW_REPEAT,
                   help=f"预览图自铺次数（默认 {PREVIEW_REPEAT}）")
    p.add_argument("--posterize-bits", type=int, default=4,
                   help="阶段 3 posterize 每通道位数（默认 4 = 16 阶；调小=色块更狠）")
    p.add_argument("--bilateral-sigma", type=int, default=75,
                   help="阶段 3 bilateral filter sigma（默认 75；调大=色块更整齐但细节更糊）")
    args = p.parse_args()

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    p00 = out_dir / "00_seed.png"
    p01 = out_dir / "01_source_1024.png"
    p02 = out_dir / "02_seamless_1024.png"
    p03 = out_dir / f"03_tile_{args.target}.png"
    p04 = out_dir / f"04_preview_{args.repeat}x{args.repeat}.png"

    print(f"[main] 输出目录: {out_dir}")

    ref_paths: list[Path] = []

    # 用户参考图（v3 路线 B：直接锁风格）
    if args.user_ref is not None:
        ur = args.user_ref.expanduser().resolve()
        if not ur.is_file():
            print(f"[ERROR] --user-ref 文件不存在: {ur}")
            return 1
        ref_paths.append(ur)
        print(f"[ref] 用户参考图: {ur}")

    # 程序化噪声 seed（v1 旧路径，默认关）
    if args.use_seed:
        try:
            stage0_make_seed(p00)
            ref_paths.append(p00)
        except Exception as e:
            print(f"[ERROR] 阶段 0 失败: {e}")
            return 1
    else:
        print("[stage0] 跳过 (默认 v3 路径)")

    if args.skip_gen:
        if not p01.exists():
            print(f"[ERROR] --skip-gen 但 {p01} 不存在")
            return 1
        print(f"[stage1] 跳过 (复用 {p01})")
    else:
        try:
            stage1_generate(p01, GRASS_PROMPT, ref_paths=ref_paths)
        except Exception as e:
            print(f"[ERROR] 阶段 1 失败: {e}")
            return 1

    try:
        stage2_make_seamless(p01, p02, feather=args.feather)
        stage3_pixelize(p02, p03, target=args.target, n_colors=args.colors,
                        posterize_bits=args.posterize_bits,
                        bilateral_sigma=args.bilateral_sigma)
        stage4_preview(p03, p04, repeat=args.repeat)
    except Exception as e:
        print(f"[ERROR] 后处理阶段失败: {e}")
        return 1

    print()
    print("[main] === 完成 ===")
    print(f"  种子:   {p00}")
    print(f"  原始:   {p01}")
    print(f"  无缝:   {p02}")
    print(f"  最终:   {p03}")
    print(f"  预览:   {p04}")
    print()
    print("[main] 我看不到图，请你打开 04_preview 验收：")
    print("  1. 拼接处有没有可见接缝（横竖线）？")
    print("  2. 像素是否清晰（不糊）？")
    print("  3. 整体颜色/风格是否符合需求？")
    print("  4. 03_tile 单格放大看是否还像草地？")
    return 0


if __name__ == "__main__":
    sys.exit(main())
