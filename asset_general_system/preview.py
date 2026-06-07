#!/usr/bin/env python
"""
预览工具 - 把 sprite sheet 转成 GIF / HTML 动画播放器

使用：
    # 生成 GIF
    python preview.py output/ice_storm/vfx/white_ice_0022.png

    # 生成 GIF + HTML 播放器
    python preview.py output/ice_storm/vfx/white_ice_0022.png --html

    # 批量预览整个目录
    python preview.py output/ice_storm/vfx/ --batch

    # 调整放大倍数
    python preview.py output/ice_storm/vfx/white_ice_0022.png --scale 4

    # 自定义 fps（覆盖 metadata）
    python preview.py output/ice_storm/vfx/white_ice_0022.png --fps 6
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_metadata(image_path: Path) -> dict[str, Any] | None:
    """加载对应的 metadata JSON。"""
    json_path = image_path.with_suffix(".json")
    if not json_path.exists():
        return None
    return json.loads(json_path.read_text(encoding="utf-8"))


def split_frames(image, frame_size: tuple[int, int]) -> list:
    """把 sprite sheet 切成单帧列表。"""
    fw, fh = frame_size
    frames = []

    rows = image.height // fh
    cols = image.width // fw

    for row in range(rows):
        for col in range(cols):
            box = (col * fw, row * fh, (col + 1) * fw, (row + 1) * fh)
            frame = image.crop(box)
            frames.append(frame)

    return frames


def detect_layout(metadata: dict, image) -> tuple[list, int]:
    """根据 metadata 确定帧布局，返回 (frames, fps)。

    返回的 frames 是按播放顺序排列的 PIL Image 列表。
    """
    # VFX：单行
    if "frames" in metadata and "fps" in metadata:
        frame_size = tuple(metadata["frame_size"])
        all_frames = split_frames(image, frame_size)
        return all_frames[:metadata["frames"]], metadata["fps"]

    # 角色 sprite sheet：多行多动画
    if "animations" in metadata:
        return None, None  # 由调用者处理多个动画

    return None, None


def generate_gif_for_vfx(image_path: Path, scale: int = 4, fps_override: int = None):
    """为 VFX 单行 sprite sheet 生成 GIF。"""
    from PIL import Image

    image = Image.open(image_path)
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    metadata = load_metadata(image_path)
    if not metadata:
        print(f"[警告] 没有 metadata: {image_path.with_suffix('.json')}")
        return None

    if "frames" not in metadata:
        print(f"[跳过] 不是 VFX 类型: {image_path.name}")
        return None

    frame_size = tuple(metadata["frame_size"])
    fw, fh = frame_size
    num_frames = metadata["frames"]
    fps = fps_override or metadata["fps"]
    loop = metadata.get("loop", False)

    # 切分帧
    frames = []
    for i in range(num_frames):
        frame = image.crop((i * fw, 0, (i + 1) * fw, fh))
        if scale > 1:
            frame = frame.resize((fw * scale, fh * scale), Image.NEAREST)
        # GIF 不支持 alpha，用白色背景
        bg = Image.new("RGB", frame.size, (40, 40, 40))  # 深灰背景
        bg.paste(frame, (0, 0), frame)
        frames.append(bg)

    # 生成 GIF
    output_path = image_path.with_suffix(".gif")
    duration_ms = int(1000 / fps)

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=duration_ms,
        loop=0 if loop else 1,  # 0 = 无限循环, 1 = 播一次
        disposal=2,
    )

    print(f"  [OK] {output_path.name} ({num_frames} 帧 @ {fps}fps, scale={scale}x)")
    return output_path


def generate_gif_for_character(image_path: Path, scale: int = 2, fps_override: int = None):
    """为角色 sprite sheet 生成多个 GIF（每个动画一个）。"""
    from PIL import Image

    image = Image.open(image_path)
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    metadata = load_metadata(image_path)
    if not metadata or "animations" not in metadata:
        return []

    frame_size = tuple(metadata["frame_size"])
    fw, fh = frame_size

    output_paths = []
    base_name = image_path.stem

    for anim_name, anim_data in metadata["animations"].items():
        row = anim_data["row"]
        num_frames = anim_data["frames"]
        fps = fps_override or anim_data["fps"]
        loop = anim_data.get("loop", True)

        # 切分该行的帧
        frames = []
        for i in range(num_frames):
            box = (i * fw, row * fh, (i + 1) * fw, (row + 1) * fh)
            frame = image.crop(box)
            if scale > 1:
                frame = frame.resize((fw * scale, fh * scale), Image.NEAREST)
            bg = Image.new("RGB", frame.size, (40, 40, 40))
            bg.paste(frame, (0, 0), frame)
            frames.append(bg)

        # 输出 GIF
        gif_path = image_path.parent / f"{base_name}_{anim_name}.gif"
        duration_ms = int(1000 / fps)

        frames[0].save(
            gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0 if loop else 1,
            disposal=2,
        )

        output_paths.append(gif_path)
        print(f"  [OK] {gif_path.name} ({num_frames} 帧 @ {fps}fps)")

    return output_paths


def generate_html_player(image_path: Path, gif_paths: list, scale: int = 4):
    """为单个 sprite sheet 生成 HTML 播放器（可调速、放大、对比）。"""
    metadata = load_metadata(image_path)

    title = image_path.stem
    sprite_url = image_path.name

    # 构建动画列表
    if metadata and "animations" in metadata:
        # 角色：多动画
        animations_data = []
        for anim_name, anim_data in metadata["animations"].items():
            animations_data.append({
                "name": anim_name,
                "row": anim_data["row"],
                "frames": anim_data["frames"],
                "fps": anim_data["fps"],
                "loop": anim_data.get("loop", True),
            })
        frame_size = metadata["frame_size"]
    else:
        # VFX：单动画
        animations_data = [{
            "name": title,
            "row": 0,
            "frames": metadata.get("frames", 8) if metadata else 8,
            "fps": metadata.get("fps", 12) if metadata else 12,
            "loop": metadata.get("loop", False) if metadata else False,
        }]
        frame_size = metadata.get("frame_size", [64, 64]) if metadata else [64, 64]

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>动画预览 - {title}</title>
<style>
    body {{
        font-family: 'Segoe UI', sans-serif;
        background: #1a1a1a;
        color: #eee;
        padding: 20px;
        margin: 0;
    }}
    h1 {{ color: #4af; }}
    .container {{
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
    }}
    .anim-card {{
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 8px;
        padding: 15px;
        min-width: 280px;
    }}
    .anim-card h3 {{ margin: 0 0 10px 0; color: #6f9; }}
    canvas {{
        background: #333;
        border: 1px solid #555;
        image-rendering: pixelated;
        display: block;
        margin: 10px 0;
    }}
    .controls {{
        display: flex;
        gap: 10px;
        align-items: center;
        margin-top: 10px;
    }}
    button {{
        background: #4af;
        color: white;
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    }}
    button:hover {{ background: #6cf; }}
    .info {{ font-size: 12px; color: #aaa; margin-top: 8px; }}
    label {{ font-size: 13px; }}
    input[type=range] {{ width: 120px; }}
    .sprite-sheet {{
        margin-top: 30px;
        padding: 15px;
        background: #2a2a2a;
        border-radius: 8px;
    }}
    .sprite-sheet img {{
        max-width: 100%;
        image-rendering: pixelated;
        border: 1px solid #555;
    }}
</style>
</head>
<body>
    <h1>🎬 {title}</h1>
    <p style="color:#aaa">点击图像或按钮控制播放</p>

    <div class="container" id="container"></div>

    <div class="sprite-sheet">
        <h3>原始 Sprite Sheet</h3>
        <img src="{sprite_url}" alt="sprite sheet">
    </div>

<script>
const SPRITE_URL = {json.dumps(sprite_url)};
const FRAME_W = {frame_size[0]};
const FRAME_H = {frame_size[1]};
const SCALE = {scale};
const ANIMATIONS = {json.dumps(animations_data)};

const img = new Image();
img.src = SPRITE_URL;

img.onload = () => {{
    const container = document.getElementById('container');
    ANIMATIONS.forEach(anim => {{
        container.appendChild(createPlayer(anim));
    }});
}};

function createPlayer(anim) {{
    const card = document.createElement('div');
    card.className = 'anim-card';

    card.innerHTML = `
        <h3>${{anim.name}}</h3>
        <canvas width="${{FRAME_W * SCALE}}" height="${{FRAME_H * SCALE}}"></canvas>
        <div class="controls">
            <button class="play-btn">⏸ 暂停</button>
            <button class="reset-btn">⟲ 重置</button>
        </div>
        <div class="controls">
            <label>速度:</label>
            <input type="range" min="1" max="30" value="${{anim.fps}}" class="fps-slider">
            <span class="fps-label">${{anim.fps}}fps</span>
        </div>
        <div class="info">
            ${{anim.frames}} 帧 ·
            ${{anim.loop ? '循环' : '一次性'}} ·
            row ${{anim.row}}
        </div>
    `;

    const canvas = card.querySelector('canvas');
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = false;

    let frameIdx = 0;
    let playing = true;
    let lastTime = 0;
    let fps = anim.fps;

    function draw() {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#333';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        const sx = frameIdx * FRAME_W;
        const sy = anim.row * FRAME_H;
        ctx.drawImage(
            img,
            sx, sy, FRAME_W, FRAME_H,
            0, 0, canvas.width, canvas.height
        );
    }}

    function tick(now) {{
        if (playing) {{
            const elapsed = now - lastTime;
            if (elapsed > 1000 / fps) {{
                frameIdx++;
                if (frameIdx >= anim.frames) {{
                    if (anim.loop) {{
                        frameIdx = 0;
                    }} else {{
                        frameIdx = anim.frames - 1;
                    }}
                }}
                draw();
                lastTime = now;
            }}
        }}
        requestAnimationFrame(tick);
    }}

    draw();
    requestAnimationFrame(tick);

    // 事件绑定
    card.querySelector('.play-btn').onclick = (e) => {{
        playing = !playing;
        e.target.textContent = playing ? '⏸ 暂停' : '▶ 播放';
    }};
    card.querySelector('.reset-btn').onclick = () => {{
        frameIdx = 0;
        draw();
    }};
    const slider = card.querySelector('.fps-slider');
    const fpsLabel = card.querySelector('.fps-label');
    slider.oninput = () => {{
        fps = parseInt(slider.value);
        fpsLabel.textContent = fps + 'fps';
    }};
    canvas.onclick = () => {{
        playing = !playing;
        card.querySelector('.play-btn').textContent = playing ? '⏸ 暂停' : '▶ 播放';
    }};

    return card;
}}
</script>
</body>
</html>
"""

    html_path = image_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    print(f"  [OK] {html_path.name}")
    return html_path


