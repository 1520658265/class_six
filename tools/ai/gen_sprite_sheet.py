"""
Generate one 2x2 sprite sheet (1024x1024, 4 frames of 512x512) per animation
in a single Gemini call, then slice into 4 PNGs with magenta cutout.

Why: separate calls produce frames with inconsistent character size, position,
and camera angle. Generating all 4 frames on a single canvas forces the model
to keep them aligned.

Usage:
    python gen_sprite_sheet.py --anim walk-down
    python gen_sprite_sheet.py --anim all  --concurrency 3
"""

import argparse
import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
REF_IMAGE = HERE / "out" / "hero01" / "_test-portrait-v5-magenta.jpg"
OUT_DIR = HERE / "out" / "hero01" / "sprites_v2"
PROMPT_DIR = OUT_DIR / "prompts"
SHEET_DIR = OUT_DIR / "sheets"
SHEET_SIZE = 1024
FRAME_SIZE = 512

WALK_BASE = """You are given a reference image of a character — an 11-12 year old Chinese sixth-grade boy in 2008, drawn in HD-2D pixel art style with shamate side-bangs hairstyle and blue school sportswear.

Your task: produce a SINGLE 1024x1024 image containing a 2x2 GRID of 4 walking-animation frames of EXACTLY THE SAME character.

Grid layout (read left-to-right, top-to-bottom):
- Top-left  (frame 1): {STEP1}
- Top-right (frame 2): {STEP2}
- Bot-left  (frame 3): {STEP3}
- Bot-right (frame 4): {STEP4}

CRITICAL — across all 4 frames keep IDENTICAL:
- Character size and proportions (each frame must show the character at the SAME scale)
- Vertical position (feet at the same y-line; do not let the character float)
- Camera angle and distance (top-down 45-degree RPG view, identical zoom)
- Face, hair, outfit, art style (HD-2D pixel art, crisp pixel edges)
- {DIRECTION_LOCK}

The ONLY thing that changes between frames is the leg/arm pose described above.

Layout rules:
- Each frame is exactly 512x512 pixels, arranged in a 2x2 grid
- Thin black 2-pixel borders separating the 4 frames are OK (will be cropped)
- Solid flat magenta background (#FF00FF) inside every frame
- Single character per frame, centered horizontally, full body visible

Final output: ONE image, 1024x1024, four walking frames in 2x2 grid, magenta backgrounds.
"""

BATTLE_BASE = """You are given a reference image of a character — an 11-12 year old Chinese sixth-grade boy in 2008, drawn in HD-2D pixel art style with shamate side-bangs hairstyle and blue school sportswear.

Your task: produce a SINGLE 1024x1024 image containing a 2x2 GRID of 4 battle-animation frames of EXACTLY THE SAME character.

Grid layout (read left-to-right, top-to-bottom):
- Top-left  (frame 1): {STEP1}
- Top-right (frame 2): {STEP2}
- Bot-left  (frame 3): {STEP3}
- Bot-right (frame 4): {STEP4}

CRITICAL — across all 4 frames keep IDENTICAL:
- Character size and proportions (each frame must show the character at the SAME scale)
- Vertical position (feet at the same y-line; do not let the character float)
- Camera angle and distance (side view, character facing right, identical zoom)
- Face, hair, outfit, art style (HD-2D pixel art, crisp pixel edges)

The ONLY thing that changes between frames is the action pose described above.

Layout rules:
- Each frame is exactly 512x512 pixels, arranged in a 2x2 grid
- Thin black 2-pixel borders separating the 4 frames are OK (will be cropped)
- Solid flat magenta background (#FF00FF) inside every frame
- Single character per frame, centered horizontally, full body visible

Final output: ONE image, 1024x1024, four battle frames in 2x2 grid, magenta backgrounds.
"""

DIRECTION_LOCK = {
    "down": "All 4 frames show the character FACING DOWNWARD (toward viewer); camera looks at the FRONT of the character",
    "up":   "All 4 frames show the character FACING UPWARD (away from viewer); camera looks at the BACK of the character",
    "left": "All 4 frames show the character FACING LEFT (side profile, body in profile to the left)",
    "right":"All 4 frames show the character FACING RIGHT (side profile, body in profile to the right)",
}

WALK_STEPS = {
    1: "neutral standing — both feet on the ground, arms relaxed at sides (rest pose)",
    2: "LEFT FOOT stepping forward in mid-stride, right leg supporting, arms swinging naturally",
    3: "neutral standing — both feet on the ground, arms relaxed at sides (same rest pose as frame 1)",
    4: "RIGHT FOOT stepping forward in mid-stride, left leg supporting, arms swinging naturally",
}

BATTLE_STEPS = {
    "idle": {
        1: "battle-ready idle stance, both feet planted, slight crouch, arms relaxed but ready",
        2: "battle idle slight inhale, chest raised, arms slightly tensed",
        3: "battle idle, neutral stance (same as frame 1)",
        4: "battle idle slight exhale, shoulders relaxed",
    },
    "attack": {
        1: "wind-up: stepping back with right foot, arms drawn back, preparing to swing",
        2: "swing forward: right arm thrown forward in punching motion, body twisted",
        3: "follow-through: arm fully extended forward, body weight on front foot",
        4: "recovery: arm pulled back, returning to ready stance",
    },
    "hurt": {
        1: "impact moment: head jerked back, body recoiling, eyes shut, mouth open in pain",
        2: "knocked back: body leaning back, arms thrown up defensively",
        3: "stagger: body bent over slightly, regaining balance",
        4: "recovery: standing back up, slight wince",
    },
}

