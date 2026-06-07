"""
改进版 VFX 生成器 v2

核心改进：
1. 一次 API 调用生成完整 sprite sheet（保证动画连贯性）
2. 强制纯黑背景，用色键算法精确抠透明
3. 边缘羽化，避免锯齿
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# 加载 Gemini 配置
_AI_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "tools" / "ai"
if _AI_CONFIG_PATH.exists() and str(_AI_CONFIG_PATH) not in sys.path:
    sys.path.insert(0, str(_AI_CONFIG_PATH))

try:
    from ai_config import get_service_config
except ImportError:
    def get_service_config(service_name, env_prefix=None, default_host=None, default_model=None):
        api_key = os.getenv(f"{env_prefix}_API_KEY")
        if not api_key:
            raise ValueError(f"{env_prefix}_API_KEY 未设置")
        return {
            "api_key": api_key,
            "api_host": os.getenv(f"{env_prefix}_API_HOST", default_host),
            "model": os.getenv(f"{env_prefix}_MODEL", default_model),
        }


@dataclass
class VFXSheetRequest:
    """VFX sprite sheet 生成请求。"""
    description: str
    frame_size: tuple[int, int] = (512, 512)  # 单帧尺寸（默认 512，匹配 4x4 grid in 2048）
    frame_count: int = 16                     # 帧数（默认 16 = 4x4）
    grid_rows: int = 4
    grid_cols: int = 4
    fps: int = 12
    loop: bool = False
    blend_mode: str = "additive"
    seed: int | None = None
    asset_id: str = "vfx"
    # 可选：用户提供的逐帧故事板（每帧一行描述）
    storyboard: list[str] | None = None


def generate_vfx_sprite_sheet(
    request: VFXSheetRequest,
    output_dir: Path,
) -> dict:
    """
    一次 API 调用生成完整 VFX sprite sheet。

    返回：
        包含 sprite_path、metadata_path 等信息的字典
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 加载配置
    config = get_service_config(
        "gemini_image",
        env_prefix="GEMINI_IMAGE",
        default_host="bobdong.cn",
        default_model="gemini-3.1-flash-image-preview",
    )

    # 2. 构造特殊 prompt - 让 Gemini 生成一张完整 sprite sheet
    fw, fh = request.frame_size
    n_frames = request.frame_count
    sheet_w = fw * n_frames
    sheet_h = fh

    prompt = build_sprite_sheet_prompt(request)

    # 3. 调用 Gemini API（带重试）
    print(f"  生成 sprite sheet ({sheet_w}x{sheet_h}, {n_frames} 帧)...")
    image_data = call_gemini_api(prompt, config, aspect_ratio=_get_aspect(sheet_w, sheet_h))

    if not image_data:
        return {"success": False, "error": "API 调用失败"}

    # 4. 保存原始图像
    raw_path = output_dir / f"{request.asset_id}_raw.png"
    raw_path.write_bytes(image_data)
    print(f"  原始图像: {raw_path}")

    # 4.5 清除 Gemini 偷加的 grid 边框线
    clean_grid_borders(raw_path, request.grid_rows, request.grid_cols)

    # 4.6 Lumakey：黑色背景 → 透明（让 VFX 不遮挡地图）
    apply_lumakey(raw_path)

    # 5. 后处理：调整尺寸 + 移除黑色背景
    sheet_path = output_dir / f"{request.asset_id}.png"
    process_sprite_sheet(
        raw_path,
        sheet_path,
        target_size=(sheet_w, sheet_h),
        frame_count=n_frames,
        frame_size=request.frame_size,
    )

    # 6. 生成 metadata
    metadata = {
        "asset_id": request.asset_id,
        "image": sheet_path.name,
        "frame_size": [fw, fh],
        "frames": n_frames,
        "fps": request.fps,
        "loop": request.loop,
        "blend": request.blend_mode,
        "anchor": "center",
        "category": "combat",
        "tags": [request.asset_id, "vfx"],
        "generated": {
            "timestamp": datetime.now().isoformat(),
            "generator": "gemini/sprite-sheet-v2",
            "prompt": request.description,
            "seed": request.seed or 0,
            "model": config["model"],
        },
    }

    metadata_path = output_dir / f"{request.asset_id}.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "success": True,
        "asset_id": request.asset_id,
        "sprite_path": str(sheet_path),
        "raw_path": str(raw_path),
        "metadata_path": str(metadata_path),
        "metadata": metadata,
    }


