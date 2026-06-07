"""Run an rpg-asset-gen style animation test for the Q hero.

The old pipeline generated 2x2 sheets and then sliced them. This test pipeline
writes a separate asset pack and prefers single-frame outputs, mirrored side
directions, anchor normalization, and visual QA previews.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from audit_q_hero import ImageStats, audit_animation_group, image_stats


HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE / "out" / "hero01_q"
SOURCE_SPRITES = SOURCE_ROOT / "sprites"
REF_IMAGE = SOURCE_ROOT / "portrait-q.png"
OUT_ROOT = HERE / "out" / "hero01_q_skilltest"

FRAME_SIZE = 512
TARGET_HEIGHT = {
    "walk-down": 462,
    "walk-up": 456,
    "walk-right": 452,
    "walk-left": 452,
}
TARGET_BOTTOM = {
    "walk-down": 500,
    "walk-up": 492,
    "walk-right": 492,
    "walk-left": 492,
}

WALK_DIRECT_GROUPS = ("walk-down", "walk-up", "walk-right")
WALK_ALL_GROUPS = ("walk-down", "walk-up", "walk-right", "walk-left")
ANIM_CYCLES = {
    "compact4": 4,
    "smooth8": 8,
}

COMPACT4_POSES = {
    1: "idle standing pose; both feet planted evenly; arms relaxed at the sides",
    2: "left foot stepping forward in a small RPG walk stride; opposite arm swings forward",
    4: "right foot stepping forward in a small RPG walk stride; opposite arm swings forward",
}

SMOOTH8_POSES = {
    1: "phase 1 of 8, compact contact pose; both feet close to the body, body upright, arms relaxed",
    2: "phase 2 of 8, front leg begins a tiny forward swing; arm swing starts; only a small change from phase 1",
    3: "phase 3 of 8, front foot reaches a moderate short stride; body dips very slightly; no large step",
    4: "phase 4 of 8, passing pose; legs return closer under the body; arms cross near neutral",
    5: "phase 5 of 8, opposite compact contact pose; same size and silhouette balance as phase 1",
    6: "phase 6 of 8, opposite leg begins a tiny forward swing; only a small change from phase 5",
    7: "phase 7 of 8, opposite foot reaches a moderate short stride; body dips very slightly; no large step",
    8: "phase 8 of 8, recovery passing pose close to phase 1 so the loop returns smoothly",
}

DIRECTION_PROMPTS = {
    "walk-down": (
        "front view facing the viewer; both eyes visible; chest, scarf knot, and front of "
        "tracksuit visible; not a side profile"
    ),
    "walk-up": (
        "back view facing away from the viewer; backpack centered and visible; back of "
        "head and tracksuit visible; face not visible"
    ),
    "walk-right": (
        "right-facing side profile, walking toward screen right; one eye visible; nose "
        "points right; not front-facing"
    ),
}


def ensure_dirs(root: Path) -> dict[str, Path]:
    dirs = {
        "inputs": root / "inputs",
        "references": root / "references",
        "prompts": root / "prompts",
        "raw": root / "raw",
        "raw_rejected": root / "raw" / "rejected",
        "final": root / "final",
        "sprites": root / "final" / "sprites",
        "qa": root / "qa",
        "gifs": root / "qa" / "animation_gifs",
        "strips": root / "qa" / "strips",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def write_manifest(root: Path, strategy: str, groups: list[str], cycle: str) -> None:
    frame_count = ANIM_CYCLES[cycle]
    manifest = {
        "schema": "rpg-asset-gen.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": "animation",
        "style": "q_chibi_pixel_rpg",
        "name": "hero01_walk_skilltest",
        "status": "draft",
        "strategy": strategy,
        "cycle": cycle,
        "frame_count": frame_count,
        "source_root": str(SOURCE_ROOT),
        "references": [str(REF_IMAGE)],
        "outputs": [f"final/sprites/{group}-{{1..{frame_count}}}.png" for group in groups],
        "qa": {
            "status": "not_run",
            "report": "qa/report.json",
            "requires_human_animation_review": True,
        },
        "style_lock": {
            "character": "11-12 year old Chinese schoolboy",
            "outfit": "blue-and-white school tracksuit, red scarf, backpack, white-red sneakers",
            "rendering": "Q-version chibi pixel art, bold dark outline, rich multi-tone shading",
            "background_key": "#FF00FF",
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def build_single_frame_prompt(group: str, frame: int, cycle: str) -> str:
    pose = SMOOTH8_POSES[frame] if cycle == "smooth8" else COMPACT4_POSES[frame]
    direction = DIRECTION_PROMPTS[group]
    smooth_rules = ""
    if cycle == "smooth8":
        smooth_rules = """
