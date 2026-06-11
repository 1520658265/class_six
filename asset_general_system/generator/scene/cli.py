from __future__ import annotations

import argparse
from pathlib import Path

from .background_plan import build_background_plan, extract_background_tiles, write_background_review_html
from .concept import generate_scene_concept
from .images import generate_scene_images
from .map_build import build_scene_map
from .pack import pack_scene
from .status import scene_status_text
from .tilemap_art import (
    build_tile_candidates,
    build_tile_family_plan,
    build_tilemap_blueprint,
    build_tilemap_mapping,
    export_tilemap_to_tiled,
    generate_pixellab_tilesets,
)
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

    tilemap_blueprint = subparsers.add_parser("scene-tilemap-blueprint")
    tilemap_blueprint.add_argument("scene_dir", type=Path)
    tilemap_blueprint.add_argument("--force", action="store_true")

    tile_family_plan = subparsers.add_parser("scene-tilemap-family-plan")
    tile_family_plan.add_argument("scene_dir", type=Path)
    tile_family_plan.add_argument("--force", action="store_true")

    tileset_generate = subparsers.add_parser("scene-tileset-generate")
    tileset_generate.add_argument("scene_dir", type=Path)
    tileset_generate.add_argument("--pixellab", action="store_true")
    tileset_generate.add_argument("--run-api", action="store_true")
    tileset_generate.add_argument("--force", action="store_true")
    tileset_generate.add_argument("--case")

    tile_candidates = subparsers.add_parser("scene-tilemap-candidates")
    tile_candidates.add_argument("scene_dir", type=Path)
    tile_candidates.add_argument("--force", action="store_true")

    tilemap_mapping = subparsers.add_parser("scene-tilemap-mapping")
    tilemap_mapping.add_argument("scene_dir", type=Path)
    tilemap_mapping.add_argument("--force", action="store_true")

    tiled_export = subparsers.add_parser("scene-tilemap-export-tiled")
    tiled_export.add_argument("scene_dir", type=Path)
    tiled_export.add_argument("--force", action="store_true")

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
    if args.command == "scene-tilemap-blueprint":
        blueprint = build_tilemap_blueprint(args.scene_dir, force=args.force)
        print(f"[ok] scene-tilemap-blueprint: {len(blueprint['layers']['cells'])} cell(s)")
        return 0
    if args.command == "scene-tilemap-family-plan":
        plan = build_tile_family_plan(args.scene_dir, force=args.force)
        print(f"[ok] scene-tilemap-family-plan: {len(plan.get('groups', []))} group(s)")
        return 0
    if args.command == "scene-tileset-generate":
        if not args.pixellab:
            parser.error("scene-tileset-generate currently requires --pixellab")
        manifest = generate_pixellab_tilesets(args.scene_dir, run_api=args.run_api, force=args.force, case=args.case)
        print(f"[ok] scene-tileset-generate: {len(manifest.get('groups', []))} group(s), run_api={manifest.get('run_api')}")
        return 0
    if args.command == "scene-tilemap-candidates":
        candidates = build_tile_candidates(args.scene_dir, force=args.force)
        print(f"[ok] scene-tilemap-candidates: {len(candidates.get('candidates', []))} candidate(s)")
        return 0
    if args.command == "scene-tilemap-mapping":
        mapping = build_tilemap_mapping(args.scene_dir, force=args.force)
        print(f"[ok] scene-tilemap-mapping: {len(mapping.get('assignments', []))} assignment(s), {len(mapping.get('issues', []))} issue(s)")
        return 0
    if args.command == "scene-tilemap-export-tiled":
        exported = export_tilemap_to_tiled(args.scene_dir, force=args.force)
        print(f"[ok] scene-tilemap-export-tiled: {exported['tmj']}")
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
