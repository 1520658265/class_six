import json
from pathlib import Path

from generator.demo_cases import DEMO_CASES
from generator.export import TiledExporter
from generator.export import TiledJsonValidator
from generator.map import MapGenerator
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.render import PreviewRenderer
from generator.validation import Validator


def test_phase1_five_demo_prompts_generate_complete_asset_packages():
    root = Path(__file__).resolve().parents[1]
    parser = RulePromptParser()
    generator = MapGenerator()
    validator = Validator()
    exporter = TiledExporter()
    tiled_validator = TiledJsonValidator()
    renderer = PreviewRenderer()

    for _name, prompt_file, seed in DEMO_CASES:
        prompt = (root / prompt_file).read_text(encoding="utf-8").strip()

        spec = parser.parse(GenerateRequest(prompt=prompt, seed=seed))
        tilemap = generator.generate(spec)
        report = validator.validate(tilemap)
        tiled = exporter.to_dict(tilemap)
        tiled_report = tiled_validator.validate(tiled)
        preview = renderer.render_image(tilemap)

        assert report.passed, report.model_dump()
        assert tiled_report.passed, tiled_report.model_dump()
        assert spec.map.width == 64
        assert spec.map.height == 64
        assert preview.size == (64 * 32, 64 * 32)

        layer_names = {layer["name"] for layer in tiled["layers"]}
        assert {"terrain", "path", "building", "decoration", "collision", "objects", "events"} <= layer_names
        assert tiled["tilesets"]

        serialized = {
            "map_spec.json": spec.model_dump(mode="json", by_alias=True),
            "map_data.json": tilemap.model_dump(mode="json"),
            "validation_report.json": report.model_dump(mode="json"),
            "tiled_validation_report.json": tiled_report.model_dump(mode="json"),
            "map.tiled.json": tiled,
        }
        for data in serialized.values():
            assert json.loads(json.dumps(data, ensure_ascii=False))
        preview.close()
