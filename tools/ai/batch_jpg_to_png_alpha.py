"""Batch convert every image under assets/art/ to an alpha PNG.

For each .jpg/.png:
- Output stem strips `_v<digits>` (case-insensitive).
- Output goes next to the input as `.png`.
- If the output path already exists, skip (never overwrite).
- If output path == input path (no rename possible), skip.
- If the input PNG already has alpha (transparent pixels present), copy via
  re-save as RGBA without running chroma_key (avoids destroying finished art).
- Otherwise call chroma_key with the same defaults as the CLI.

Usage:
    python tools/ai/batch_jpg_to_png_alpha.py [root]
"""

import os
import re
import shutil
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from jpg_to_png_alpha import chroma_key  # noqa: E402

V_TAG_RE = re.compile(r"_v\d+", re.IGNORECASE)


def out_path_for(in_path: str) -> str:
    d = os.path.dirname(in_path)
    stem, _ = os.path.splitext(os.path.basename(in_path))
    new_stem = V_TAG_RE.sub("", stem)
    return os.path.join(d, new_stem + ".png")


def png_has_alpha(img: Image.Image) -> bool:
    if img.mode in ("RGBA", "LA"):
        # Cheap check: if any pixel has alpha < 255, treat as alpha-bearing.
        alpha = img.getchannel("A")
        return alpha.getextrema()[0] < 255
    if img.mode == "P" and "transparency" in img.info:
        return True
    return False


def same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def main(root: str) -> int:
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in (".jpg", ".jpeg", ".png"):
                files.append(os.path.join(dirpath, fn))
    files.sort()
    print(f"[INFO] {len(files)} images under {root}")

    converted = copied = skipped_exists = skipped_same = errors = 0
    for in_path in files:
        out_path = out_path_for(in_path)

        if same_path(out_path, in_path):
            print(f"[SKIP same] {in_path}")
            skipped_same += 1
            continue
        if os.path.exists(out_path):
            print(f"[SKIP exists] {out_path}")
            skipped_exists += 1
            continue

        try:
            img = Image.open(in_path)
            if png_has_alpha(img):
                img.convert("RGBA").save(out_path, "PNG")
                print(f"[COPY alpha] {in_path} -> {out_path}")
                copied += 1
            else:
                out, cand, core, halo, matte, grid = chroma_key(
                    img,
                    tol=15,
                    halo_passes=2,
                    halo_max_sat=110,
                )
                out.save(out_path, "PNG")
                print(f"[KEY] {in_path} -> {out_path}  cand={cand} core={core} halo={halo} matte={matte} grid={grid}")
                converted += 1
        except Exception as e:
            print(f"[ERR] {in_path}: {type(e).__name__}: {e}")
            errors += 1

    print(
        f"[DONE] keyed={converted} copied={copied} "
        f"skipped_exists={skipped_exists} skipped_same={skipped_same} errors={errors}"
    )
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) > 1:
        root = sys.argv[1]
    else:
        root = os.path.join(HERE, "..", "..", "assets", "art")
    sys.exit(main(os.path.abspath(root)))
