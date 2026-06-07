from __future__ import annotations

import argparse
import time
from pathlib import Path

from .export import TiledExporter, TiledJsonValidator, find_tiled, find_tmxrasterizer, verify_tiled_maps
from .map import MapGenerator
from .editor import EditorStateDocument, PartialRegenerationRequest, PartialRegenerator, SelectionRect, validate_editor_state_document
from .models import GenerateRequest, GenerationReport, TilemapData
from .models.base import read_json, write_model_json
from .parser import RulePromptParser
from .render import PreviewRenderer
from .validation import Validator
from .demo_cases import DEMO_NAMES
from .assets.image_generation import ImageStyle, MockImageGenerator
from .assets.object_generator import ObjectGenerator, generate_standard_objects
from .assets.asset_library import AssetLibrary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m generator.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate an RPG tilemap asset package.")
    generate.add_argument("--prompt")
    generate.add_argument("--prompt-file")
    generate.add_argument("--theme")
    generate.add_argument("--size", default="64x64")
    generate.add_argument("--seed", type=int)
    generate.add_argument("--tileset", default="default_rpg_32")
    generate.add_argument("--output", required=True)
    generate.add_argument("--debug-preview", action="store_true")

    validate = subparsers.add_parser("validate", help="Validate a map_data.json file.")
    validate.add_argument("--map-data", required=True)
    validate.add_argument("--output")

    export = subparsers.add_parser("export-tiled", help="Export a map_data.json file to Tiled JSON.")
    export.add_argument("--map-data", required=True)
    export.add_argument("--output", required=True)

    validate_editor = subparsers.add_parser("validate-editor-state", help="Validate an editor state JSON file.")
    validate_editor.add_argument("--editor-state", required=True)
    validate_editor.add_argument("--map-data")
    validate_editor.add_argument("--output")

    partial = subparsers.add_parser("partial-regenerate", help="Regenerate a selected map area while preserving locked regions.")
    partial.add_argument("--map-data", required=True)
    partial.add_argument("--editor-state", required=True)
    partial.add_argument("--prompt", required=True)
    partial.add_argument("--seed", type=int)
    partial.add_argument("--selection", help="Override editor state selection as x,y,width,height.")
    partial.add_argument("--output", required=True)
    partial.add_argument("--debug-preview", action="store_true")

    import_tiled = subparsers.add_parser("import-tiled", help="Import a Tiled JSON map back to map_data.json.")
    import_tiled.add_argument("--tiled-json", required=True)
    import_tiled.add_argument("--output", required=True)

    check_tiled = subparsers.add_parser("check-tiled", help="Check whether the Tiled editor executable is available.")
    check_tiled.add_argument("--tiled-path")
    check_tiled.add_argument("--tmxrasterizer-path")

    verify_demos = subparsers.add_parser("verify-tiled-demos", help="Run static Tiled checks for demo maps and report runtime Tiled availability.")
    verify_demos.add_argument("--outputs", default="examples/outputs")
    verify_demos.add_argument("--tiled-path")
    verify_demos.add_argument("--tmxrasterizer-path")
    verify_demos.add_argument("--runtime-output-dir", default="tmp/tiled_runtime_renders")
    verify_demos.add_argument("--output")
    verify_demos.add_argument("--all", action="store_true", help="Verify every map.tiled.json under --outputs instead of only standard Phase 1 demos.")

    generate_objects = subparsers.add_parser("generate-objects", help="Generate standard set of map objects.")
    generate_objects.add_argument("--output", required=True, help="Output directory for generated objects")
    generate_objects.add_argument("--style", default="pixel_art", choices=["pixel_art", "hand_drawn"], help="Visual style")
    generate_objects.add_argument("--tile-size", default="32x32", help="Base tile size")
    generate_objects.add_argument("--seed-offset", type=int, default=1000, help="Starting seed value")
    generate_objects.add_argument("--count", type=int, default=20, help="Number of objects to generate")

    list_objects = subparsers.add_parser("list-objects", help="List objects in asset library.")
    list_objects.add_argument("--library-dir", required=True, help="Directory containing object metadata")
    list_objects.add_argument("--tags", nargs="*", help="Filter by tags")
    list_objects.add_argument("--theme", nargs="*", help="Filter by theme")
    list_objects.add_argument("--stats", action="store_true", help="Show library statistics")

    args = parser.parse_args(argv)
    if args.command == "generate":
        generate_command(args)
    elif args.command == "validate":
        validate_command(args)
    elif args.command == "export-tiled":
        export_tiled_command(args)
    elif args.command == "validate-editor-state":
        validate_editor_state_command(args)
    elif args.command == "partial-regenerate":
        partial_regenerate_command(args)
    elif args.command == "import-tiled":
        import_tiled_command(args)
    elif args.command == "check-tiled":
        check_tiled_command(args)
    elif args.command == "verify-tiled-demos":
        verify_tiled_demos_command(args)
    elif args.command == "generate-objects":
        generate_objects_command(args)
    elif args.command == "list-objects":
        list_objects_command(args)


