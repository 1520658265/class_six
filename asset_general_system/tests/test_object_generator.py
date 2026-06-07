"""
Test object generator.
"""

import tempfile
from pathlib import Path

from generator.assets.image_generation import ImageStyle, MockImageGenerator
from generator.assets.object_generator import (
    ObjectGenerationRequest,
    ObjectGenerator,
    generate_standard_objects,
)
from generator.models.asset_metadata import AssetKind


def test_object_generator_basic():
    """Test basic object generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "objects"
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock_images")
        generator = ObjectGenerator(mock_gen, output_dir)

        request = ObjectGenerationRequest(
            object_type="tree",
            description="oak tree with green leaves",
            style=ImageStyle.PIXEL_ART,
            footprint=(1, 2),
            tile_size=(32, 32),
            theme=["forest", "village"],
            seed=1000,
            tags=["tree", "oak", "nature"],
        )

        result = generator.generate(request)

        assert result.success
        assert result.asset_id is not None
        assert result.sprite_path is not None
        assert result.metadata_path is not None
        assert result.metadata is not None

        # Check metadata
        assert result.metadata.kind == AssetKind.TILE_OBJECT
        assert result.metadata.footprint == (1, 2)
        assert "tree" in result.metadata.tags
        assert "blocking" in result.metadata.tags  # Auto-added
        assert result.metadata.generated is not None
        assert result.metadata.generated.seed == 1000

        # Check files exist
        assert Path(result.sprite_path).exists()
        assert Path(result.metadata_path).exists()


def test_generate_standard_objects():
    """Test standard object set generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "objects"
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock_images")
        generator = ObjectGenerator(mock_gen, output_dir)

        results = generate_standard_objects(generator, seed_offset=2000)

        assert len(results) == 5
        assert all(r.success for r in results)

        # Check variety
        asset_ids = [r.asset_id for r in results if r.asset_id]
        assert len(set(asset_ids)) == 5  # All unique

        # Check specific objects
        tree_results = [r for r in results if r.metadata and "tree" in r.metadata.tags]
        assert len(tree_results) >= 2  # At least oak and pine

        chest_results = [r for r in results if r.metadata and "chest" in r.metadata.tags]
        assert len(chest_results) == 1


def test_collision_inference():
    """Test automatic collision inference."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "objects"
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock_images")
        generator = ObjectGenerator(mock_gen, output_dir)

        # Tall object (tree) - should block bottom row
        tall_request = ObjectGenerationRequest(
            object_type="tree",
            description="tall tree",
            footprint=(1, 2),
            tile_size=(32, 32),
            seed=3000,
        )
        tall_result = generator.generate(tall_request)
        assert tall_result.success
        assert tall_result.metadata is not None
        assert (0, 1) in tall_result.metadata.collision  # Bottom row

        # Small object (rock) - should block center
        small_request = ObjectGenerationRequest(
            object_type="rock",
            description="small rock",
            footprint=(1, 1),
            tile_size=(32, 32),
            seed=3001,
        )
        small_result = generator.generate(small_request)
        assert small_result.success
        assert small_result.metadata is not None
        assert len(small_result.metadata.collision) > 0


if __name__ == "__main__":
    test_object_generator_basic()
    test_generate_standard_objects()
    test_collision_inference()
    print("All object generator tests passed!")
