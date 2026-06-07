"""
Simple standalone test for Phase 4 modules without pytest.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.models.asset_metadata import (
    AnchorPoint,
    AssetKind,
    AssetMetadata,
    AssetSourceType,
)
from generator.assets.image_generation import (
    ImageGenerationRequest,
    ImageStyle,
    MockImageGenerator,
)
from generator.assets.object_generator import ObjectGenerator, ObjectGenerationRequest
from generator.assets.asset_library import AssetLibrary


def test_asset_metadata():
    """Test asset metadata."""
    print("Testing AssetMetadata...")

    metadata = AssetMetadata(
        asset_id="tree_oak_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["tree", "oak", "blocking"],
        tile_size=(32, 32),
        footprint=(1, 2),
        collision=[(0, 1)],
    )

    # Test serialization
    data = metadata.to_dict()
    assert data["asset_id"] == "tree_oak_01"
    assert data["footprint"] == [1, 2]

    # Test deserialization
    restored = AssetMetadata.from_dict(data)
    assert restored.asset_id == metadata.asset_id
    assert restored.footprint == metadata.footprint

    print("  [OK] AssetMetadata serialization works")


def test_mock_generator():
    """Test mock image generator."""
    print("Testing MockImageGenerator...")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        generator = MockImageGenerator(Path(tmpdir))

        request = ImageGenerationRequest(
            prompt="oak tree with green leaves",
            style=ImageStyle.PIXEL_ART,
            size=(32, 64),
            seed=1000,
        )

        response = generator.generate(request)
        assert response.success
        assert response.image_path is not None
        assert Path(response.image_path).exists()

        print("  [OK] MockImageGenerator works")


def test_object_generator():
    """Test object generator."""
    print("Testing ObjectGenerator...")

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")

        request = ObjectGenerationRequest(
            object_type="tree",
            description="oak tree with green leaves",
            footprint=(1, 2),
            tile_size=(32, 32),
            seed=1000,
        )

        result = obj_gen.generate(request)
        assert result.success
        assert result.asset_id is not None
        assert result.metadata is not None
        assert Path(result.sprite_path).exists()
        assert Path(result.metadata_path).exists()

        print(f"  [OK] Generated object: {result.asset_id}")


def test_asset_library():
    """Test asset library."""
    print("Testing AssetLibrary...")

    library = AssetLibrary()

    # Add test assets
    library.add_asset(AssetMetadata(
        asset_id="tree_oak_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["tree", "oak", "blocking"],
        tile_size=(32, 32),
        theme=["forest", "village"],
    ))

    library.add_asset(AssetMetadata(
        asset_id="rock_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["rock", "stone", "blocking"],
        tile_size=(32, 32),
        theme=["mountains"],
    ))

    # Test search
    results = library.search_by_tags(["tree"])
    assert len(results) == 1
    assert results[0].asset_id == "tree_oak_01"

    # Test synonym search
    results = library.search_by_tags(["boulder"], use_synonyms=True)
    assert len(results) == 1  # Should find rock via synonym

    # Test theme search
    results = library.search_by_theme(["forest"])
    assert len(results) == 1

    print("  [OK] AssetLibrary search works")


if __name__ == "__main__":
    print("\n=== Phase 4 Module Tests ===\n")

    try:
        test_asset_metadata()
        test_mock_generator()
        test_object_generator()
        test_asset_library()

        print("\n[SUCCESS] All Phase 4 tests passed!\n")

    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
