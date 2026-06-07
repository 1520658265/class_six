"""
Standalone test for ObjectPlacer without full imports.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_object_placer_standalone():
    """Test ObjectPlacer logic without full tilemap integration."""
    print("Testing ObjectPlacer standalone...")

    # Direct import to avoid pydantic dependency
    from generator.map.object_placer import ObjectPlacer

    # Test without asset library (no sprite references)
    placer = ObjectPlacer(asset_library=None)

    # Mock ObjectData for testing
    class MockObjectData:
        def __init__(self, id, type, x, y, properties=None):
            self.id = id
            self.type = type
            self.x = x
            self.y = y
            self.width = 1
            self.height = 1
            self.properties = properties or {}
            self.sprite_ref = None
            self.sprite_path = None

    # Temporarily replace the import
    import generator.models as models
    original_ObjectData = getattr(models, 'ObjectData', None)
    models.ObjectData = MockObjectData

    try:
        # Test create_object_with_sprite
        obj = placer.create_object_with_sprite("test_01", "tree", 10, 10)
        assert obj.id == "test_01"
        assert obj.type == "tree"
        assert obj.x == 10
        assert obj.y == 10
        assert obj.sprite_ref is None  # No library, so no sprite
        print("  [OK] create_object_with_sprite works")

        # Test get_missing_object_types
        class MockTilemap:
            def __init__(self):
                self.objects = []
                self.map = type('obj', (object,), {'width': 32, 'height': 32})()

        tilemap = MockTilemap()
        tilemap.objects.append(MockObjectData("obj1", "tree", 5, 5))
        tilemap.objects.append(MockObjectData("obj2", "rock", 10, 10))

        # Add one with sprite_ref
        obj_with_sprite = MockObjectData("obj3", "chest", 15, 15)
        obj_with_sprite.sprite_ref = "chest_1000"
        tilemap.objects.append(obj_with_sprite)

        missing = placer.get_missing_object_types(tilemap)
        assert "tree" in missing
        assert "rock" in missing
        assert "chest" not in missing
        print(f"  [OK] Missing types detected: {missing}")

        # Test report_object_coverage
        report = placer.report_object_coverage(tilemap)
        assert report["total_objects"] == 3
        assert report["with_sprite"] == 1
        assert report["without_sprite"] == 2
        assert abs(report["coverage_percent"] - 33.33) < 0.1
        print(f"  [OK] Coverage report: {report['coverage_percent']:.1f}%")

        print("\n[SUCCESS] ObjectPlacer standalone test passed!")
        return True

    finally:
        # Restore original
        if original_ObjectData:
            models.ObjectData = original_ObjectData


if __name__ == "__main__":
    try:
        test_object_placer_standalone()
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
