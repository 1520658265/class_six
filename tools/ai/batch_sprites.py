"""
Batch-generate hero01 walking and battle sprites with Gemini.

Pipeline per frame:
1. Write prompt file with frame-specific instructions
2. Call Gemini API with reference image
3. Run magenta-keyed cutout to get transparent PNG
4. Resize to game-target size (NEAREST)

Runs frames in parallel (max 4 concurrent) to avoid rate limits.
"""

import argparse
import concurrent.futures
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REF_IMAGE = HERE / "out" / "hero01" / "_test-portrait-v5-magenta.jpg"
OUT_DIR = HERE / "out" / "hero01" / "sprites"
PROMPT_DIR = OUT_DIR / "prompts"
MAX_CONCURRENCY = 4

WALK_BASE = """You are given a reference image of a character — an 11-12 year old Chinese sixth-grade boy in 2008, drawn in HD-2D pixel art style with shamate side-bangs hairstyle and blue school sportswear.

Your task: redraw EXACTLY THE SAME character, in a different walking pose.

Keep IDENTICAL to the reference:
- Face shape, eye shape, all facial features
- Skin tone
- Hairstyle (long sweeping side-bangs, stiff styled black hair)
- Outfit (blue-and-white school tracksuit jacket, loose sport pants, canvas sneakers)
- Body proportions (chibi-ish, 3-head-tall)
- Art style (HD-2D pixel art, crisp pixel edges, limited palette, bold outlines, cel-shaded)

CHANGE the pose to:
- Top-down 45-degree RPG game view (like Octopath Traveler walking sprite)
- {DIRECTION}
- {STEP}
- Full body visible from head to toe
- Single character sprite, centered in frame

Background:
- SOLID FLAT MAGENTA BACKGROUND (exact hex #FF00FF, pure magenta, no gradient, no shadows)

Final output: a single walking-frame sprite of the same character as in the reference, on pure magenta background.
"""

BATTLE_BASE = """You are given a reference image of a character — an 11-12 year old Chinese sixth-grade boy in 2008, drawn in HD-2D pixel art style with shamate side-bangs hairstyle and blue school sportswear.

Your task: redraw EXACTLY THE SAME character, in a different battle pose.

Keep IDENTICAL to the reference:
- Face shape, eye shape, all facial features
- Skin tone
- Hairstyle (long sweeping side-bangs, stiff styled black hair)
- Outfit (blue-and-white school tracksuit jacket, loose sport pants, canvas sneakers)
- Body proportions (chibi-ish, 3-head-tall)
- Art style (HD-2D pixel art, crisp pixel edges, limited palette, bold outlines, cel-shaded)

CHANGE the pose to:
- Side view, character facing right (RPG turn-based battle perspective like Final Fantasy / Octopath)
- {ACTION}
- Full body visible from head to toe
- Single character sprite, centered in frame

Background:
- SOLID FLAT MAGENTA BACKGROUND (exact hex #FF00FF, pure magenta, no gradient, no shadows)

Final output: a single battle-frame sprite of the same character as in the reference, on pure magenta background.
"""

DIRECTIONS = {
    "down": "Walking motion, FACING DOWNWARD (toward the viewer), camera looking at the front of the character",
    "up": "Walking motion, FACING UPWARD (away from viewer), camera looking at the BACK of the character",
    "left": "Walking motion, FACING LEFT, side profile view, body in profile",
    "right": "Walking motion, FACING RIGHT, side profile view, body in profile",
}

STEPS = {
    1: "neutral standing frame, both feet on the ground, arms relaxed at sides — this is the resting frame between strides",
    2: "LEFT FOOT stepping forward in mid-stride, right leg supporting, arms swinging naturally",
    3: "neutral standing frame, both feet on the ground, arms relaxed at sides — same as the first resting frame",
    4: "RIGHT FOOT stepping forward in mid-stride, left leg supporting, arms swinging naturally",
}

