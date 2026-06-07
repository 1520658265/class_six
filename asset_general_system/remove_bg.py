"""
智能抠图工具 - 使用 rembg (U2-Net) 对 sprite sheet 的每帧做背景移除

用法：
    # 对单个 sprite sheet 抠图
    python remove_bg.py output/ice_storm/vfx/white_ice_0022.png

    # 对目录下所有 sprite sheet 批量抠图
    python remove_bg.py output/real_test/objects/ --batch

    # 抠完自动生成 GIF 预览
    python remove_bg.py output/ice_storm/vfx/white_ice_0022.png --preview
"""

import argparse
import json
import sys
from pathlib import Path


def load_metadata(image_path: Path) -> dict | None:
    json_path = image_path.with_suffix(".json")
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    return None


def remove_bg_single_image(image_path: Path, output_path: Path, model_name: str = "u2netp") -> bool:
    """对单张图做背景移除。"""
    try:
        from rembg import remove, new_session
        from PIL import Image
    except ImportError:
        print("[错误] 请先安装 rembg: pip install rembg")
        return False

    session = new_session(model_name)
    img = Image.open(image_path).convert("RGBA")
    result = remove(img, session=session)
    result.save(output_path, "PNG")
    return True


def process_sprite_sheet(image_path: Path, output_path: Path, metadata: dict, model_name: str = "u2netp") -> bool:
    """
    对 sprite sheet 逐帧做背景移除，然后重新拼回一张。

    原理：
    1. 按 frame_size 切分 sprite sheet 成多帧
    2. 对每帧单独 rembg 抠图
    3. 把抠好的帧重新拼回 sprite sheet
    """
    try:
        from rembg import remove, new_session
        from PIL import Image
    except ImportError:
        print("[错误] 请先安装 rembg: pip install rembg")
        return False

    # 创建一次 session 复用，避免重复加载模型
    session = new_session(model_name)
    img = Image.open(image_path).convert("RGBA")
    fw, fh = metadata["frame_size"]

    # 判断布局：VFX 是单行，角色是多行
    if "frames" in metadata:
        # VFX：单行 N 帧
        n_frames = metadata["frames"]
        cols = n_frames
        rows = 1
    elif "animations" in metadata:
        # 角色：多行
        rows = img.height // fh
        cols = img.width // fw
    else:
        print(f"  [跳过] 未知格式: {image_path.name}")
        return False

    total = rows * cols
    print(f"  切分 {rows} 行 x {cols} 列 = {total} 帧，逐帧抠图...")

    # 创建输出 sheet
    out_sheet = Image.new("RGBA", img.size, (0, 0, 0, 0))

    for row in range(rows):
        for col in range(cols):
            x0, y0 = col * fw, row * fh
            frame = img.crop((x0, y0, x0 + fw, y0 + fh))

            # 跳过全透明帧（角色 sheet 可能有空白区域）
            if frame.getbbox() is None:
                continue

            # rembg 抠图（用复用的 session）
            frame_no_bg = remove(frame, session=session)
            out_sheet.paste(frame_no_bg, (x0, y0))

            frame_idx = row * cols + col + 1
            print(f"  [{frame_idx}/{total}] 帧 ({col},{row}) 完成", end="\r")

    print()
    out_sheet.save(output_path, "PNG")
    return True


def generate_gif_preview(image_path: Path, metadata: dict, scale: int = 4):
    """生成 GIF 预览（透明背景用深色底显示）。"""
    try:
        from PIL import Image
    except ImportError:
        return

    img = Image.open(image_path).convert("RGBA")
    fw, fh = metadata["frame_size"]

    if "frames" in metadata:
        n_frames = metadata["frames"]
        fps = metadata["fps"]
        loop = metadata.get("loop", False)
    else:
        return  # 角色 GIF 另外处理

    frames_out = []
    for i in range(n_frames):
        frame = img.crop((i * fw, 0, (i + 1) * fw, fh))
        if scale > 1:
            frame = frame.resize((fw * scale, fh * scale), Image.NEAREST)

        # 深灰背景（展示透明通道效果）
        bg = Image.new("RGBA", frame.size, (30, 30, 40, 255))
        bg.paste(frame, (0, 0), frame)
        frames_out.append(bg.convert("RGB"))

    gif_path = image_path.with_name(image_path.stem + "_nobg.gif")
    duration_ms = int(1000 / fps)
    frames_out[0].save(
        gif_path,
        save_all=True,
        append_images=frames_out[1:],
        duration=duration_ms,
        loop=0 if loop else 1,
        disposal=2,
    )
    print(f"  GIF 预览: {gif_path}")
    return gif_path


def process_one(image_path: Path, scale: int, preview: bool):
    """处理单个 sprite sheet。"""
    metadata = load_metadata(image_path)
    if not metadata:
        # 对于没有 metadata 的单张图，直接抠图
        print(f"\n处理 (单图): {image_path.name}")
        output_path = image_path.with_stem(image_path.stem + "_nobg")
        if remove_bg_single_image(image_path, output_path):
            print(f"  [OK] {output_path.name}")
        return

    print(f"\n处理: {image_path.name}")
    output_path = image_path.with_stem(image_path.stem + "_nobg")

    ok = process_sprite_sheet(image_path, output_path, metadata)
    if not ok:
        return

    file_size = output_path.stat().st_size
    print(f"  [OK] {output_path.name} ({file_size // 1024} KB)")

    if preview:
        gif_path = generate_gif_preview(output_path, metadata, scale=scale)
        if gif_path:
            print(f"  预览: {gif_path}")


def main():
    parser = argparse.ArgumentParser(description="智能抠图工具（rembg）")
    parser.add_argument("path", help="sprite sheet PNG 或目录")
    parser.add_argument("--batch", "-b", action="store_true", help="批量处理目录")
    parser.add_argument("--preview", "-p", action="store_true", help="抠图后生成 GIF 预览")
    parser.add_argument("--scale", "-s", type=int, default=4, help="GIF 放大倍数")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"[错误] 路径不存在: {path}")
        sys.exit(1)

    print("=" * 60)
    print("智能抠图工具 (rembg)")
    print("=" * 60)

    if path.is_dir() or args.batch:
        directory = path if path.is_dir() else path.parent
        # 只处理原始文件，跳过已抠图的
        pngs = [p for p in sorted(directory.glob("*.png"))
                if "_nobg" not in p.stem and "_raw" not in p.stem]
        print(f"目录: {directory}")
        print(f"找到 {len(pngs)} 个文件")
        for p in pngs:
            process_one(p, args.scale, args.preview)
    else:
        process_one(path, args.scale, args.preview)

    print("\n" + "=" * 60)
    print("完成！抠图后的文件以 _nobg.png 结尾。")
    print("=" * 60)


if __name__ == "__main__":
    main()