Smoothness lock: this is an 8-frame in-place walk cycle for a large 512px preview. Make the pose delta small and continuous.
Do not jump from idle to a full stride. Keep the head, torso, backpack, scarf knot, and feet anchor visually stable.
The attached extra reference image, when present, is the previous frame; preserve it and adjust only the limbs by one small phase."""
    return f"""Create one image, not a grid and not a sprite sheet.

Asset type: RPG walking animation frame.
Subject: exactly the same Q-version chibi pixel-art boy as the reference image: black shaggy side-bang hair, big eyes, blue-and-white school tracksuit, red scarf, small backpack, and white-red sneakers.
Style lock: vibrant anime pixel art, bold dark outlines, cel-shaded pixel look, rich multi-tone shading, saturated blue tracksuit, bright red scarf, 2-head chibi proportions.
Camera and direction lock: {direction}.
Pose: {pose}.
Continuity: same character, same size, same camera, same outfit, same palette, same line weight; only the arm and leg pose changes.
{smooth_rules}
Composition: full body visible, centered horizontally, feet near the same bottom line, generous padding.
Background: perfectly flat pure #FF00FF magenta chroma key only.
Avoid: labels, frame numbers, captions, signatures, watermarks, borders, grids, shadows, floor, extra characters, extra props, motion blur, glow, and effects.