BATTLE_ACTIONS = {
    ("idle", 1): "battle-ready idle stance, both feet planted, slight crouch, arms relaxed but ready",
    ("idle", 2): "battle idle slight inhale, chest raised, arms slightly tensed",
    ("idle", 3): "battle idle, neutral stance, same as frame 1",
    ("idle", 4): "battle idle slight exhale, shoulders relaxed",
    ("attack", 1): "wind-up: stepping back with right foot, arms drawn back, preparing to swing",
    ("attack", 2): "swing forward: right arm thrown forward in punching/striking motion, body twisted",
    ("attack", 3): "follow-through: arm fully extended forward, body weight on front foot",
    ("attack", 4): "recovery: arm pulled back, returning to ready stance",
    ("hurt", 1): "impact moment: head jerked back, body recoiling, eyes shut, mouth open in pain",
    ("hurt", 2): "knocked back: body leaning back, arms thrown up defensively",
    ("hurt", 3): "stagger: body bent over slightly, regaining balance",
    ("hurt", 4): "recovery: standing back up, slight wince",
}


def build_walk_prompts():
    out = []
    for direction in ("down", "up", "left", "right"):
        for step in (1, 2, 3, 4):
            if direction == "down" and step == 1:
                continue  # already generated as walk-down-1
            name = f"walk-{direction}-{step}"
            text = WALK_BASE.replace("{DIRECTION}", DIRECTIONS[direction]).replace("{STEP}", STEPS[step])
            out.append((name, text))
    return out


def build_battle_prompts():
    out = []
    for action in ("idle", "attack", "hurt"):
        for frame in (1, 2, 3, 4):
            name = f"battle-{action}-{frame}"
            text = BATTLE_BASE.replace("{ACTION}", BATTLE_ACTIONS[(action, frame)])
            out.append((name, text))
    return out


def run_step(cmd, label):
    """Run a subprocess; return (ok, log_tail)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return False, f"[{label}] exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"[{label}] timeout"
    except Exception as e:
        return False, f"[{label}] {type(e).__name__}: {e}"


def process_frame(name, prompt_text):
    """Generate one sprite (1024) and cut out magenta background. Returns (name, ok, msg)."""
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prompt_path = PROMPT_DIR / f"{name}.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    raw_jpg = OUT_DIR / f"{name}.jpg"
    alpha_png = OUT_DIR / f"{name}.png"

    if alpha_png.exists():
        return name, True, "skip (final exists)"

    py = sys.executable
    if not raw_jpg.exists():
        ok, msg = run_step(
            [py, str(HERE / "gen_with_gemini.py"), str(prompt_path),
             "--aspect", "1:1", "--size", "1K",
             "--ref", str(REF_IMAGE),
             "-o", str(raw_jpg.with_suffix(""))],
            "gen",
        )
        if not ok:
            return name, False, msg

    ok, msg = run_step(
        [py, str(HERE / "jpg_to_png_alpha.py"), str(raw_jpg),
         "-o", str(alpha_png),
         "--mode", "global", "--tolerance", "25", "--halo-passes", "4"],
        "alpha",
    )
    if not ok:
        return name, False, msg
    return name, True, str(alpha_png)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=("walk", "battle", "all"), default="all")
    p.add_argument("--concurrency", type=int, default=MAX_CONCURRENCY)
    args = p.parse_args()

    jobs = []
    if args.only in ("walk", "all"):
        jobs.extend(build_walk_prompts())
    if args.only in ("battle", "all"):
        jobs.extend(build_battle_prompts())

    print(f"[INFO] {len(jobs)} frames to process, concurrency={args.concurrency}")
    print(f"[INFO] reference: {REF_IMAGE}")
    print(f"[INFO] output dir: {OUT_DIR}")
    print()

    fail = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(process_frame, name, prompt): name
                   for name, prompt in jobs}
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
    print(f"[DONE] {len(jobs) - len(fail)}/{len(jobs)} succeeded")
    if fail:
        print("[FAIL LIST]")
        for n, m in fail:
            print(f"  {n}: {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