def build_sprite_sheet_prompt(request: VFXSheetRequest) -> str:
    """
    构造让 Gemini 生成 sprite sheet 的 prompt（v3：4x4 grid + 逐帧故事板）。

    核心改进：
    1. 明确 4x4 grid 布局（匹配 Gemini 实际行为，2048x2048 方图）
    2. 逐帧故事板（每个 cell 写明该 t 时刻的具体画面）
    3. 反模式警告（不要画 16 张同样的图）
    4. 强调时序连贯性（同一物体跨多帧渐进位移）
    """
    rows = request.grid_rows
    cols = request.grid_cols
    n = rows * cols
    fw, fh = request.frame_size
    sheet_w = fw * cols
    sheet_h = fh * rows

    # 默认故事板（如果用户没提供）：3 阶段平滑过渡
    storyboard = request.storyboard or _default_storyboard(request.description, n)

    parts = [
        "Generate a SPRITE SHEET ANIMATION as ONE single image.",
        "",
        "=== LAYOUT (CRITICAL - MUST FOLLOW EXACTLY) ===",
        f"- Total image: EXACTLY {sheet_w}x{sheet_h} pixels",
        f"- Grid: {rows} ROWS x {cols} COLUMNS = {n} frame cells",
        f"- Each cell: EXACTLY {fw}x{fh} pixels",
        "- Reading order: LEFT-TO-RIGHT, then TOP-TO-BOTTOM (like text on a page)",
        f"- Cell (row 0, col 0) = top-left = frame 1",
        f"- Cell (row 0, col {cols - 1}) = top-right = frame {cols}",
        f"- Cell (row {rows - 1}, col {cols - 1}) = bottom-right = frame {n} (LAST)",
        "- NO borders, NO grid lines, NO numbers, NO labels between cells",
        "- Background: PURE BLACK (#000000) in EVERY cell, no exceptions",
        "",
        "=== ANIMATION SUBJECT ===",
        f"Effect: {request.description}",
        "",
        "=== HOW THIS ANIMATION WORKS ===",
        "Think of this image as a FLIPBOOK ANIMATION:",
        f"- {n} frames played at {request.fps} fps = {n / request.fps:.2f} second loop",
        f"- Each consecutive cell shows the scene {1000 / request.fps:.0f}ms later than the previous",
        "- Same objects must appear in MULTIPLE consecutive cells, slightly moved/changed",
        "- A particle visible in frame 5 should still be visible (in a new position) in frames 6, 7, 8",
        "- Motion should be VISUALLY TRACKABLE across cells",
        "",
        "=== FRAME-BY-FRAME STORYBOARD ===",
    ]

    for i, desc in enumerate(storyboard):
        r, c = divmod(i, cols)
        parts.append(f"Frame {i + 1} (row {r}, col {c}): {desc}")

    parts.extend([
        "",
        "=== ANTI-PATTERNS (DO NOT DO THESE) ===",
        "❌ DO NOT draw the same scene 16 times (no temporal change)",
        "❌ DO NOT draw 16 unrelated scenes (no continuity)",
        "❌ DO NOT just vary brightness/size of one static composition",
        "❌ DO NOT add visible borders or numbers between cells",
        "❌ DO NOT use any background color other than pure black",
        "❌ DO NOT make all cells equally 'busy' — animation should have buildup, peak, fade",
        "",
        "=== STYLE ===",
        "- Pixel art / 8-bit retro game VFX style",
        "- HIGH color saturation (vivid colors pop on black)",
        "- Bright additive-glow look (will be composited with ADD blend mode)",
        "- Sharp edges, no excessive anti-aliasing",
        "- Effect centered within each cell (don't bleed across cell boundaries)",
        "",
        "=== QUALITY CHECK BEFORE OUTPUT ===",
        "- Can a human watching cells 1→16 in order see clear MOTION?",
        "- Are individual particles trackable across at least 3 consecutive cells?",
        "- Does the animation have a clear START (sparse), MIDDLE (peak), END (dissipating)?",
        "If any answer is NO, redo the layout.",
    ])

    return "\n".join(parts)