def generate_command(args) -> None:
    started = time.perf_counter()
    prompt = _read_prompt(args.prompt, args.prompt_file)
    request = GenerateRequest(
        prompt=prompt,
        theme=args.theme,
        map_size=_parse_size(args.size),
        seed=args.seed,
        tileset_id=args.tileset,
    )
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    spec = RulePromptParser().parse(request)
    tilemap = MapGenerator().generate(spec)
    validation_report = Validator().validate(tilemap)

    renderer = PreviewRenderer()
    tileset_path = output / "tilesets" / "default_rpg_32.png"
    renderer.ensure_tileset_png(tileset_path)
    renderer.render(tilemap, output / "preview.png", debug=False)
    if args.debug_preview:
        renderer.render(tilemap, output / "preview_debug.png", debug=True)

    tiled_path = output / "map.tiled.json"
    tiled = TiledExporter().export(tilemap, tiled_path)
    tiled_validation_report = TiledJsonValidator().validate(tiled)

    write_model_json(output / "map_spec.json", spec)
    write_model_json(output / "map_data.json", tilemap)
    write_model_json(output / "validation_report.json", validation_report)
    write_model_json(output / "tiled_validation_report.json", tiled_validation_report)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    output_files = [
        "map_spec.json",
        "map_data.json",
        "map.tiled.json",
        "preview.png",
        "validation_report.json",
        "tiled_validation_report.json",
        "generation_report.json",
        "tilesets/default_rpg_32.png",
    ]
    if args.debug_preview:
        output_files.append("preview_debug.png")
    generation_report = GenerationReport(
        prompt=prompt,
        seed=spec.seed,
        theme=spec.theme,
        map_size=[spec.map.width, spec.map.height],
        tile_size=[spec.map.tile_width, spec.map.tile_height],
        tileset_id=spec.tileset_id,
        elapsed_ms=elapsed_ms,
        output_files=output_files,
        validation_passed=validation_report.passed and tiled_validation_report.passed,
    )
    write_model_json(output / "generation_report.json", generation_report)
    print(f"Generated {output}")
    print(f"validation_passed={validation_report.passed}")
    print(f"tiled_validation_passed={tiled_validation_report.passed}")


def validate_command(args) -> None:
    tilemap = TilemapData.model_validate(read_json(args.map_data))
    report = Validator().validate(tilemap)
    if args.output:
        write_model_json(args.output, report)
    print(report.model_dump_json(indent=2))


def export_tiled_command(args) -> None:
    tilemap = TilemapData.model_validate(read_json(args.map_data))
    tiled = TiledExporter().export(tilemap, args.output)
    report = TiledJsonValidator().validate(tiled)
    print(f"Exported {args.output}")
    print(f"tiled_validation_passed={report.passed}")


def validate_editor_state_command(args) -> None:
    editor_state = EditorStateDocument.model_validate(read_json(args.editor_state))
    tilemap = TilemapData.model_validate(read_json(args.map_data)) if args.map_data else None
    report = validate_editor_state_document(editor_state, tilemap)
    if args.output:
        write_model_json(args.output, report)
    print(report.model_dump_json(indent=2))