ANIM_GROUPS = [
    ("walk-down", "walk", "down"),
    ("walk-up", "walk", "up"),
    ("walk-left", "walk", "left"),
    ("walk-right", "walk", "right"),
    ("battle-idle", "battle", "idle"),
    ("battle-attack", "battle", "attack"),
    ("battle-hurt", "battle", "hurt"),
]


def build_prompt(anim_name, kind, sub):
    if kind == "walk":
        text = WALK_BASE
        text = text.replace("{DIRECTION_LOCK}", DIRECTION_LOCK[sub])
        for i in (1, 2, 3, 4):
            text = text.replace(f"{{STEP{i}}}", WALK_STEPS[i])
    else:
        text = BATTLE_BASE
        steps = BATTLE_STEPS[sub]
        for i in (1, 2, 3, 4):
            text = text.replace(f"{{STEP{i}}}", steps[i])
    return text


def run_step(cmd, label):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return False, f"[{label}] exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"[{label}] timeout"
    except Exception as e:
        return False, f"[{label}] {type(e).__name__}: {e}"


def slice_sheet(sheet_path: Path, anim_name: str):
    """Crop the 1024 sheet into 4 x 512 jpgs in OUT_DIR with names <anim>-{1..4}.jpg."""
    img = Image.open(sheet_path).convert("RGB")
    w, h = img.size
    if (w, h) != (SHEET_SIZE, SHEET_SIZE):
        img = img.resize((SHEET_SIZE, SHEET_SIZE), Image.LANCZOS)
    coords = [
        (0, 0, FRAME_SIZE, FRAME_SIZE),
        (FRAME_SIZE, 0, SHEET_SIZE, FRAME_SIZE),
        (0, FRAME_SIZE, FRAME_SIZE, SHEET_SIZE),
        (FRAME_SIZE, FRAME_SIZE, SHEET_SIZE, SHEET_SIZE),
    ]
    out_jpgs = []
    for i, box in enumerate(coords, 1):
        crop = img.crop(box)
        out_jpg = OUT_DIR / f"{anim_name}-{i}.jpg"
        crop.save(out_jpg, "JPEG", quality=92)
        out_jpgs.append(out_jpg)
    return out_jpgs


def process_anim(anim_name, kind, sub):
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prompt_text = build_prompt(anim_name, kind, sub)
    prompt_path = PROMPT_DIR / f"{anim_name}.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    sheet_jpg = SHEET_DIR / f"{anim_name}-sheet.jpg"
    final_pngs = [OUT_DIR / f"{anim_name}-{i}.png" for i in (1, 2, 3, 4)]
    if all(p.exists() for p in final_pngs):
        return anim_name, True, "skip (all 4 PNGs exist)"

    py = sys.executable
    if not sheet_jpg.exists():
        ok, msg = run_step(
            [py, str(HERE / "gen_with_gemini.py"), str(prompt_path),
             "--aspect", "1:1", "--size", "1K",
             "--ref", str(REF_IMAGE),
             "-o", str(sheet_jpg.with_suffix(""))],
            "gen",
        )
        if not ok:
            return anim_name, False, msg

    try:
        frame_jpgs = slice_sheet(sheet_jpg, anim_name)
    except Exception as e:
        return anim_name, False, f"[slice] {type(e).__name__}: {e}"

    for jpg in frame_jpgs:
        png = jpg.with_suffix(".png")
        ok, msg = run_step(
            [py, str(HERE / "jpg_to_png_alpha.py"), str(jpg),
             "-o", str(png),
             "--mode", "global", "--tolerance", "25", "--halo-passes", "4"],
            f"alpha-{jpg.stem}",
        )
        if not ok:
            return anim_name, False, msg

    return anim_name, True, f"4 frames -> {OUT_DIR}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--anim", default="all", help="anim group name or 'all'")
    p.add_argument("--concurrency", type=int, default=3)
    args = p.parse_args()

    if args.anim == "all":
        targets = ANIM_GROUPS
    else:
        targets = [t for t in ANIM_GROUPS if t[0] == args.anim]
        if not targets:
            print(f"[ERROR] unknown anim: {args.anim}; valid: {[t[0] for t in ANIM_GROUPS]}")
            return 2

    print(f"[INFO] {len(targets)} sprite sheets to generate, concurrency={args.concurrency}")
    print(f"[INFO] reference: {REF_IMAGE}")
    print(f"[INFO] output dir: {OUT_DIR}")
    print()

    fail = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(process_anim, name, kind, sub): name for name, kind, sub in targets}
        for fut in concurrent.futures.as_completed(futures):
            name = futures[fut]
            try:
                _, ok, msg = fut.result()
            except Exception as e:
                ok, msg = False, f"exception: {e}"
            tag = "OK" if ok else "FAIL"
            print(f"[{tag}] {name}: {msg}")
            if not ok:
                fail.append((name, msg))

    print()
    print(f"[DONE] {len(targets) - len(fail)}/{len(targets)} succeeded")
    if fail:
        print("[FAIL LIST]")
        for n, m in fail:
            print(f"  {n}: {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
