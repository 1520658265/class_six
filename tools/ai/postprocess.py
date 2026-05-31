"""AI sprite sheet 后处理：洋红 #FF00FF 抠 alpha + 网格切片。

按 5/25 spec 的设计：建筑/物件 sheet 用 #FF00FF 作为 gutter / 透明背景。
JPG 压缩会污染洋红到附近色，所以抠图按 RGB 距离做容差。

用法：
    python tools/ai/postprocess.py chroma <input> <output>
    python tools/ai/postprocess.py slice <input> <rows> <cols> <output_dir> [--name PREFIX]
    python tools/ai/postprocess.py chroma_slice <input> <rows> <cols> <output_dir> [--name PREFIX]

chroma 单独抠 magenta → 保存单张透明 PNG。
slice 把 input 按 rows×cols 切成 rows*cols 张独立 PNG。
chroma_slice = chroma 后再 slice，常用。
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from PIL import Image


def chroma_key_magenta(im: Image.Image, tolerance: float = 60.0) -> Image.Image:
	"""把接近 #FF00FF 的像素抠掉（变透明）。tolerance 是 RGB 距离阈值。"""
	im = im.convert("RGBA")
	pixels = im.load()
	w, h = im.size
	for y in range(h):
		for x in range(w):
			r, g, b, _ = pixels[x, y]
			# 距离 (255, 0, 255)
			dr = r - 255
			dg = g - 0
			db = b - 255
			dist = (dr * dr + dg * dg + db * db) ** 0.5
			if dist <= tolerance:
				pixels[x, y] = (0, 0, 0, 0)
	return im


def slice_grid(im: Image.Image, rows: int, cols: int) -> list[Image.Image]:
	w, h = im.size
	tw = w // cols
	th = h // rows
	tiles: list[Image.Image] = []
	for r in range(rows):
		for c in range(cols):
			box = (c * tw, r * th, c * tw + tw, r * th + th)
			tiles.append(im.crop(box))
	return tiles


def cmd_chroma(args: argparse.Namespace) -> None:
	im = Image.open(args.input)
	out = chroma_key_magenta(im, tolerance=args.tolerance)
	out.save(args.output)
	print(f"[OK] chroma → {args.output}")


def cmd_slice(args: argparse.Namespace, do_chroma: bool) -> None:
	im = Image.open(args.input)
	if do_chroma:
		im = chroma_key_magenta(im, tolerance=args.tolerance)
	else:
		im = im.convert("RGBA")
	tiles = slice_grid(im, args.rows, args.cols)
	out_dir = Path(args.output_dir)
	out_dir.mkdir(parents=True, exist_ok=True)
	prefix = args.name or Path(args.input).stem
	for i, t in enumerate(tiles):
		r = i // args.cols
		c = i % args.cols
		path = out_dir / f"{prefix}_r{r}_c{c}.png"
		t.save(path)
	print(f"[OK] sliced {args.rows}×{args.cols}={args.rows * args.cols} tiles → {out_dir}/")


def main() -> int:
	ap = argparse.ArgumentParser(description=__doc__)
	sub = ap.add_subparsers(dest="cmd", required=True)

	a1 = sub.add_parser("chroma")
	a1.add_argument("input")
	a1.add_argument("output")
	a1.add_argument("--tolerance", type=float, default=60.0)

	a2 = sub.add_parser("slice")
	a2.add_argument("input")
	a2.add_argument("rows", type=int)
	a2.add_argument("cols", type=int)
	a2.add_argument("output_dir")
	a2.add_argument("--name")
	a2.add_argument("--tolerance", type=float, default=60.0)

	a3 = sub.add_parser("chroma_slice")
	a3.add_argument("input")
	a3.add_argument("rows", type=int)
	a3.add_argument("cols", type=int)
	a3.add_argument("output_dir")
	a3.add_argument("--name")
	a3.add_argument("--tolerance", type=float, default=60.0)

	args = ap.parse_args()
	if args.cmd == "chroma":
		cmd_chroma(args)
	elif args.cmd == "slice":
		cmd_slice(args, do_chroma=False)
	elif args.cmd == "chroma_slice":
		cmd_slice(args, do_chroma=True)
	return 0


if __name__ == "__main__":
	sys.exit(main())