def preview_one(image_path: Path, scale: int, fps_override: int, generate_html: bool):
    """预览单个 sprite sheet。"""
    if not image_path.exists():
        print(f"[错误] 文件不存在: {image_path}")
        return

    metadata = load_metadata(image_path)
    if not metadata:
        print(f"[跳过] 没有 metadata: {image_path.name}")
        return

    print(f"\n预览: {image_path.name}")

    # 生成 GIF
    gif_paths = []
    if "animations" in metadata:
        # 角色：多个动画
        gif_paths = generate_gif_for_character(image_path, scale=scale, fps_override=fps_override)
    elif "frames" in metadata:
        # VFX：单个 GIF
        gif_path = generate_gif_for_vfx(image_path, scale=scale, fps_override=fps_override)
        if gif_path:
            gif_paths = [gif_path]
    else:
        print(f"  [跳过] 不是动画素材")
        return

    # 生成 HTML 播放器
    if generate_html and gif_paths:
        generate_html_player(image_path, gif_paths, scale=scale)


def main():
    parser = argparse.ArgumentParser(
        description="Sprite sheet 动画预览工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
    # 生成 GIF
    python preview.py output/ice_storm/vfx/white_ice_0022.png

    # 生成 GIF + HTML 播放器
    python preview.py output/ice_storm/vfx/white_ice_0022.png --html

    # 批量预览整个目录
    python preview.py output/real_test/objects/ --batch

    # 4倍放大
    python preview.py output/.../*.png --scale 4
""",
    )
    parser.add_argument("path", help="sprite sheet PNG 文件或目录")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="批量模式：处理目录下所有 PNG")
    parser.add_argument("--scale", "-s", type=int, default=4,
                       help="放大倍数（默认 4，像素画推荐 4-8）")
    parser.add_argument("--fps", "-f", type=int,
                       help="覆盖 metadata 的 fps（用于慢放/快放预览）")
    parser.add_argument("--html", action="store_true",
                       help="同时生成 HTML 播放器")
    parser.add_argument("--no-gif", action="store_true",
                       help="只生成 HTML，不生成 GIF")

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"[错误] 路径不存在: {path}")
        sys.exit(1)

    print("="*60)
    print("Sprite Sheet 动画预览工具")
    print("="*60)

    if path.is_dir() or args.batch:
        # 批量模式
        directory = path if path.is_dir() else path.parent
        png_files = sorted(directory.glob("*.png"))
        # 过滤掉 GIF 不需要的文件
        png_files = [p for p in png_files if not p.stem.endswith("_preview")]

        print(f"目录: {directory}")
        print(f"找到 {len(png_files)} 个 PNG 文件")

        for png in png_files:
            preview_one(png, args.scale, args.fps, args.html)
    else:
        # 单个文件
        preview_one(path, args.scale, args.fps, args.html)

    print()
    print("="*60)
    print("完成！")
    print("="*60)
    print()
    print("查看 GIF：")
    print("  - Windows: 双击 GIF 文件，或拖到浏览器")
    print("  - Mac: 用预览或浏览器打开")
    if args.html:
        print()
        print("查看 HTML 播放器（推荐）：")
        print("  - 双击 .html 文件用浏览器打开")
        print("  - 可以调速度、暂停、重置")


if __name__ == "__main__":
    main()