def _default_storyboard(description: str, n_frames: int) -> list[str]:
    """
    生成默认逐帧故事板（v4 格式：每帧 STAGE N/total + 明确的密度/位置描述）。

    适合运动型 VFX。9 帧是甜点。
    """
    storyboard = []
    for i in range(n_frames):
        progress = i / max(1, n_frames - 1)

        if progress < 0.22:
            # 起始：空场 → 第一个元素出现
            density = "EMPTY" if i == 0 else "VERY SPARSE (1-2 elements entering)"
            storyboard.append(
                f"STAGE {i + 1}/{n_frames} ({density}): "
                f"{'Pure black, nothing visible yet. Only a tiny hint at the edge.' if i == 0 else 'First 1-2 elements just entering from the edge, rest of the frame is 90% empty black.'} "
                f"Animation: {description}"
            )
        elif progress < 0.44:
            storyboard.append(
                f"STAGE {i + 1}/{n_frames} (BUILDING): "
                f"Several elements ({int(3 + progress * 8)}) streaking/moving across the upper portion. "
                f"Lower portion still mostly empty. Building energy. "
                f"Animation: {description}"
            )
        elif progress < 0.67:
            storyboard.append(
                f"STAGE {i + 1}/{n_frames} (PEAK): "
                f"MAXIMUM density — 10+ elements filling the entire frame. "
                f"Impacts/explosions at their brightest. Most intense, busiest frame. "
                f"Animation: {description}"
            )
        elif progress < 0.78:
            storyboard.append(
                f"STAGE {i + 1}/{n_frames} (THINNING): "
                f"Density dropping — 5-6 elements remain in air, fewer new ones entering. "
                f"Impact debris accumulating. Sparks dimming. "
                f"Animation: {description}"
            )
        else:
            remaining_pct = int((1.0 - progress) / (1.0 - 0.78) * 100)
            storyboard.append(
                f"STAGE {i + 1}/{n_frames} (AFTERMATH {'- FINAL' if i == n_frames - 1 else ''}): "
                f"{'Almost empty — just 1-2 lingering particles and ground debris. Black sky returns.' if remaining_pct < 30 else 'No main elements in air. Only lingering debris, fading sparks, drifting dust.'} "
                f"Animation: {description}"
            )
    return storyboard


def clean_grid_borders(raw_path: Path, rows: int, cols: int, border_width: int = 4) -> None:
    """
    清除 Gemini 在 grid 边界处偷加的白色分隔线。

    在 grid 边界位置 ±border_width 像素范围内，将所有像素设为黑色透明。
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return

    img = Image.open(raw_path).convert("RGBA")
    arr = np.array(img)
    h, w = arr.shape[:2]
    cell_h, cell_w = h // rows, w // cols

    cleaned = False
    # 清除水平边界线
    for r in range(1, rows):
        y = r * cell_h
        y0 = max(0, y - border_width)
        y1 = min(h, y + border_width + 1)
        strip_brightness = arr[y0:y1, :, :3].astype(float).mean(axis=2)
        if strip_brightness.mean() > 40:
            arr[y0:y1, :, :] = 0
            cleaned = True

    # 清除垂直边界线
    for c in range(1, cols):
        x = c * cell_w
        x0 = max(0, x - border_width)
        x1 = min(w, x + border_width + 1)
        strip_brightness = arr[:, x0:x1, :3].astype(float).mean(axis=2)
        if strip_brightness.mean() > 40:
            arr[:, x0:x1, :] = 0
            cleaned = True

    if cleaned:
        Image.fromarray(arr, "RGBA").save(raw_path, "PNG")
        print(f"  [清理] 已移除 grid 边框线")


def apply_lumakey(raw_path: Path, threshold_low: int = 24, fade_range: int = 64) -> None:
    """
    Lumakey：把黑色背景变成透明。

    原理：像素亮度 → alpha 通道
    - 亮度 < threshold_low → 完全透明（背景）
    - 亮度 > threshold_low + fade_range → 完全不透明（前景）
    - 中间 → 半透明渐变（边缘柔化）

    参数已在铅笔暴雨/冰风暴实验中验证（2026-06-07）。
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return

    img = Image.open(raw_path).convert("RGBA")
    arr = np.array(img)

    rgb = arr[:, :, :3].astype(np.float32)
    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    alpha = np.clip((lum - threshold_low) / fade_range, 0, 1) * 255
    arr[:, :, 3] = alpha.astype(np.uint8)

    Image.fromarray(arr, "RGBA").save(raw_path, "PNG")

    total = alpha.size
    opaque = (alpha == 255).sum() / total
    transparent = (alpha == 0).sum() / total
    print(f"  [lumakey] 不透明 {opaque:.1%} / 透明 {transparent:.1%} / 渐变 {1 - opaque - transparent:.1%}")