def partial_regenerate_command(args) -> None:
    started = time.perf_counter()
    source_path = Path(args.map_data)
    tilemap = TilemapData.model_validate(read_json(source_path))
    editor_state = EditorStateDocument.model_validate(read_json(args.editor_state))
    request = PartialRegenerationRequest(
        prompt=args.prompt,
        seed=args.seed,
        editor_state=editor_state,
        selection=_parse_selection(args.selection) if args.selection else None,
    )
    regenerated, partial_report = PartialRegenerator().regenerate(tilemap, request)

    validation_report = Validator().validate(regenerated)
    partial_report.validation_passed = validation_report.passed

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    renderer = PreviewRenderer()
    tileset_path = output / "tilesets" / "default_rpg_32.png"
    renderer.ensure_tileset_png(tileset_path)
    renderer.render(regenerated, output / "preview.png", debug=False)
    if args.debug_preview:
        renderer.render(regenerated, output / "preview_debug.png", debug=True)

    tiled_path = output / "map.tiled.json"
    tiled = TiledExporter().export(regenerated, tiled_path)
    tiled_validation_report = TiledJsonValidator().validate(tiled)
    partial_report.tiled_validation_passed = tiled_validation_report.passed

    write_model_json(output / "map_data.json", regenerated)
    write_model_json(output / "validation_report.json", validation_report)
    write_model_json(output / "tiled_validation_report.json", tiled_validation_report)
    write_model_json(output / "partial_regeneration_report.json", partial_report)
    write_model_json(output / "editor_state.json", editor_state)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    output_files = [
        "map_data.json",
        "map.tiled.json",
        "preview.png",
        "validation_report.json",
        "tiled_validation_report.json",
        "partial_regeneration_report.json",
        "editor_state.json",
        "tilesets/default_rpg_32.png",
    ]
    if args.debug_preview:
        output_files.append("preview_debug.png")
    generation_report = GenerationReport(
        prompt=args.prompt,
        seed=partial_report.seed,
        theme=str(regenerated.metadata.get("theme", "")),
        map_size=[regenerated.map.width, regenerated.map.height],
        tile_size=[regenerated.map.tile_width, regenerated.map.tile_height],
        tileset_id=regenerated.tileset.id,
        elapsed_ms=elapsed_ms,
        output_files=output_files,
        validation_passed=validation_report.passed and tiled_validation_report.passed,
    )
    write_model_json(output / "generation_report.json", generation_report)
    print(f"Regenerated {output}")
    print(f"operation={partial_report.operation}")
    print(f"changed_tiles={partial_report.changed_tiles}")
    print(f"validation_passed={validation_report.passed}")
    print(f"tiled_validation_passed={tiled_validation_report.passed}")


def import_tiled_command(args) -> None:
    from .export.tiled_importer import TiledImporter

    tilemap = TiledImporter().import_file(args.tiled_json)
    write_model_json(args.output, tilemap)
    print(f"Imported {args.tiled_json} -> {args.output}")


def check_tiled_command(args) -> None:
    status = find_tiled(args.tiled_path)
    rasterizer_status = find_tmxrasterizer(status.executable, args.tmxrasterizer_path) if status.available else None
    print(f"available={status.available}")
    print(f"executable={status.executable or ''}")
    print(f"version={status.version or ''}")
    print(f"message={status.message}")
    if rasterizer_status:
        print(f"tmxrasterizer_available={rasterizer_status.available}")
        print(f"tmxrasterizer_executable={rasterizer_status.executable or ''}")
        print(f"tmxrasterizer_version={rasterizer_status.version or ''}")
        print(f"tmxrasterizer_message={rasterizer_status.message}")


