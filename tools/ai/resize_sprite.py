"""
Resize a transparent PNG sprite to target size using NEAREST (preserves pixel art edges).

Usage:
    python resize_sprite.py <input.png> -o <output.png> --size 128
    python resize_sprite.py <input.png> -o <output.png> --size 256
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--size", type=int, required=True, help="Target square size (e.g. 128, 256)")
    args = p.parse_args()

    img = Image.open(args.input)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    resized = img.resize((args.size, args.size), Image.NEAREST)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    resized.save(args.out)
    print(f"[OK] {args.input} ({img.size[0]}x{img.size[1]}) -> {args.out} ({args.size}x{args.size})")


if __name__ == "__main__":
    sys.exit(main())
