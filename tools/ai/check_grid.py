"""
Overlay an N x M grid on a sprite sheet to verify that no element bleeds across cell boundaries.

Usage:
    python check_grid.py <sheet.png> <rows> <cols> [-o OUTPUT]

Output: <sheet>_grid.png with green grid lines drawn over the original.
Use it as the final acceptance step before delivering any sprite sheet.
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("sheet")
    p.add_argument("rows", type=int)
    p.add_argument("cols", type=int)
    p.add_argument("-o", "--out", help="Output path. Default: <sheet>_grid.png")
    args = p.parse_args()

    img = Image.open(args.sheet).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    line_color = (0, 255, 0)
    line_width = max(2, min(w, h) // 400)

    for r in range(1, args.rows):
        y = h * r // args.rows
        draw.line([(0, y), (w, y)], fill=line_color, width=line_width)
    for c in range(1, args.cols):
        x = w * c // args.cols
        draw.line([(x, 0), (x, h)], fill=line_color, width=line_width)

    if args.out:
        out = args.out
    else:
        stem, ext = os.path.splitext(args.sheet)
        out = f"{stem}_grid{ext}"

    img.save(out)
    print(f"[OK] -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