def verify_tiled_demos_command(args) -> None:
    outputs = Path(args.outputs)
    if args.all:
        map_paths = sorted(outputs.glob("*/map.tiled.json"))
    else:
        map_paths = [outputs / name / "map.tiled.json" for name in DEMO_NAMES]
        map_paths = [path for path in map_paths if path.exists()]
    if not map_paths:
        raise SystemExit(f"No map.tiled.json files found under {outputs}.")
    result = verify_tiled_maps(
        map_paths,
        tiled_path=args.tiled_path,
        tmxrasterizer_path=args.tmxrasterizer_path,
        runtime_output_dir=args.runtime_output_dir,
    )
    if args.output:
        Path(args.output).write_text(_json_dumps(result), encoding="utf-8")
    print(_json_dumps(result))


def _json_dumps(data) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)


def _read_prompt(prompt: str | None, prompt_file: str | None) -> str:
    if prompt_file:
        return Path(prompt_file).read_text(encoding="utf-8").strip()
    if prompt:
        return prompt.strip()
    raise SystemExit("Either --prompt or --prompt-file is required.")


def generate_objects_command(args) -> None:
    """Generate standard set of map objects."""
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse style and tile size
    style = ImageStyle.PIXEL_ART if args.style == "pixel_art" else ImageStyle.HAND_DRAWN
    tile_size = tuple(map(int, args.tile_size.split("x")))

    # Create generators
    mock_image_gen = MockImageGenerator(output_dir / "tmp")
    obj_gen = ObjectGenerator(mock_image_gen, output_dir)

    print(f"Generating {args.count} objects...")
    print(f"Style: {args.style}, Tile size: {tile_size}, Seed offset: {args.seed_offset}")

    # Generate standard objects
    results = generate_standard_objects(
        obj_gen,
        style=style,
        tile_size=tile_size,
        seed_offset=args.seed_offset,
    )

    success_count = sum(1 for r in results if r.success)
    print(f"\nGenerated {success_count}/{len(results)} objects successfully")

    # List generated objects
    for result in results:
        if result.success:
            print(f"  - {result.asset_id}: {result.sprite_path}")
        else:
            print(f"  - Failed: {result.error}")

    # Export catalog
    library = AssetLibrary(output_dir)
    catalog_path = output_dir / "object_catalog.json"
    library.export_catalog(catalog_path)
    print(f"\nCatalog exported to {catalog_path}")

    # Show stats
    stats = library.get_stats()
    print(f"\nLibrary stats:")
    print(f"  Total assets: {stats['total_assets']}")
    print(f"  Unique tags: {stats['unique_tags']}")
    print(f"  By kind: {stats['by_kind']}")


def list_objects_command(args) -> None:
    """List objects in asset library."""
    library_dir = Path(args.library_dir)
    if not library_dir.exists():
        raise SystemExit(f"Library directory not found: {library_dir}")

    library = AssetLibrary(library_dir)

    if args.stats:
        stats = library.get_stats()
        print(_json_dumps(stats))
        return

    # Search with filters
    results = library.search(
        tags=args.tags if args.tags else None,
        themes=args.theme if args.theme else None,
    )

    if not results:
        print("No objects found matching filters")
        return

    print(f"Found {len(results)} objects:")
    for asset in results:
        tags_str = ", ".join(asset.tags)
        theme_str = ", ".join(asset.theme) if asset.theme else "none"
        footprint_str = f"{asset.footprint[0]}x{asset.footprint[1]}" if asset.footprint else "1x1"
        print(f"  {asset.asset_id}")
        print(f"    Tags: {tags_str}")
        print(f"    Theme: {theme_str}")
        print(f"    Footprint: {footprint_str}")


def _parse_size(value: str) -> tuple[int, int]:
    try:
        left, right = value.lower().split("x", 1)
        width, height = int(left), int(right)
    except ValueError as exc:
        raise SystemExit(f"Invalid --size value: {value}. Expected WIDTHxHEIGHT.") from exc
    if width < 16 or height < 16:
        raise SystemExit("Map size must be at least 16x16.")
    return width, height


def _parse_selection(value: str) -> SelectionRect:
    try:
        x, y, width, height = [int(part.strip()) for part in value.split(",", 3)]
    except ValueError as exc:
        raise SystemExit(f"Invalid --selection value: {value}. Expected x,y,width,height.") from exc
    return SelectionRect(x=x, y=y, width=width, height=height)


if __name__ == "__main__":
    main()