Final output: one square image containing exactly one full-body character frame on a flat magenta background."""


def run_cmd(cmd: list[str], label: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=480)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout)[-1200:]
        raise RuntimeError(f"{label} failed with exit {result.returncode}: {tail}")


def latest_generated(stem: Path) -> Path:
    candidates = [stem.with_suffix(ext) for ext in (".png", ".jpg", ".jpeg")]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        raise FileNotFoundError(f"No generated image found for {stem}")
    return max(existing, key=lambda path: path.stat().st_mtime)


def strip_opaque_magenta(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    px = rgba.load()
    width, height = rgba.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = px[x, y]
            if a and r > 180 and b > 120 and g < 125 and (r - g) > 55 and (b - g) > 25:
                px[x, y] = (0, 0, 0, 0)
    return rgba


def normalize_to_frame(src: Path, dest: Path, group: str, mirror: bool = False) -> None:
    img = Image.open(src).convert("RGBA")
    img = strip_opaque_magenta(img)
    if mirror:
        img = ImageOps.mirror(img)

    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise ValueError(f"No opaque subject in {src}")

    crop = img.crop(bbox)
    target_h = TARGET_HEIGHT[group]
    scale = target_h / crop.height
    target_w = max(1, int(round(crop.width * scale)))
    if target_w > FRAME_SIZE - 24:
        scale = (FRAME_SIZE - 24) / crop.width
        target_w = int(round(crop.width * scale))
        target_h = int(round(crop.height * scale))
    resized = crop.resize((target_w, target_h), Image.Resampling.LANCZOS)

    out = Image.new("RGBA", (FRAME_SIZE, FRAME_SIZE), (0, 0, 0, 0))
    x = int(round((FRAME_SIZE - target_w) / 2))
    y = int(round(TARGET_BOTTOM[group] - target_h))
    x = max(0, min(FRAME_SIZE - target_w, x))
    y = max(0, min(FRAME_SIZE - target_h, y))
    out.paste(resized, (x, y), resized)
    out = strip_opaque_magenta(out)

    # Clear outer pixels so old sheet/grid residue cannot survive as import noise.
    px = out.load()
    for i in range(FRAME_SIZE):
        px[i, 0] = (0, 0, 0, 0)
        px[i, FRAME_SIZE - 1] = (0, 0, 0, 0)
        px[0, i] = (0, 0, 0, 0)
        px[FRAME_SIZE - 1, i] = (0, 0, 0, 0)

    dest.parent.mkdir(parents=True, exist_ok=True)
    out.save(dest, "PNG")


def generate_frame(root: Path, group: str, frame: int, extra_refs: list[Path], cycle: str) -> Path:
    dirs = ensure_dirs(root)
    prompt_path = dirs["prompts"] / f"{group}-{frame}.txt"
    prompt_path.write_text(build_single_frame_prompt(group, frame, cycle), encoding="utf-8")
    out_stem = dirs["raw"] / f"{group}-{frame}"

    cmd = [
        sys.executable,
        str(HERE / "gen_with_gemini.py"),
        str(prompt_path),
        "--aspect",
        "1:1",
        "--size",
        "1K",
        "--ref",
        str(REF_IMAGE),
    ]
    for ref in extra_refs:
        cmd.extend(["--ref", str(ref)])
    cmd.extend(["-o", str(out_stem)])
    run_cmd(cmd, f"gemini {group}-{frame}")
    return latest_generated(out_stem)


def convert_raw_to_final(root: Path, raw_path: Path, group: str, frame: int) -> Path:
    dirs = ensure_dirs(root)
    keyed = dirs["raw"] / f"{group}-{frame}-alpha.png"
    run_cmd(
        [
            sys.executable,
            str(HERE / "jpg_to_png_alpha.py"),
            str(raw_path),
            "-o",
            str(keyed),
            "--mode",
            "auto",
            "--tolerance",
            "20",
            "--halo-passes",
            "5",
            "--grid-cleanup",
            "off",
        ],
        f"alpha {group}-{frame}",
    )
    final = dirs["sprites"] / f"{group}-{frame}.png"
    normalize_to_frame(keyed, final, group)
    return final


def find_existing_raw(root: Path, group: str, frame: int) -> Path | None:
    raw_dir = ensure_dirs(root)["raw"]
    stem = raw_dir / f"{group}-{frame}"
    candidates = [stem.with_suffix(ext) for ext in (".png", ".jpg", ".jpeg")]
    existing = [path for path in candidates if path.exists()]
    return max(existing, key=lambda path: path.stat().st_mtime) if existing else None


def run_gemini_single(root: Path, groups: list[str], cycle: str) -> None:
    dirs = ensure_dirs(root)
    if not REF_IMAGE.exists():
        raise FileNotFoundError(f"Reference image missing: {REF_IMAGE}")

    generated_refs: dict[tuple[str, int], Path] = {}
    for group in groups:
        if group == "walk-left":
            continue
        if group not in WALK_DIRECT_GROUPS:
            raise ValueError(f"Gemini single-frame generation supports walking groups only: {group}")

        frame_count = ANIM_CYCLES[cycle]
        final1 = dirs["sprites"] / f"{group}-1.png"
        if not final1.exists():
            raw1 = find_existing_raw(root, group, 1) or generate_frame(root, group, 1, [], cycle)
            final1 = convert_raw_to_final(root, raw1, group, 1)
        generated_refs[(group, 1)] = final1

        frames_to_generate = range(2, frame_count + 1) if cycle == "smooth8" else (2, 4)
        previous = final1
        for frame in frames_to_generate:
            final = dirs["sprites"] / f"{group}-{frame}.png"
            if final.exists():
                previous = final
                continue
            refs = [previous]
            raw = find_existing_raw(root, group, frame) or generate_frame(root, group, frame, refs, cycle)
            final = convert_raw_to_final(root, raw, group, frame)
            generated_refs[(group, frame)] = final
            previous = final

        if cycle == "compact4":
            shutil.copyfile(final1, dirs["sprites"] / f"{group}-3.png")

    if "walk-left" in groups or "walk-right" in groups:
        derive_left_from_right(root, ANIM_CYCLES[cycle])


def run_local_repair(root: Path, groups: list[str], cycle: str) -> None:
    if cycle != "compact4":
        raise ValueError("local-repair only supports compact4 because the source pack has 4 frames.")
    dirs = ensure_dirs(root)
    for group in groups:
        if group == "walk-right" and "walk-left" in groups:
            # Existing left-facing frames are visually more side-locked; mirror them
            # for the right-facing QA candidate.
            source_group = "walk-left"
            mirror = True
        else:
            source_group = group
            mirror = False

        for frame in (1, 2, 4):
            src = SOURCE_SPRITES / f"{source_group}-{frame}.png"
            if not src.exists():
                raise FileNotFoundError(src)
            dest = dirs["sprites"] / f"{group}-{frame}.png"
            normalize_to_frame(src, dest, group, mirror=mirror)

        shutil.copyfile(dirs["sprites"] / f"{group}-1.png", dirs["sprites"] / f"{group}-3.png")


def derive_left_from_right(root: Path, frame_count: int) -> None:
    dirs = ensure_dirs(root)
    for frame in range(1, frame_count + 1):
        src = dirs["sprites"] / f"walk-right-{frame}.png"
        dest = dirs["sprites"] / f"walk-left-{frame}.png"
        if src.exists():
            normalize_to_frame(src, dest, "walk-left", mirror=True)


def checkerboard(size: tuple[int, int], cell: int = 24) -> Image.Image:
    width, height = size
    img = Image.new("RGBA", size, (52, 52, 52, 255))
    draw = ImageDraw.Draw(img)
    for y in range(0, height, cell):
        for x in range(0, width, cell):
            if ((x // cell) + (y // cell)) % 2:
                draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(72, 72, 72, 255))
    return img


def create_strip(root: Path, group: str, frame_count: int) -> Path:
    dirs = ensure_dirs(root)
    strip = checkerboard((FRAME_SIZE * frame_count, FRAME_SIZE + 38), 24)
    draw = ImageDraw.Draw(strip)
    for idx, frame in enumerate(range(1, frame_count + 1)):
        path = dirs["sprites"] / f"{group}-{frame}.png"
        img = Image.open(path).convert("RGBA")
        strip.alpha_composite(img, (idx * FRAME_SIZE, 0))
        draw.text((idx * FRAME_SIZE + 8, FRAME_SIZE + 10), f"{group}-{frame}", fill=(235, 235, 235, 255))
    out = dirs["strips"] / f"{group}_strip.png"
    strip.convert("RGB").save(out, "PNG")
    return out


def create_gif(root: Path, group: str, frame_count: int, duration: int) -> Path:
    dirs = ensure_dirs(root)
    frames = []
    bg = checkerboard((FRAME_SIZE, FRAME_SIZE), 24)
    for frame in range(1, frame_count + 1):
        img = bg.copy()
        sprite = Image.open(dirs["sprites"] / f"{group}-{frame}.png").convert("RGBA")
        img.alpha_composite(sprite)
        frames.append(img.convert("P", palette=Image.Palette.ADAPTIVE))
    out = dirs["gifs"] / f"{group}.gif"
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=duration, loop=0)
    return out


def create_contact_sheet(root: Path, groups: list[str], frame_count: int) -> Path:
    dirs = ensure_dirs(root)
    scale = 0.35
    thumb = int(FRAME_SIZE * scale)
    label_h = 28
    width = thumb * frame_count
    height = (thumb + label_h) * len(groups)
    sheet = checkerboard((width, height), 18)
    draw = ImageDraw.Draw(sheet)
    for row, group in enumerate(groups):
        y = row * (thumb + label_h)
        draw.text((8, y + 6), group, fill=(255, 255, 255, 255))
        for idx, frame in enumerate(range(1, frame_count + 1)):
            img = Image.open(dirs["sprites"] / f"{group}-{frame}.png").convert("RGBA")
            img = img.resize((thumb, thumb), Image.Resampling.NEAREST)
            sheet.alpha_composite(img, (idx * thumb, y + label_h))
    out = dirs["qa"] / "contact_sheet.png"
    sheet.convert("RGB").save(out, "PNG")
    return out


def audit_sequence(sprite_dir: Path, group: str, frame_count: int) -> tuple[list[str], list[str], list[ImageStats], dict]:
    if frame_count == 4:
        errors, warnings, stats = audit_animation_group(sprite_dir, group)
    else:
        errors = []
        warnings = []
        stats = [image_stats(sprite_dir / f"{group}-{frame}.png") for frame in range(1, frame_count + 1)]
        for frame, item in enumerate(stats, 1):
            label = f"{group}-{frame}"
            if item.error:
                errors.append(f"{label}: {item.error}: {item.path}")
                continue
            if item.size != (FRAME_SIZE, FRAME_SIZE):
                errors.append(f"{label}: expected {(FRAME_SIZE, FRAME_SIZE)}, got {item.size}: {item.path}")
            if not item.has_alpha:
                errors.append(f"{label}: PNG has no alpha channel: {item.path}")
            elif item.transparent_pct <= 1.0:
                errors.append(f"{label}: almost no transparent background ({item.transparent_pct:.2f}%): {item.path}")
            if item.edge_opaque_pct > 0.5:
                errors.append(f"{label}: edge residue too high ({item.edge_opaque_pct:.2f}% > 0.50%)")
            if item.opaque_magenta_pct > 0.1:
                errors.append(f"{label}: opaque magenta residue too high ({item.opaque_magenta_pct:.3f}% > 0.100%)")

    valid = [item for item in stats if not item.error and item.has_alpha and item.bbox]
    metrics = {
        "frame_count": frame_count,
        "center_x_range": None,
        "bottom_range": None,
        "bbox_width_ratio": None,
        "bbox_height_ratio": None,
        "max_consecutive_width_delta": None,
        "max_consecutive_opaque_delta": None,
    }
    if len(valid) == frame_count:
        centers = [item.bbox_center_x for item in valid]
        bottoms = [item.bbox[3] for item in valid if item.bbox]
        widths = [max(1, item.bbox_width) for item in valid]
        heights = [max(1, item.bbox_height) for item in valid]
        opaque = [item.opaque_pct for item in valid]
        width_deltas = [abs(widths[i] - widths[i - 1]) for i in range(1, len(widths))]
        opaque_deltas = [abs(opaque[i] - opaque[i - 1]) for i in range(1, len(opaque))]
        metrics.update({
            "center_x_range": max(centers) - min(centers),
            "bottom_range": max(bottoms) - min(bottoms),
            "bbox_width_ratio": max(widths) / min(widths),
            "bbox_height_ratio": max(heights) / min(heights),
            "max_consecutive_width_delta": max(width_deltas) if width_deltas else 0,
            "max_consecutive_opaque_delta": max(opaque_deltas) if opaque_deltas else 0,
        })
        if metrics["center_x_range"] > 12:
            errors.append(f"{group}: center X range too high for smooth cycle ({metrics['center_x_range']:.1f}px > 12px)")
        if metrics["bottom_range"] > 3:
            errors.append(f"{group}: feet/bottom anchor range too high ({metrics['bottom_range']:.1f}px > 3px)")
        if frame_count >= 8 and metrics["max_consecutive_width_delta"] > 36:
            warnings.append(
                f"{group}: large consecutive silhouette width jump "
                f"({metrics['max_consecutive_width_delta']:.1f}px > 36px); inspect GIF"
            )
        if frame_count >= 8 and metrics["max_consecutive_opaque_delta"] > 4.0:
            warnings.append(
                f"{group}: large consecutive opaque-area jump "
                f"({metrics['max_consecutive_opaque_delta']:.2f}% > 4.00%); inspect GIF"
            )
    return errors, warnings, stats, metrics


def run_qa(root: Path, groups: list[str], strategy: str, cycle: str) -> dict:
    dirs = ensure_dirs(root)
    frame_count = ANIM_CYCLES[cycle]
    report = {
        "root": str(root.resolve()),
        "strategy": strategy,
        "cycle": cycle,
        "frame_count": frame_count,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "ok": True,
        "groups": {},
        "human_review_required": True,
        "semantic_checks": [
            "direction must match filename in all four frames",
            "frame 3 must return cleanly to frame 1",
            "camera angle must not change between frames",
            "outfit, hair, scarf, backpack, and palette must not flicker",
            "for smooth8, consecutive poses must change in small increments without idle-to-full-stride jumps",
        ],
        "process_findings": [
            "The previous 2x2-sheet workflow can pass structural QA while still failing animation semantics.",
            "Side walking directions should use one generated side and mirror the opposite side to avoid direction drift.",
            "Frame 3 is copied from frame 1 only for compact4 loops; do not use this for high-resolution smooth previews.",
            "When the preview looks choppy at 512px, promote the workflow to smooth8 instead of only fixing anchors.",
            "A structural pass does not mean final approval; inspect GIF and strip previews before promoting assets.",
        ],
    }
    for group in groups:
        errors, warnings, stats, metrics = audit_sequence(dirs["sprites"], group, frame_count)
        report["groups"][group] = {
            "ok": not errors,
            "errors": errors,
            "warnings": warnings,
            "stats": [asdict(item) for item in stats],
            "metrics": metrics,
            "strip": f"qa/strips/{group}_strip.png",
            "gif": f"qa/animation_gifs/{group}.gif",
        }
        if errors:
            report["ok"] = False
    manual_review_path = dirs["qa"] / "manual_review.json"
    if manual_review_path.exists():
        report["human_review_result"] = json.loads(manual_review_path.read_text(encoding="utf-8"))
    (dirs["qa"] / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def update_manifest_after_qa(root: Path, report: dict) -> None:
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "qa_structural_pass" if report["ok"] else "qa_failed"
    manifest["qa"] = {
        "status": "structural_pass" if report["ok"] else "failed",
        "report": "qa/report.json",
        "requires_human_animation_review": True,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def create_preview(root: Path, groups: list[str], report: dict) -> Path:
    status = "PASS" if report["ok"] else "FAIL"
    human = report.get("human_review_result") or {
        "status": "pending",
        "reason": "Manual GIF/strip continuity review has not been recorded.",
        "recommendation": "Inspect the animation before promoting assets to final.",
    }
    human_status = str(human.get("status", "pending"))
    human_class = "pass" if human_status in {"accept_for_final", "approved"} else "fail" if "reject" in human_status else "pending"
    cards = []
    for group in groups:
        group_report = report["groups"][group]
        qa = "PASS" if group_report["ok"] else "FAIL"
        cards.append(f"""
        <section class="card">
          <h2>{group} <span class="{qa.lower()}">{qa}</span></h2>
          <img class="strip" src="qa/strips/{group}_strip.png" alt="{group} strip">
          <div class="frames">
            <img src="qa/animation_gifs/{group}.gif" alt="{group} gif">
            <div class="note">Structural QA: {qa}. Human continuity review is still required.</div>
          </div>
        </section>""")

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>RPG Animation Skill Test</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #202124; color: #f5f5f5; }}
    main {{ max-width: 1240px; margin: 0 auto; padding: 24px; }}
    h1 {{ font-size: 24px; margin: 0 0 8px; }}
    .summary {{ color: #c8c8c8; margin-bottom: 22px; }}
    .card {{ border: 1px solid #444; background: #2a2b2e; border-radius: 8px; padding: 16px; margin-bottom: 18px; }}
    h2 {{ font-size: 18px; margin: 0 0 12px; }}
    .pass {{ color: #7bd88f; }}
    .fail {{ color: #ff7b72; }}
    .pending {{ color: #ffd166; }}
    .review {{ border: 1px solid #5f5141; background: #332d24; padding: 12px; border-radius: 8px; margin-bottom: 18px; }}
    .strip {{ width: 100%; max-width: 1024px; image-rendering: pixelated; border: 1px solid #555; display: block; }}
    .frames {{ display: flex; gap: 16px; align-items: center; margin-top: 12px; flex-wrap: wrap; }}
    .frames img {{ width: 192px; height: 192px; object-fit: contain; image-rendering: pixelated; border: 1px solid #555; }}
    .note {{ color: #c8c8c8; font-size: 14px; }}
    a {{ color: #8ab4f8; }}
  </style>
</head>
<body>
  <main>
    <h1>RPG Animation Skill Test - {status}</h1>
    <div class="summary">
      Output follows the rpg-asset-gen animation flow: single-frame candidates, mirrored side direction, anchor normalization, GIF/strip QA.
      Cycle: {report.get('cycle')} ({report.get('frame_count')} frames).
      Report: <a href="qa/report.json">qa/report.json</a>
    </div>
    <div class="review">
      Human review: <strong class="{human_class}">{human_status}</strong><br>
      {human.get('reason', '')}<br>
      {human.get('recommendation', '')}
    </div>
    {''.join(cards)}
  </main>
</body>
</html>
"""
    out = root / "preview.html"
    out.write_text(html, encoding="utf-8")
    return out


