"""
Test object placement integration.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.asset_library import AssetLibrary
from generator.assets.image_generation import ImageStyle, MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.map.object_placer import ObjectPlacer
from generator.models import MapInfo, ObjectData, TilemapData, TilesetInfo


def test_object_placer():
    """Test object placer with asset library."""
    print("Testing ObjectPlacer integration...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Generate standard objects
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")
        results = generate_standard_objects(obj_gen, seed_offset=4000)

        success_count = sum(1 for r in results if r.success)
        print(f"  Generated {success_count} objects")

        # Load into library
        library = AssetLibrary(Path(tmpdir) / "objects")
        print(f"  Library loaded {len(library.assets)} assets")

        # Create test tilemap
        tilemap = TilemapData(
            map=MapInfo(width=32, height=32),
            tileset=TilesetInfo(),
            layers={
                "terrain": [1] * 1024,
                "decoration": [0] * 1024,
                "collision": [0] * 1024,
            },
        )

        # Create placer with library
        placer = ObjectPlacer(library)

        # Place some objects
        obj1 = placer.create_object_with_sprite("tree_01", "tree_oak", 10, 10)
        assert obj1.sprite_ref is not None, "Tree should have sprite reference"
        assert obj1.sprite_path is not None, "Tree should have sprite path"
        print(f"  Created tree: {obj1.sprite_ref}")

        obj2 = placer.create_object_with_sprite("chest_01", "chest", 15, 15)
        assert obj2.sprite_ref is not None, "Chest should have sprite reference"
        print(f"  Created chest: {obj2.sprite_ref}")

        # Place multiple decorations
        positions = [(5, 5), (7, 5), (9, 5)]
        rocks = placer.place_decoration_objects(tilemap, "rock_small", positions)
        assert len(rocks) == 3
        assert all(r.sprite_ref for r in rocks), "All rocks should have sprites"
        print(f"  Placed {len(rocks)} rocks with sprites")

        # Test coverage report
        report = placer.report_object_coverage(tilemap)
        print(f"\nCoverage report:")
        print(f"  Total objects: {report['total_objects']}")
        print(f"  With sprite: {report['with_sprite']}")
        print(f"  Coverage: {report['coverage_percent']:.1f}%")

        assert report["coverage_percent"] == 100.0, "Should have 100% coverage"

        # Test missing detection
        tilemap.objects.append(ObjectData(
            id="unknown_01",
            type="unknown_object",
            x=20,
            y=20,
        ))

        missing = placer.get_missing_object_types(tilemap)
        assert "unknown_object" in missing, "Should detect missing object type"
        print(f"  Missing types: {missing}")

        print("\n[SUCCESS] ObjectPlacer integration test passed!")
        return True


if __name__ == "__main__":
    try:
        test_object_placer()
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
