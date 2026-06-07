"""
Test asset metadata models and serialization.
"""

import json
import tempfile
from pathlib import Path

from generator.models.asset_metadata import (
    AnchorPoint,
    AssetKind,
    AssetMetadata,
    AssetSourceType,
    GenerationMetadata,
    SourceMetadata,
    VisualBounds,
)


def test_asset_metadata_serialization():
    """Test metadata to_dict and from_dict round-trip."""
    metadata = AssetMetadata(
        asset_id="tree_oak_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["tree", "oak", "forest", "blocking"],
        tile_size=(32, 32),
        theme=["forest", "village"],
        footprint=(1, 2),
        collision=[(0, 1)],
        anchor=AnchorPoint.BOTTOM_CENTER,
        sprite_path="objects/tree_oak_01.png",
    )

    # Serialize
    data = metadata.to_dict()
    assert data["asset_id"] == "tree_oak_01"
    assert data["kind"] == "tile_object"
    assert data["footprint"] == [1, 2]
    assert data["collision"] == [[0, 1]]

    # Deserialize
    restored = AssetMetadata.from_dict(data)
    assert restored.asset_id == metadata.asset_id
    assert restored.kind == metadata.kind
    assert restored.footprint == metadata.footprint
    assert restored.collision == metadata.collision


def test_asset_metadata_with_generation_info():
    """Test metadata with generation information."""
    gen_info = GenerationMetadata(
        timestamp="2026-06-06T10:00:00",
        generator="MockGenerator-v1",
        prompt="oak tree with green leaves",
        seed=1234,
        model="mock",
    )

    source_info = SourceMetadata(
        type=AssetSourceType.GENERATED,
        attribution="AI-generated",
    )

    metadata = AssetMetadata(
        asset_id="tree_oak_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["tree", "oak"],
        tile_size=(32, 32),
        generated=gen_info,
        source=source_info,
    )

    data = metadata.to_dict()
    assert "generated" in data
    assert data["generated"]["seed"] == 1234
    assert "source" in data
    assert data["source"]["type"] == "generated"

    restored = AssetMetadata.from_dict(data)
    assert restored.generated is not None
    assert restored.generated.seed == 1234
    assert restored.source is not None
    assert restored.source.type == AssetSourceType.GENERATED


def test_asset_metadata_minimal():
    """Test metadata with minimal required fields."""
    metadata = AssetMetadata(
        asset_id="simple_tile",
        kind=AssetKind.TILE,
        tags=["terrain", "grass"],
        tile_size=(32, 32),
    )

    data = metadata.to_dict()
    assert data["asset_id"] == "simple_tile"
    assert "footprint" not in data  # Optional, not included
    assert "collision" not in data  # Empty list, not included

    restored = AssetMetadata.from_dict(data)
    assert restored.footprint is None
    assert restored.collision == []


def test_visual_bounds():
    """Test visual bounds calculation."""
    bounds = VisualBounds(x=5, y=10, width=22, height=48)

    metadata = AssetMetadata(
        asset_id="test",
        kind=AssetKind.TILE_OBJECT,
        tags=["test"],
        tile_size=(32, 32),
        visual_bounds=bounds,
    )

    data = metadata.to_dict()
    assert "visual_bounds" in data
    assert data["visual_bounds"]["x"] == 5
    assert data["visual_bounds"]["width"] == 22

    restored = AssetMetadata.from_dict(data)
    assert restored.visual_bounds is not None
    assert restored.visual_bounds.x == 5
    assert restored.visual_bounds.width == 22


if __name__ == "__main__":
    test_asset_metadata_serialization()
    test_asset_metadata_with_generation_info()
    test_asset_metadata_minimal()
    test_visual_bounds()
    print("All asset metadata tests passed!")
