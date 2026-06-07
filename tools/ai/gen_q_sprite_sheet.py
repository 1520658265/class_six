"""
Generate Q-version sprite sheets (1024x1024, 2x2 grid of 4 frames) for walking and battle animations.

Uses the Q-version portrait as reference to maintain consistent vibrant pixel-art style.

Output: out/hero01_q/sprites/
"""

import argparse
import concurrent.futures
import subprocess
import sys
from pathlib import Path

from PIL import Image

from audit_q_hero import audit_animation_group

HERE = Path(__file__).resolve().parent
REF_IMAGE = HERE / "out" / "hero01_q" / "portrait-q.png"
OUT_DIR = HERE / "out" / "hero01_q" / "sprites"
PROMPT_DIR = OUT_DIR / "prompts"
SHEET_DIR = OUT_DIR / "sheets"
SLICE_DIR = OUT_DIR / "slices"
SHEET_SIZE = 1024
FRAME_SIZE = 512

WALK_BASE = """You are given a reference image of a Q-version (chibi) pixel-art RPG character — an 11-12 year old Chinese boy with vibrant multi-tone shading, red scarf, school tracksuit, and backpack.

Your task: produce a SINGLE 1024x1024 image containing a 2x2 GRID of 4 walking-animation frames of EXACTLY THE SAME character.

Grid layout (read left-to-right, top-to-bottom):
- Top-left  (frame 1): {STEP1}
- Top-right (frame 2): {STEP2}
- Bot-left  (frame 3): {STEP3}
- Bot-right (frame 4): {STEP4}

ART STYLE — keep IDENTICAL to reference:
- Vibrant anime pixel art with bold dark outlines
- RICH MULTI-TONE SHADING:衣服/头发/鞋子都有 3+ 层高光/中间调/阴影，不要单色平涂
- High-contrast highlights on hair tips, fabric folds
- Saturated lively palette (vivid blue tracksuit, bright red scarf, white-red sneakers)
- Cel-shaded pixel art, glossy hand-painted feeling

CRITICAL — across all 4 frames keep IDENTICAL:
- Character size and proportions (每帧角色同样大小，2 头身 Q 版比例不变)
- Vertical position (feet at the same y-line across all 4 frames; do not let character float or shift height)
- Camera angle and distance (top-down 45-degree RPG view, identical zoom/perspective)
- Face, hairstyle (shamate side-bangs), outfit (tracksuit + red scarf + backpack), art style
- {DIRECTION_LOCK}
- All clothing details: red scarf, yellow inner collar, backpack straps, shoe laces

The ONLY thing that changes between frames is the leg/arm walking pose.

Layout rules:
- Each frame is exactly 512x512 pixels, arranged in a 2x2 grid
- Thin black 2-pixel borders separating frames are OK (will be cropped)
- Solid flat magenta background (#FF00FF) inside every frame, no glow or atmospheric effects
- Single character per frame, centered horizontally, full body visible

Final output: ONE image, 1024x1024, four walking frames in 2x2 grid, pure magenta backgrounds.
"""

BATTLE_BASE = """You are given a reference image of a Q-version (chibi) pixel-art RPG character — an 11-12 year old Chinese boy with vibrant multi-tone shading, red scarf, school tracksuit, and backpack.

Your task: produce a SINGLE 1024x1024 image containing a 2x2 GRID of 4 battle-animation frames of EXACTLY THE SAME character.

Grid layout (read left-to-right, top-to-bottom):
- Top-left  (frame 1): {STEP1}
- Top-right (frame 2): {STEP2}
- Bot-left  (frame 3): {STEP3}
- Bot-right (frame 4): {STEP4}

ART STYLE — keep IDENTICAL to reference:
- Vibrant anime pixel art with bold dark outlines
- RICH MULTI-TONE SHADING: 衣服/头发/鞋子都有 3+ 层高光/中间调/阴影，不要单色平涂
- High-contrast highlights on hair tips, fabric folds
- Saturated lively palette (vivid blue tracksuit, bright red scarf, white-red sneakers)
- Cel-shaded pixel art, glossy hand-painted feeling

CRITICAL — across all 4 frames keep IDENTICAL:
- Character size and proportions (每帧角色同样大小，2 头身 Q 版比例不变)
- Vertical position (feet at the same y-line across all 4 frames; do not let character float or shift height)
- Camera angle and distance (side view, character facing right, identical zoom/perspective)
- Face, hairstyle (shamate side-bangs), outfit (tracksuit + red scarf + backpack), art style
- All clothing details: red scarf, yellow inner collar, backpack straps, shoe laces

The ONLY thing that changes between frames is the action pose.

Layout rules:
- Each frame is exactly 512x512 pixels, arranged in a 2x2 grid
- Thin black 2-pixel borders separating frames are OK (will be cropped)
- Solid flat magenta background (#FF00FF) inside every frame, no glow or atmospheric effects
- Single character per frame, centered horizontally, full body visible

Final output: ONE image, 1024x1024, four battle frames in 2x2 grid, pure magenta backgrounds.
"""

