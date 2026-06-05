"""
Generate Q-version (chibi, 2-head-tall) hero portrait and 7 expression faces.

Flow:
1. Generate Q-version portrait using v5 portrait as facial reference
2. Run magenta cutout -> portrait-q.png
3. Use the new Q portrait as reference, generate 7 expression close-ups in parallel
4. Cut alpha for each

Output dir: out/hero01_q/
"""

import argparse
import concurrent.futures
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ORIGINAL_REF = Path(r"D:\证件照片\1.jpg")
FALLBACK_REF = HERE / "out" / "hero01" / "_test-portrait-v5-magenta.jpg"
OUT_DIR = HERE / "out" / "hero01_q"
PROMPT_DIR = OUT_DIR / "prompts"

PORTRAIT_PROMPT = """You are given a reference image of a sixth-grade Chinese boy from 2008.

Your task: redraw the SAME character as a vibrant, eye-catching Q-version pixel-art RPG hero.

ART STYLE — PIXEL ART RPG (like LiblibAI-style anime pixel hero illustrations):
- Anime-pixel art with crisp pixel edges and bold dark outlines around every shape
- RICH MULTI-TONE SHADING on every clothing element: each color has at least 3 shades (highlight + midtone + shadow), no flat single-color blocks
- HIGH-CONTRAST highlights: bright white/near-white pixel highlights on hair tips, fabric folds, metal accessories
- Saturated, lively palette — push colors to vivid, NOT muted school-uniform gray-blue
- Cel-shaded with hand-painted feeling, expressive and glossy, like a hero card art

CHARACTER PROPORTIONS — Q-version chibi:
- 2-to-2.5 head-tall body, big head, short stubby limbs
- BIG round expressive anime eyes (~30% of face), small mouth, soft rounded cheeks, adorable

PRESERVE from reference (so the character stays recognizable):
- Shamate side-bangs hairstyle (long sweeping black bangs, stiff styled, 2008 look)
- Skin tone
- Overall vibe of an 11-12 year old Chinese boy

OUTFIT — keep the school sportswear theme but UPGRADE it visually:
- Blue-and-white school tracksuit jacket as the BASE, but with multi-tone shading and white piping/stripes down the sleeves
- Bright RED scarf (red pioneer scarf / 红领巾) tied around neck — vivid red with white highlights and shadow folds, this is the main accent color
- Inner T-shirt collar visible, bright contrast color (bright yellow or warm orange)
- A small school backpack on his back (visible straps over both shoulders, navy with bright accent stripes)
- White sneakers with red accent details

POSE & FRAMING:
- Standing front view, full body visible from head to toe, slight heroic confident stance
- Arms relaxed at sides or one hand adjusting backpack strap
- Friendly slight smile, eyes looking forward with a determined sparkle
- Single character, centered horizontally and vertically, full body fits inside the frame with small margin

BACKGROUND:
- Solid flat magenta (exact hex #FF00FF), completely uniform, no gradient, no glow, no wisps, no atmospheric effects
- The character itself has detailed shading and highlights, but the background is PURE FLAT MAGENTA with no decoration

Final output: a single colorful, detailed Q-version chibi pixel-art hero portrait, 1024x1024, magenta background.
"""

FACE_BASE = """You are given a reference image of a Q-version (chibi) character — an 11-12 year old Chinese boy in 2008 with shamate side-bangs hairstyle and blue school tracksuit.

Your task: redraw the SAME character's HEAD/FACE close-up with a specific expression.

Framing:
- Close-up portrait, head and upper shoulders visible (no full body)
- Centered in frame

Keep IDENTICAL to the reference:
- Q-version chibi art style (big anime eyes, soft cheeks, cel-shaded pixel art)
- Hairstyle (shamate side-bangs)
- Skin tone
- Tracksuit collar visible at bottom
- All facial structural features

CHANGE the expression to:
- {EXPRESSION}

Background:
- Solid flat magenta (#FF00FF), no gradient

Final output: 1024x1024, single character face close-up, magenta background.
"""

