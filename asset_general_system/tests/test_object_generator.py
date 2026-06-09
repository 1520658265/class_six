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
<<<<<<< HEAD
from generator.assets.sprite_cleanup import (
    clean_object_sprite_background,
    fit_object_sprite_to_runtime_canvas,
    validate_rpg_sprite_usability,
)
=======
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
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

<<<<<<< HEAD
        assert len(results) == 20
=======
        assert len(results) == 5
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
        assert all(r.success for r in results)

        # Check variety
        asset_ids = [r.asset_id for r in results if r.asset_id]
<<<<<<< HEAD
        assert len(set(asset_ids)) == 20  # All unique
=======
        assert len(set(asset_ids)) == 5  # All unique
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0

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


<<<<<<< HEAD
def test_object_sprite_cleanup_removes_fake_checker_background(tmp_path):
    from PIL import Image, ImageDraw

    sprite_path = tmp_path / "checker_object.png"
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(64):
        for x in range(64):
            gray = 82 if ((x // 4) + (y // 4)) % 2 else 138
            img.putpixel((x, y), (gray, gray, gray, 180))
    draw.rectangle((22, 18, 42, 46), fill=(190, 60, 45, 255))
    img.save(sprite_path)

    quality = clean_object_sprite_background(sprite_path)
    cleaned = Image.open(sprite_path).convert("RGBA")

    assert quality.passed
    assert cleaned.getpixel((0, 0))[3] == 0
    assert cleaned.getpixel((63, 63))[3] == 0
    assert cleaned.getpixel((32, 32))[3] == 255


def test_fit_object_sprite_to_runtime_canvas_scales_subject_to_footprint(tmp_path):
    from PIL import Image, ImageDraw

    sprite_path = tmp_path / "small_building.png"
    img = Image.new("RGBA", (1024, 768), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((360, 280, 660, 460), fill=(180, 70, 55, 255))
    img.save(sprite_path)

    repack = fit_object_sprite_to_runtime_canvas(
        sprite_path,
        footprint=(10, 6),
        tile_size=(32, 32),
        anchor="bottom_center",
        category="building",
    )

    assert repack.passed
    with Image.open(sprite_path).convert("RGBA") as repacked:
        assert repacked.size == (320, 192)
        bbox = repacked.getchannel("A").getbbox()
    assert bbox is not None
    assert bbox[2] - bbox[0] >= 280
    assert bbox[3] - bbox[1] >= 165
    assert bbox[3] >= 188


def test_thin_low_information_large_prop_fails_runtime_usability(tmp_path):
    from PIL import Image, ImageDraw

    sprite_path = tmp_path / "thin_bicycle.png"
    img = Image.new("RGBA", (96, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 24, 28, 42), outline=(24, 24, 22, 255), width=1)
    draw.ellipse((64, 24, 82, 42), outline=(24, 24, 22, 255), width=1)
    draw.line((19, 33, 42, 19, 73, 33, 19, 33, 42, 33, 52, 23), fill=(24, 24, 22, 255), width=1)
    draw.line((42, 19, 44, 13, 50, 13), fill=(24, 24, 22, 255), width=1)
    draw.line((73, 33, 80, 20, 86, 18), fill=(24, 24, 22, 255), width=1)
    img.save(sprite_path)

    usability = validate_rpg_sprite_usability(
        sprite_path,
        footprint=(2, 1),
        tile_size=(48, 48),
        category="large_prop",
    )

    assert not usability.passed
    assert any("sparse" in error or "readable" in error or "short" in error for error in usability.errors)


def test_object_generator_prompt_keeps_structured_asset_contract():
    generator = object.__new__(ObjectGenerator)
    request = ObjectGenerationRequest(
        object_type="dining_hall",
        description=(
            "TASK: Create one production-ready RPG map object sprite.\n"
            "Asset contract:\n"
            "- Name: dining hall\n"
            "- Runtime display size: 160x288 px"
        ),
        style=ImageStyle.PIXEL_ART,
        footprint=(5, 9),
        tile_size=(32, 32),
        source_canvas=(640, 1152),
        category="building",
        anchor="bottom_center",
    )

    prompt = generator._build_prompt(request)

    assert "Asset contract:" in prompt
    assert "Runtime display size: 160x288 px" in prompt
    assert "Building-specific requirements:" in prompt
    assert "\nAsset contract:\n" in prompt
    assert "No 8-bit micro-icon style" in prompt or "Do not use 8-bit micro-icon style" in prompt


=======
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
if __name__ == "__main__":
    test_object_generator_basic()
    test_generate_standard_objects()
    test_collision_inference()
    print("All object generator tests passed!")