def call_gemini_api(prompt: str, config: dict, aspect_ratio: str = "16:9", max_retries: int = 4) -> bytes | None:
    """调用 Gemini API。"""
    endpoint = (
        f"https://{config['api_host']}/v1beta/models/"
        f"{config['model']}:generateContent?key={config['api_key']}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "imageSize": "2K",  # 2K 以获得更高质量
                "aspectRatio": aspect_ratio,
            },
        },
    }

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  API 请求 (尝试 {attempt}/{max_retries})...")
            resp = requests.post(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=300,
            )

            if resp.status_code != 200:
                print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
                if attempt < max_retries:
                    time.sleep(2 * attempt)
                    continue
                return None

            data = resp.json()
            parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts") or []

            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline:
                    return base64.b64decode(inline.get("data", ""))

            print(f"  无图像数据返回")
            return None

        except Exception as e:
            print(f"  请求异常: {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
            else:
                return None

    return None


def _get_aspect(width: int, height: int) -> str:
    """计算最接近的 aspect ratio。"""
    ratio = width / height
    options = {
        "1:1": 1.0,
        "4:3": 4 / 3,
        "3:4": 3 / 4,
        "16:9": 16 / 9,
        "9:16": 9 / 16,
        "3:2": 3 / 2,
        "7:2": 7 / 2,  # 用于 8 帧 64x64 = 512x64 (8:1 ≈ 7:2)
    }
    closest = min(options.items(), key=lambda kv: abs(kv[1] - ratio))
    return closest[0]


def process_sprite_sheet(
    raw_path: Path,
    output_path: Path,
    target_size: tuple[int, int],
    frame_count: int,
    frame_size: tuple[int, int],
) -> None:
    """
    后处理 sprite sheet：
    1. 调整到目标尺寸
    2. 用色键移除黑色背景
    3. 边缘羽化
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        # 没有 PIL/numpy，直接复制
        import shutil
        shutil.copy(raw_path, output_path)
        return

    # 1. 加载原始图像
    img = Image.open(raw_path)
    print(f"  原始尺寸: {img.size}")

    # 2. 调整到目标尺寸
    if img.size != target_size:
        img = img.resize(target_size, Image.LANCZOS)
        print(f"  调整为: {target_size}")

    # 3. 转为 RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 4. 色键移除：把接近黑色的像素设为透明
    data = np.array(img)
    h, w = data.shape[:2]

    # 计算每个像素到黑色的距离
    rgb = data[:, :, :3].astype(np.int16)

    # 距离 = R + G + B（简单的亮度）
    brightness = rgb.sum(axis=2)

    # 设置透明度阈值
    # brightness < 30: 完全透明（背景）
    # brightness > 80: 完全不透明（前景）
    # 中间渐变：用于边缘羽化
    threshold_low = 30
    threshold_high = 80

    alpha = np.zeros_like(brightness, dtype=np.uint8)

    # 完全不透明
    full_opaque = brightness > threshold_high
    alpha[full_opaque] = 255

    # 中间渐变（边缘羽化）
    mid = (brightness >= threshold_low) & (brightness <= threshold_high)
    if mid.any():
        # 线性插值
        alpha[mid] = ((brightness[mid] - threshold_low) * 255 // (threshold_high - threshold_low)).astype(np.uint8)

    # 应用 alpha
    data[:, :, 3] = alpha

    # 5. 保存
    result = Image.fromarray(data, mode="RGBA")
    result.save(output_path, "PNG")
    print(f"  抠图后保存: {output_path}")


# ===== 命令行入口 =====
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="VFX Sprite Sheet 生成器 v3（3×3 grid + 关键帧 + crossfade 预览）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    # 预览故事板（不调 API，仅确认帧描述）
    python -m generator.vfx.vfx_sheet_generator "冰锥从天而降" --dry-run

    # 确认后生成
    python -m generator.vfx.vfx_sheet_generator "冰锥从天而降" --asset-id ice_rain

    # 自定义 grid
    python -m generator.vfx.vfx_sheet_generator "爆炸冲击波" --grid 2x2 --asset-id explosion
""",
    )
    parser.add_argument("description", help="特效描述（中文）")
    parser.add_argument("--grid", default="3x3",
                        help="grid 布局 ROWSxCOLS（默认 3x3 = 9 关键帧）")
    parser.add_argument("--fps", type=int, default=12, help="播放帧率（默认 12）")
    parser.add_argument("--loop", action="store_true", help="循环动画")
    parser.add_argument("--seed", type=int, help="随机种子")
    parser.add_argument("--asset-id", default=None, help="资产 ID（默认从描述生成）")
    parser.add_argument("--output", "-o", default=None, help="输出目录（默认 output/<asset_id>）")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示故事板预览，不调用 Gemini API")

    args = parser.parse_args()

    # 解析 grid
    try:
        rows, cols = (int(x) for x in args.grid.lower().split("x"))
    except ValueError:
        print(f"[错误] 无效 grid: {args.grid}")
        sys.exit(1)

    n_frames = rows * cols
    # 2048 / cols 或 2048 / rows 取整
    cell_size = 2048 // max(rows, cols)

    # 自动生成 asset_id
    asset_id = args.asset_id
    if not asset_id:
        import re
        clean = re.sub(r'[^一-龥a-zA-Z0-9]', '_', args.description)[:30]
        asset_id = clean.strip("_").lower() or "vfx"

    output_dir = Path(args.output) if args.output else Path(f"output/{asset_id}")

    request = VFXSheetRequest(
        description=args.description,
        frame_size=(cell_size, cell_size),
        frame_count=n_frames,
        grid_rows=rows,
        grid_cols=cols,
        fps=args.fps,
        loop=args.loop,
        seed=args.seed,
        asset_id=asset_id,
    )

    # 生成故事板
    storyboard = _default_storyboard(request.description, n_frames)

    print("=" * 60)
    print(f"VFX Sprite Sheet 生成器 v3 ({rows}×{cols} = {n_frames} 关键帧)")
    print("=" * 60)
    print(f"描述: {args.description}")
    print(f"Grid: {rows}×{cols} = {n_frames} 帧")
    print(f"单帧: {cell_size}×{cell_size}")
    print(f"Asset ID: {asset_id}")
    print(f"输出: {output_dir}")
    print()
    print("─── 故事板预览 ───")
    for i, desc in enumerate(storyboard):
        r, c = divmod(i, cols)
        print(f"  [{i + 1:2d}] (row {r}, col {c}): {desc[:80]}...")
    print("─── / 故事板预览 ───")
    print()

    if args.dry_run:
        print("[DRY RUN] 仅预览故事板，未调用 API。")
        print("去掉 --dry-run 后再执行即可开始生成。")
        sys.exit(0)

    # 正式生成
    request.storyboard = storyboard
    result = generate_vfx_sprite_sheet(request, output_dir)

    if result["success"]:
        raw_path = Path(result["raw_path"])
        # 自动生成 keyframes 预览
        print()
        print("─── 生成 keyframes 预览 ───")
        import subprocess
        preview_script = Path(__file__).parent.parent.parent / "keyframes_preview.py"
        if preview_script.exists():
            subprocess.run([
                sys.executable, str(preview_script),
                str(raw_path),
                "--grid", f"{rows}x{cols}",
            ])
        # 同时生成 grid 硬切预览
        grid_script = Path(__file__).parent.parent.parent / "grid_preview.py"
        if grid_script.exists():
            subprocess.run([
                sys.executable, str(grid_script),
                str(raw_path),
                "--grid", f"{rows}x{cols}",
                "--fps", str(args.fps),
            ])

        print()
        print("=" * 60)
        print("[完成]")
        print("=" * 60)
        print(f"原始 raw:     {result['raw_path']}")
        print(f"metadata:     {result['metadata_path']}")
        print()
        print("预览文件：")
        keyframes_html = raw_path.with_suffix(".keyframes.html")
        grid_html = raw_path.with_suffix(".grid.html")
        if keyframes_html.exists():
            print(f"  补帧预览:  {keyframes_html}")
        if grid_html.exists():
            print(f"  硬切预览:  {grid_html}")
    else:
        print(f"[失败] {result.get('error')}")
        sys.exit(1)