EXPRESSIONS = {
    "neutral": "calm relaxed expression, mouth in a tiny natural smile, eyes looking straight ahead",
    "happy": "big bright smile showing joy, eyes curved into happy crescents, cheeks slightly raised",
    "angry": "eyebrows furrowed downward, mouth pressed tight or slightly open showing frustration, eyes narrowed",
    "sad": "eyebrows tilted upward in the middle, mouth turned slightly down, eyes looking down with a melancholy mood",
    "surprised": "eyes wide open in shock, eyebrows raised, mouth open in a small O shape",
    "shy": "soft light blush on both cheeks, eyes looking slightly away to the side, small bashful smile, head tilted a little",
    "hurt": "dizzy tired expression, eyes squeezed shut, eyebrows pulled together, small uneasy grimace, no wounds, no blood",
}


def run(cmd, label, timeout=300):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return False, f"[{label}] exit {r.returncode}: {(r.stderr or r.stdout)[-300:]}"
        return True, ""
    except subprocess.TimeoutExpired:
        return False, f"[{label}] timeout"
    except Exception as e:
        return False, f"[{label}] {type(e).__name__}: {e}"


def gen_one(name, prompt_text, ref_image: Path, force=False):
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt_path = PROMPT_DIR / f"{name}.txt"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    raw_jpg = OUT_DIR / f"{name}.jpg"
    final_png = OUT_DIR / f"{name}.png"

    if final_png.exists() and not force:
        return name, True, "skip (exists)"

    py = sys.executable
    if not raw_jpg.exists() or force:
        ok, msg = run(
            [py, str(HERE / "gen_with_gemini.py"), str(prompt_path),
             "--aspect", "1:1", "--size", "1K",
             "--ref", str(ref_image),
             "-o", str(raw_jpg.with_suffix(""))],
            "gen",
        )
        if not ok:
            return name, False, msg

    ok, msg = run(
        [py, str(HERE / "jpg_to_png_alpha.py"), str(raw_jpg),
         "-o", str(final_png),
         "--mode", "global", "--tolerance", "25", "--halo-passes", "4"],
        "alpha",
    )
    if not ok:
        return name, False, msg
    return name, True, str(final_png)


def resolve_portrait_reference(ref_arg: str | None):
    if ref_arg:
        return Path(ref_arg)
    if DEFAULT_ORIGINAL_REF.exists():
        return DEFAULT_ORIGINAL_REF
    return FALLBACK_REF


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--only", choices=("portrait", "faces", "all"), default="all")
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--ref", help="Portrait reference image. Default: D:\\证件照片\\1.jpg, fallback to prior hero01 portrait.")
    p.add_argument("--force", action="store_true", help="Regenerate images even if final PNGs already exist")
    p.add_argument("--face", choices=tuple(EXPRESSIONS.keys()), action="append",
                   help="Only generate this face expression. Repeatable. Applies when --only faces/all.")
    args = p.parse_args()

    portrait_png = OUT_DIR / "portrait-q.png"

    if args.only in ("portrait", "all"):
        portrait_ref = resolve_portrait_reference(args.ref)
        if not portrait_ref.exists():
            print(f"[ERROR] portrait reference not found: {portrait_ref}")
            return 1
        print("[STEP 1] Generating Q-version portrait...")
        print(f"[INFO] portrait reference: {portrait_ref}")
        name, ok, msg = gen_one("portrait-q", PORTRAIT_PROMPT, portrait_ref, args.force)
        tag = "OK" if ok else "FAIL"
        print(f"[{tag}] {name}: {msg}")
        if not ok:
            return 1

    if args.only in ("faces", "all"):
        if not portrait_png.exists():
            print(f"[ERROR] portrait reference not found: {portrait_png}")
            return 1

        jobs = []
        for emo, desc in EXPRESSIONS.items():
            if args.face and emo not in args.face:
                continue
            name = f"face-q-{emo}"
            text = FACE_BASE.replace("{EXPRESSION}", desc)
            jobs.append((name, text))

        print()
        print(f"[STEP 2] Generating {len(jobs)} Q-version expression faces (concurrency={args.concurrency})...")

        fail = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = {pool.submit(gen_one, n, t, portrait_png, args.force): n for n, t in jobs}
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
            for n, m in fail:
                print(f"  {n}: {m}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