def parse_groups(anim: str) -> list[str]:
    if anim == "walk":
        return list(WALK_ALL_GROUPS)
    if anim in WALK_ALL_GROUPS:
        return [anim]
    raise ValueError(f"Unsupported anim '{anim}'. Use walk, walk-down, walk-up, walk-left, or walk-right.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=("local-repair", "gemini-single"), default="local-repair")
    parser.add_argument("--cycle", choices=tuple(ANIM_CYCLES), default="compact4")
    parser.add_argument("--anim", default="walk")
    parser.add_argument("--out", default=str(OUT_ROOT))
    parser.add_argument("--qa-only", action="store_true", help="Rebuild QA and preview from existing final sprites.")
    args = parser.parse_args()

    root = Path(args.out)
    groups = parse_groups(args.anim)
    ensure_dirs(root)
    write_manifest(root, args.strategy, groups, args.cycle)

    if not args.qa_only:
        if args.strategy == "local-repair":
            run_local_repair(root, groups, args.cycle)
        else:
            direct_groups = [group for group in groups if group != "walk-left"]
            run_gemini_single(root, direct_groups, args.cycle)
            if "walk-left" in groups:
                derive_left_from_right(root, ANIM_CYCLES[args.cycle])

    frame_count = ANIM_CYCLES[args.cycle]
    duration = 105 if args.cycle == "smooth8" else 180
    for group in groups:
        create_strip(root, group, frame_count)
        create_gif(root, group, frame_count, duration)
    create_contact_sheet(root, groups, frame_count)
    report = run_qa(root, groups, args.strategy, args.cycle)
    update_manifest_after_qa(root, report)
    preview = create_preview(root, groups, report)

    print(f"[INFO] output: {root.resolve()}")
    print(f"[INFO] preview: {preview.resolve()}")
    print(f"[INFO] status: {'OK' if report['ok'] else 'FAIL'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