DIRECTION_LOCK = {
    "down": "All 4 frames: character FACING DOWNWARD (toward viewer), camera looks at the FRONT",
    "up":   "All 4 frames: character FACING UPWARD (away from viewer), camera looks at the BACK",
    "left": "All 4 frames: character FACING LEFT (side profile to the left)",
    "right":"All 4 frames: character FACING RIGHT (side profile to the right)",
}

WALK_STEPS = {
    1: "neutral standing — both feet on ground, arms at sides (rest pose)",
    2: "LEFT FOOT stepping forward mid-stride, right leg supporting, arms swinging naturally",
    3: "neutral standing — both feet on ground, arms at sides (same rest pose as frame 1)",
    4: "RIGHT FOOT stepping forward mid-stride, left leg supporting, arms swinging naturally",
}

BATTLE_STEPS = {
    "idle": {
        1: "battle-ready idle stance, feet planted, slight crouch, arms relaxed but ready",
        2: "battle idle slight inhale, chest raised, arms slightly tensed",
        3: "battle idle neutral stance (same as frame 1)",
        4: "battle idle slight exhale, shoulders relaxed",
    },
    "attack": {
        1: "wind-up: stepping back with right foot, arms drawn back, preparing to punch",
        2: "swing forward: right arm thrown forward in punching motion, body twisted",
        3: "follow-through: arm fully extended forward, body weight on front foot",
        4: "recovery: arm pulled back, returning to ready stance",
    },
    "hurt": {
        1: "impact: head jerked back, body recoiling, eyes shut, mouth open in pain",
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


def latest_existing(paths):
    existing = [p for p in paths if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def sheet_path_for(anim_name: str):
    return latest_existing([
        SHEET_DIR / f"{anim_name}-sheet.jpg",
        SHEET_DIR / f"{anim_name}-sheet.jpeg",
        SHEET_DIR / f"{anim_name}-sheet.png",
    ])


def clear_edge_alpha(path: Path, pixels: int):
    if pixels <= 0:
        return
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    px = img.load()
    for y in range(h):
        for x in range(w):
            if x < pixels or x >= w - pixels or y < pixels or y >= h - pixels:
                px[x, y] = (0, 0, 0, 0)
    img.save(path, "PNG")


def find_alpha_components(alpha: Image.Image):
    width, height = alpha.size
    px = alpha.load()
    seen = set()
    components = []

    for start_y in range(height):
        for start_x in range(width):
            if px[start_x, start_y] == 0 or (start_x, start_y) in seen:
                continue

            stack = [(start_x, start_y)]
            seen.add((start_x, start_y))
            pixels = []
            x_min = x_max = start_x
            y_min = y_max = start_y

            while stack:
                x, y = stack.pop()
                pixels.append((x, y))
                x_min = min(x_min, x)
                x_max = max(x_max, x)
                y_min = min(y_min, y)
                y_max = max(y_max, y)
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and px[nx, ny] > 0
                        and (nx, ny) not in seen
                    ):
                        seen.add((nx, ny))
                        stack.append((nx, ny))

            components.append({
                "area": len(pixels),
                "bbox": (x_min, y_min, x_max + 1, y_max + 1),
                "pixels": pixels,
            })

    components.sort(key=lambda component: component["area"], reverse=True)
    return components


def remove_duplicate_large_components(path: Path, min_area=4096, large_ratio=0.2):
    """Keep one character when the model paints duplicate full-body sprites."""
    img = Image.open(path).convert("RGBA")
    alpha = img.getchannel("A")
    components = find_alpha_components(alpha)
    if not components:
        return False

    largest_area = components[0]["area"]
    large_components = [
        component
        for component in components
        if component["area"] >= min_area and component["area"] >= largest_area * large_ratio
    ]
    if len(large_components) <= 1:
        return False

    keep = set(large_components[0]["pixels"])
    px = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            if px[x, y][3] > 0 and (x, y) not in keep:
                px[x, y] = (0, 0, 0, 0)
    img.save(path, "PNG")
    return True


def normalize_animation_frames(frame_paths):
    """Re-anchor frames to a stable sprite origin using the alpha bounding box."""
    frames = []
    for path in frame_paths:
        img = Image.open(path).convert("RGBA")
        bbox = img.getchannel("A").getbbox()
        if not bbox:
            return
        frames.append((path, img, bbox))

    target_bottom = int(round(sorted(b[3] for _, _, b in frames)[len(frames) // 2]))
    target_bottom = min(FRAME_SIZE - 8, max(32, target_bottom))
    target_center_x = FRAME_SIZE // 2

    for path, img, bbox in frames:
        x0, y0, x1, y1 = bbox
        crop = img.crop(bbox)
        cw, ch = crop.size
        if cw >= FRAME_SIZE or ch >= FRAME_SIZE:
            continue
        paste_x = int(round(target_center_x - (cw / 2)))
        paste_y = int(round(target_bottom - ch))
        paste_x = max(0, min(FRAME_SIZE - cw, paste_x))
        paste_y = max(0, min(FRAME_SIZE - ch, paste_y))
        out = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
        out.paste(crop, (paste_x, paste_y), crop)
        out.save(path, "PNG")


def slice_sheet(sheet_path: Path, anim_name: str):
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
    SLICE_DIR.mkdir(parents=True, exist_ok=True)
    out_pngs = []
    for i, box in enumerate(coords, 1):
        crop = img.crop(box)
        out_png = SLICE_DIR / f"{anim_name}-{i}-raw.png"
        crop.save(out_png, "PNG")
        out_pngs.append(out_png)
    return out_pngs


def audit_ok(anim_name):
    errors, warnings, _stats = audit_animation_group(OUT_DIR, anim_name)
    return not errors, errors, warnings


def process_anim(
    anim_name,
    kind,
    sub,
    force=False,
    regenerate_sheet=False,
    max_attempts=2,
    edge_clean_pixels=2,
):
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    prompt_text = build_prompt(anim_name, kind, sub)
    prompt_path = PROMPT_DIR / f"{anim_name}.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    sheet_jpg = SHEET_DIR / f"{anim_name}-sheet.jpg"
    final_pngs = [OUT_DIR / f"{anim_name}-{i}.png" for i in (1, 2, 3, 4)]
    if all(p.exists() for p in final_pngs) and not force:
        ok, errors, warnings = audit_ok(anim_name)
        if ok:
            warn_msg = f", {len(warnings)} warnings" if warnings else ""
            return anim_name, True, f"skip (all 4 PNGs exist and QA passes{warn_msg})"

    py = sys.executable
    last_errors = []
    attempts = max(1, max_attempts)

    for attempt in range(1, attempts + 1):
        sheet_path = sheet_path_for(anim_name)
        reuse_existing_sheet = sheet_path is not None and not regenerate_sheet and attempt == 1
        if not reuse_existing_sheet:
            ok, msg = run_step(
                [py, str(HERE / "gen_with_gemini.py"), str(prompt_path),
                 "--aspect", "1:1", "--size", "1K",
                 "--ref", str(REF_IMAGE),
                 "-o", str(sheet_jpg.with_suffix(""))],
                f"gen-attempt-{attempt}",
            )
            if not ok:
                return anim_name, False, msg
            sheet_path = sheet_path_for(anim_name)

        if sheet_path is None:
            return anim_name, False, "[sheet] no existing or generated sheet found"

        try:
            frame_inputs = slice_sheet(sheet_path, anim_name)
        except Exception as e:
            return anim_name, False, f"[slice] {type(e).__name__}: {e}"

        for index, frame_input in enumerate(frame_inputs, 1):
            final_png = OUT_DIR / f"{anim_name}-{index}.png"
            ok, msg = run_step(
                [py, str(HERE / "jpg_to_png_alpha.py"), str(frame_input),
                 "-o", str(final_png),
                 "--mode", "auto", "--tolerance", "25", "--halo-passes", "4"],
                f"alpha-{anim_name}-{index}",
            )
            if not ok:
                return anim_name, False, msg
            clear_edge_alpha(final_png, edge_clean_pixels)
            remove_duplicate_large_components(final_png)

        normalize_animation_frames(final_pngs)

        ok, errors, warnings = audit_ok(anim_name)
        if ok:
            source = "existing sheet" if reuse_existing_sheet else f"new sheet attempt {attempt}"
            warn_msg = f", {len(warnings)} warnings" if warnings else ""
            return anim_name, True, f"4 frames QA OK from {source}{warn_msg} -> {OUT_DIR}"
        last_errors = errors
        regenerate_sheet = True

    short_errors = "; ".join(last_errors[:4])
    extra = "" if len(last_errors) <= 4 else f"; +{len(last_errors) - 4} more"
    return anim_name, False, f"QA failed after {attempts} attempt(s): {short_errors}{extra}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--anim", default="all", help="anim group name or 'all'")
    p.add_argument("--concurrency", type=int, default=2)
    p.add_argument("--force", action="store_true", help="Reprocess frames even if final PNGs already pass QA")
    p.add_argument("--regenerate-sheet", action="store_true",
                   help="Call the image model immediately instead of first reusing an existing sheet")
    p.add_argument("--max-attempts", type=int, default=2,
                   help="Attempts per animation. Attempt 1 reuses an existing sheet when available; later attempts regenerate.")
    p.add_argument("--edge-clean-pixels", type=int, default=2,
                   help="Clear this many outer pixels after alpha cutout to remove grid residue.")
    args = p.parse_args()

    if not REF_IMAGE.exists():
        print(f"[ERROR] reference image not found: {REF_IMAGE}")
        return 2

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
        futures = {
            pool.submit(
                process_anim,
                name,
                kind,
                sub,
                args.force,
                args.regenerate_sheet,
                args.max_attempts,
                args.edge_clean_pixels,
            ): name
            for name, kind, sub in targets
        }
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
