from __future__ import annotations

import argparse
from pathlib import Path

from .background_plan import build_background_plan, extract_background_tiles, write_background_review_html
from .concept import generate_scene_concept
from .images import generate_scene_images
from .map_build import build_scene_map
from .pack import pack_scene
from .status import scene_status_text
from .validation import validate_scene_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python generate.py scene-*")
    subparsers = parser.add_subparsers(dest="command", required=True)

    map_build = subparsers.add_parser("scene-map-build")
    map_build.add_argument("scene_dir", type=Path)
    map_build.add_argument("--force", action="store_true")

    concept = subparsers.add_parser("scene-concept")
    concept.add_argument("scene_dir", type=Path)
    concept.add_argument("--gemini", action="store_true")
    concept.add_argument("--force", action="store_true")

    background_plan = subparsers.add_parser("scene-background-plan")
    background_plan.add_argument("scene_dir", type=Path)
    background_plan.add_argument("--force", action="store_true")
    background_plan.add_argument("--concept-image")

    background_review = subparsers.add_parser("scene-background-review")
    background_review.add_argument("scene_dir", type=Path)
    background_review.add_argument("--force", action="store_true")

    background_assets = subparsers.add_parser("scene-background-assets")
    background_assets.add_argument("scene_dir", type=Path)
    background_assets.add_argument("--force", action="store_true")
    background_assets.add_argument("--gemini", action="store_true")

    images = subparsers.add_parser("scene-images")
    images.add_argument("scene_dir", type=Path)
    images.add_argument("--gemini", action="store_true")
    images.add_argument("--force", action="store_true")
    images.add_argument("--variants", type=int, default=1)
    images.add_argument("--target")

    pack = subparsers.add_parser("scene-pack")
    pack.add_argument("scene_dir", type=Path)
    pack.add_argument("--force", action="store_true")
    pack.add_argument("--resource-base")

    status = subparsers.add_parser("scene-status")
    status.add_argument("scene_dir", type=Path)

    validate = subparsers.add_parser("scene-validate")
    validate.add_argument("scene_dir", type=Path)
    validate.add_argument("--stage")

    args = parser.parse_args(argv)

    if args.command == "scene-map-build":
        build_scene_map(args.scene_dir, force=args.force)
        print(f"[ok] scene-map-build: {args.scene_dir}")
        return 0
    if args.command == "scene-concept":
        result = generate_scene_concept(args.scene_dir, use_gemini=args.gemini, force=args.force)
        print(f"[ok] scene-concept: {result['image']}")
        return 0
    if args.command == "scene-background-plan":
        plan = build_background_plan(args.scene_dir, force=args.force, concept_image=args.concept_image)
        print(f"[ok] scene-background-plan: {len(plan.get('review_items', []))} review item(s)")
        return 0
    if args.command == "scene-background-review":
        html_path = write_background_review_html(args.scene_dir, force=args.force)
        print(f"[ok] scene-background-review: {html_path}")
        return 0
    if args.command == "scene-background-assets":
        written = extract_background_tiles(args.scene_dir, force=args.force, use_gemini=args.gemini)
        print(f"[ok] scene-background-assets: {len(written)} asset(s)")
        return 0
    if args.command == "scene-images":
        generated = generate_scene_images(
            args.scene_dir,
            use_gemini=args.gemini,
            force=args.force,
            variants=args.variants,
            target=args.target,
        )
        print(f"[ok] scene-images: {len(generated)} target(s)")
        return 0
    if args.command == "scene-pack":
        manifest = pack_scene(args.scene_dir, force=args.force, resource_base=args.resource_base)
        metadata = manifest["metadata"]
        print(f"[ok] scene-pack: {metadata.get('fulfilled_count', metadata['generated_count'])}/{metadata['total_objects']}")
        return 0
    if args.command == "scene-status":
        print(scene_status_text(args.scene_dir))
        return 0
    if args.command == "scene-validate":
        issues = validate_scene_file(args.scene_dir, args.stage)
        errors = [issue for issue in issues if issue.severity == "error"]
        for issue in issues:
            print(f"[{issue.severity}] {issue.path}: {issue.message}")
        if errors:
            print(f"[failed] {len(errors)} error(s)")
            return 1
        print("[ok] validation passed")
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2
