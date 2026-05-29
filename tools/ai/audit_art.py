"""Audit images under assets/art/ for structural sanity.

Checks:
- File can open without error.
- For images we expect to be transparent (i.e. NOT in walk/ slice dirs that we
  don't process), report alpha-pixel ratio.
- Filenames should not contain `_v<digit>` anymore (the dealiased outputs).
- Report dimensions, mode, file size.
- Group by character / category.
"""
import argparse
import os
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image

DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "assets" / "art"
V_TAG_RE = re.compile(r"_v\d+", re.IGNORECASE)


def collect_results(root: Path) -> list[dict]:
    results = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in (".png", ".jpg", ".jpeg"):
                continue
            full = Path(dirpath) / fn
            rel = full.relative_to(root).as_posix()
            try:
                sz = full.stat().st_size
                with Image.open(full) as img:
                    w, h = img.size
                    mode = img.mode
                    alpha_ratio = None
                    if mode == "RGBA":
                        a = img.getchannel("A")
                        import numpy as np

                        arr = np.array(a)
                        alpha_ratio = float((arr == 0).sum()) / arr.size
                results.append({
                    "rel": rel,
                    "ext": ext,
                    "size_kb": sz / 1024,
                    "w": w,
                    "h": h,
                    "mode": mode,
                    "transparent_ratio": alpha_ratio,
                    "has_v_tag": bool(V_TAG_RE.search(fn)),
                })
            except Exception as e:
                results.append({"rel": rel, "error": f"{type(e).__name__}: {e}"})

    results.sort(key=lambda r: r["rel"])
    return results


def print_report(results: list[dict]) -> None:
    errors = [r for r in results if "error" in r]
    v_tagged = [r for r in results if r.get("has_v_tag")]
    non_alpha_pngs = [r for r in results if r.get("ext") == ".png" and r.get("mode") != "RGBA"]

    print(f"=== Total: {len(results)} files ===")
    print(f"  errors: {len(errors)}")
    print(f"  still has _vN tag: {len(v_tagged)}")
    print(f"  PNG without RGBA mode: {len(non_alpha_pngs)}")

    if errors:
        print("\n--- ERRORS ---")
        for r in errors:
            print(f"  {r['rel']}: {r['error']}")

    if v_tagged:
        print("\n--- STILL HAS _vN ---")
        for r in v_tagged:
            print(f"  {r['rel']}")

    if non_alpha_pngs:
        print("\n--- PNG without RGBA ---")
        for r in non_alpha_pngs:
            print(f"  {r['rel']}  mode={r['mode']}  {r['w']}x{r['h']}")

    groups = defaultdict(list)
    for r in results:
        if "error" in r:
            continue
        parts = r["rel"].split("/")
        key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        groups[key].append(r)

    print("\n=== By group (count, ext breakdown) ===")
    for key in sorted(groups.keys()):
        rs = groups[key]
        jpg = sum(1 for r in rs if r["ext"] == ".jpg")
        png = sum(1 for r in rs if r["ext"] == ".png")
        print(f"  {key}: {len(rs)} files (jpg={jpg}, png={png})")

    print("\n=== RGBA transparency ratio outliers ===")
    rgba = [r for r in results if r.get("mode") == "RGBA" and r.get("transparent_ratio") is not None]
    ratio_zero = [r for r in rgba if r["transparent_ratio"] == 0]
    ratio_low = [r for r in rgba if 0 < r["transparent_ratio"] < 0.05]
    ratio_high = [r for r in rgba if r["transparent_ratio"] > 0.95]
    print(f"  zero alpha (0% transparent): {len(ratio_zero)}")
    for r in ratio_zero:
        print(f"    {r['rel']}  {r['w']}x{r['h']}")
    print(f"  low alpha (<5% transparent): {len(ratio_low)}")
    for r in ratio_low:
        print(f"    {r['rel']}  {r['w']}x{r['h']}  transparent={r['transparent_ratio']:.1%}")
    print(f"  very high alpha (>95% transparent): {len(ratio_high)}")
    for r in ratio_high:
        print(f"    {r['rel']}  {r['w']}x{r['h']}  transparent={r['transparent_ratio']:.1%}")

    print("\n=== Pair check: jpg sources -> png alpha output ===")
    by_dir = defaultdict(set)
    for r in results:
        if "error" in r:
            continue
        d = os.path.dirname(r["rel"])
        stem = os.path.splitext(os.path.basename(r["rel"]))[0]
        by_dir[d].add((stem, r["ext"]))
    missing = []
    for d, items in by_dir.items():
        stems_with_jpg = {s for s, e in items if e in (".jpg", ".jpeg")}
        stems_with_png = {s for s, e in items if e == ".png"}
        expected_png_stems = {V_TAG_RE.sub("", s) for s in stems_with_jpg}
        not_paired = expected_png_stems - stems_with_png
        for s in not_paired:
            missing.append(f"{d}/{s}.png")
    print(f"  unpaired (jpg has no matching alpha png): {len(missing)}")
    for m in missing:
        print(f"    {m}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root",
        nargs="?",
        default=str(DEFAULT_ROOT),
        help="Image root to audit. Default: assets/art",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"[ERROR] not a directory: {root}")
        return 1

    print(f"[INFO] audit root: {root}")
    print_report(collect_results(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
