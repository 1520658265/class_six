from generator.export import TiledExporter, TiledJsonValidator
from generator.map import MapGenerator
from generator.models import GenerateRequest
from generator.parser import RulePromptParser


def test_tiled_exporter_outputs_required_layers_and_tileset():
    spec = RulePromptParser().parse(
        GenerateRequest(
            prompt="生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙",
            seed=20260605,
        )
    )
    tilemap = MapGenerator().generate(spec)

    tiled = TiledExporter().to_dict(tilemap)

    assert tiled["type"] == "map"
    assert tiled["orientation"] == "orthogonal"
    assert tiled["width"] == 64
    assert tiled["height"] == 64
    assert tiled["tilesets"][0]["firstgid"] == 1
    layers = {layer["name"]: layer for layer in tiled["layers"]}
    assert {"terrain", "path", "building", "decoration", "collision", "objects", "events"} <= set(layers)
    assert layers["collision"]["visible"] is False
    assert layers["objects"]["type"] == "objectgroup"
    assert layers["events"]["type"] == "objectgroup"


def test_tiled_validator_accepts_exported_map():
    spec = RulePromptParser().parse(
        GenerateRequest(
            prompt="生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙",
            seed=20260605,
        )
    )
    tilemap = MapGenerator().generate(spec)
    tiled = TiledExporter().to_dict(tilemap)

    report = TiledJsonValidator().validate(tiled)

    assert report.passed, report.model_dump()
    assert report.metrics["layer_count"] == 7
    assert report.metrics["tile_layer_count"] == 5
    assert report.metrics["object_layer_count"] == 2
