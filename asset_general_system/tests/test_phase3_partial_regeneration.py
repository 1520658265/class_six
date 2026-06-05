from generator.editor import (
    EditorLockedRegionDocument,
    EditorMapDocument,
    EditorStateDocument,
    PartialRegenerationRequest,
    PartialRegenerator,
    SelectionRect,
    validate_editor_state_document,
)
from generator.export import TiledExporter, TiledImporter
from generator.map import MapGenerator
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.validation import Validator


def _tilemap():
    spec = RulePromptParser().parse(
        GenerateRequest(
            prompt="生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙，村民可以在道路上行走",
            seed=20260605,
        )
    )
    return MapGenerator().generate(spec)


def _editor_state(tilemap, selection=None, locked_regions=None):
    return EditorStateDocument(
        source_file="map_data.json",
        map=EditorMapDocument(
            width=tilemap.map.width,
            height=tilemap.map.height,
            tile_width=tilemap.map.tile_width,
            tile_height=tilemap.map.tile_height,
        ),
        layer_visibility={name: name != "collision" for name in tilemap.layers},
        selection=selection or SelectionRect(x=20, y=20, width=8, height=8),
        locked_regions=locked_regions or [],
    )


def test_editor_state_document_validates_against_tilemap():
    tilemap = _tilemap()
    state = _editor_state(tilemap)

    report = validate_editor_state_document(state, tilemap)

    assert report.passed
    assert report.metrics["has_selection"] is True


def test_partial_regeneration_changes_selection_and_preserves_validation():
    tilemap = _tilemap()
    state = _editor_state(tilemap, selection=SelectionRect(x=24, y=24, width=8, height=8))
    request = PartialRegenerationRequest(prompt="把这里改成一片树林", seed=99, editor_state=state)

    updated, report = PartialRegenerator().regenerate(tilemap, request)
    validation = Validator().validate(updated)

    report.validation_passed = validation.passed
    assert report.operation == "forest"
    assert report.changed_tiles > 0
    assert validation.passed, validation.model_dump()


def test_partial_regeneration_preserves_locked_cells():
    tilemap = _tilemap()
    locked = EditorLockedRegionDocument(id="locked_a", x=24, y=24, width=2, height=2, layers=None)
    state = _editor_state(tilemap, selection=SelectionRect(x=23, y=23, width=8, height=8), locked_regions=[locked])
    before = {name: layer[:] for name, layer in tilemap.layers.items()}

    updated, report = PartialRegenerator().regenerate(
        tilemap,
        PartialRegenerationRequest(prompt="把这里改成水池", seed=100, editor_state=state),
    )

    assert report.skipped_locked_tiles > 0
    width = tilemap.map.width
    for layer_name, layer in updated.layers.items():
        for y in range(24, 26):
            for x in range(24, 26):
                assert layer[y * width + x] == before[layer_name][y * width + x]


def test_tiled_importer_round_trips_exported_core_layers():
    tilemap = _tilemap()
    tiled = TiledExporter().to_dict(tilemap)

    imported = TiledImporter().from_dict(tiled)

    assert imported.map.width == tilemap.map.width
    assert imported.map.height == tilemap.map.height
    assert imported.layers == tilemap.layers
    assert len(imported.objects) == len(tilemap.objects)
    assert len(imported.events) == len(tilemap.events)
