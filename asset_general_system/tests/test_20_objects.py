"""
Test expanded 20-object standard set.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.image_generation import ImageStyle, MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.assets.asset_library import AssetLibrary


def test_20_objects():
    """Test generation of 20 standard objects."""
    print("Testing 20-object standard set...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")

        results = generate_standard_objects(obj_gen, seed_offset=3000)

        assert len(results) == 20, f"Expected 20 objects, got {len(results)}"

        success_count = sum(1 for r in results if r.success)
        print(f"  Generated {success_count}/20 objects successfully")

        # Check categories
        categories = {
            "trees": ["tree_oak", "tree_pine", "tree_palm", "tree_willow", "tree_dead"],
            "rocks": ["rock_small", "rock_large", "crystal"],
            "containers": ["chest", "barrel", "crate"],
            "decorations": ["lamppost", "statue", "well", "fountain", "bench"],
            "markers": ["signpost", "torch"],
            "structures": ["stall", "gate"],
        }

        for category, expected in categories.items():
            found = [r.asset_id for r in results if r.success and any(e in r.asset_id for e in expected)]
            print(f"  {category.capitalize()}: {len(found)} objects")

        # Test AssetLibrary with all objects
        library = AssetLibrary(Path(tmpdir) / "objects")
        stats = library.get_stats()
        print(f"\nLibrary stats:")
        print(f"  Total assets: {stats['total_assets']}")
        print(f"  Unique tags: {stats['unique_tags']}")

        # Test category searches
        trees = library.search_by_tags(["tree"])
        print(f"  Trees found by tag: {len(trees)}")
        assert len(trees) == 5, f"Expected 5 trees, found {len(trees)}"

        rocks = library.search_by_tags(["rock", "stone", "boulder", "crystal"])
        print(f"  Rocks/stones found: {len(rocks)}")
        assert len(rocks) == 3, f"Expected 3 rocks, found {len(rocks)}"

        # Test theme search
        village_objects = library.search_by_theme(["village"])
        print(f"  Village-themed objects: {len(village_objects)}")

        dungeon_objects = library.search_by_theme(["dungeon"])
        print(f"  Dungeon-themed objects: {len(dungeon_objects)}")

        print("\n[SUCCESS] 20-object set test passed!")
        return True


if __name__ == "__main__":
    try:
        test_20_objects()
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
