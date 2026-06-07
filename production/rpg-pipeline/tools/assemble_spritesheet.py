"""
将单帧 PNG 拼接为 sprite sheet。
用法: python assemble_spritesheet.py <input_dir> <output.png> --cols 4 --rows 4

输入目录中的文件按文件名排序后按行优先填入网格。
"""
import sys
import argparse
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("需要安装 Pillow: pip install Pillow")
    sys.exit(1)


def assemble(input_dir: Path, output: Path, cols: int, rows: int):
    frames = sorted(input_dir.glob("*.png"))
    expected = cols * rows
    if len(frames) != expected:
        print(f"警告: 期望 {expected} 帧，实际找到 {len(frames)} 帧")

    if not frames:
        print("错误: 输入目录中没有 PNG 文件")
        sys.exit(1)

    sample = Image.open(frames[0])
    fw, fh = sample.size

    sheet = Image.new("RGBA", (fw * cols, fh * rows), (0, 0, 0, 0))

    for i, frame_path in enumerate(frames):
        if i >= expected:
            break
        img = Image.open(frame_path).convert("RGBA")
        if img.size != (fw, fh):
            print(f"警告: {frame_path.name} 尺寸 {img.size} 与首帧 {(fw, fh)} 不一致，已缩放")
            img = img.resize((fw, fh), Image.NEAREST)
        col = i % cols
        row = i // cols
        sheet.paste(img, (col * fw, row * fh))

    sheet.save(output)
    print(f"拼接完成: {output} ({cols}x{rows}, 单帧 {fw}x{fh})")


def main():
    parser = argparse.ArgumentParser(description="单帧 PNG 拼接为 sprite sheet")
    parser.add_argument("input_dir", help="包含单帧 PNG 的目录")
    parser.add_argument("output", help="输出 sprite sheet 路径")
    parser.add_argument("--cols", type=int, default=4, help="列数（默认 4）")
    parser.add_argument("--rows", type=int, default=4, help="行数（默认 4）")
    args = parser.parse_args()

    assemble(Path(args.input_dir), Path(args.output), args.cols, args.rows)


if __name__ == "__main__":
    main()
