"""
Test missing asset auto-generation and backfill.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.asset_library import AssetLibrary
from generator.assets.image_generation import MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.map.missing_asset_handler import MissingAssetHandler
from generator.models import MapInfo, ObjectData, TilemapData, TilesetInfo


def test_missing_asset_detection():
    """测试缺失素材检测。"""
    print("测试缺失素材检测...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建库和生成器
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")

        # 只生成部分对象
        results = generate_standard_objects(obj_gen, seed_offset=6000)
        library = AssetLibrary(Path(tmpdir) / "objects")

        # 创建 tilemap，包含库中有的和没有的对象
        tilemap = TilemapData(
            map=MapInfo(width=32, height=32),
            tileset=TilesetInfo(),
            layers={
                "terrain": [1] * 1024,
                "decoration": [0] * 1024,
                "collision": [0] * 1024,
            },
        )

        # 添加对象：一些在库中，一些不在
        tilemap.objects.append(ObjectData(id="tree_01", type="tree_oak", x=5, y=5))  # 在库中
        tilemap.objects.append(ObjectData(id="magic_01", type="magic_circle", x=10, y=10))  # 不在库中
        tilemap.objects.append(ObjectData(id="crystal_tower_01", type="crystal_tower", x=15, y=15))  # 不在库中

        # 创建处理器
        handler = MissingAssetHandler(library, obj_gen)

        # 检测缺失
        missing = handler.detect_missing_assets(tilemap)
        print(f"  检测到 {len(missing)} 个缺失类型: {missing}")

        assert "magic_circle" in missing, "应检测到 magic_circle 缺失"
        assert "crystal_tower" in missing, "应检测到 crystal_tower 缺失"
        assert "tree_oak" not in missing, "tree_oak 不应在缺失列表中（有同义词匹配）"

        print("  [OK] 缺失检测正确")
        return handler, tilemap


def test_auto_generate_single_asset():
    """测试单个素材自动生成。"""
    print("\n测试单个素材自动生成...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")
        library = AssetLibrary(Path(tmpdir) / "objects")

        handler = MissingAssetHandler(library, obj_gen)

        # 生成一个新素材
        asset_id = handler.generate_missing_asset("magic_circle", seed=7000)

        assert asset_id is not None, "应成功生成素材"
        print(f"  生成素材: {asset_id}")

        # 验证已加入库
        asset = library.get_asset(asset_id)
        assert asset is not None, "素材应已加入库"
        assert "magic_circle" in asset.tags, "素材应有正确的标签"

        print("  [OK] 自动生成成功")


def test_auto_generate_and_backfill():
    """测试自动生成和回填完整流程。"""
    print("\n测试自动生成和回填...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")

        # 生成标准对象集
        results = generate_standard_objects(obj_gen, seed_offset=6000)
        library = AssetLibrary(Path(tmpdir) / "objects")
        print(f"  初始库: {len(library.assets)} 个素材")

        # 创建 tilemap，包含未知对象
        tilemap = TilemapData(
            map=MapInfo(width=32, height=32),
            tileset=TilesetInfo(),
            layers={
                "terrain": [1] * 1024,
                "decoration": [0] * 1024,
                "collision": [0] * 1024,
            },
        )

        tilemap.objects.append(ObjectData(id="obj1", type="tree_oak", x=5, y=5))
        tilemap.objects.append(ObjectData(id="obj2", type="magic_circle", x=10, y=10))
        tilemap.objects.append(ObjectData(id="obj3", type="crystal_tower", x=15, y=15))
        tilemap.objects.append(ObjectData(id="obj4", type="ancient_altar", x=20, y=20))

        # 创建处理器并自动生成
        handler = MissingAssetHandler(library, obj_gen)
        report = handler.auto_generate_and_backfill(tilemap, seed_offset=8000)

        print(f"  生成报告:")
        print(f"    缺失总数: {report['total_missing']}")
        print(f"    成功生成: {report['generated']}")
        print(f"    生成失败: {report['failed']}")

        assert report['total_missing'] == 3, "应检测到 3 个缺失类型"
        assert report['generated'] == 3, "应成功生成 3 个素材"
        assert report['failed'] == 0, "不应有生成失败"

        # 验证回填
        for obj in tilemap.objects:
            assert obj.sprite_ref is not None, f"对象 {obj.id} 应有 sprite_ref"
            print(f"    {obj.id} ({obj.type}): {obj.sprite_ref}")

        # 验证库增长
        stats = handler.get_generation_stats()
        print(f"  最终库: {stats['total_assets']} 个素材")
        assert stats['total_assets'] == 23, "库应有 23 个素材（20 + 3）"

        print("  [OK] 自动生成和回填成功")


def test_object_property_inference():
    """测试对象属性推断。"""
    print("\n测试对象属性推断...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")
        library = AssetLibrary()

        handler = MissingAssetHandler(library, obj_gen)

        # 测试不同类型的推断
        test_cases = [
            ("oak_tree", (1, 2), ["forest", "village"]),
            ("small_rock", (1, 1), ["mountains", "desert"]),
            ("wooden_chest", (1, 1), ["dungeon", "village"]),
            ("iron_lamppost", (1, 2), ["village", "plaza"]),
            ("magic_tower", (2, 2), ["village", "ruins"]),
        ]

        for obj_type, expected_footprint, expected_themes in test_cases:
            desc, theme, footprint = handler._infer_object_properties(obj_type)

            assert footprint == expected_footprint, f"{obj_type} footprint 应为 {expected_footprint}"
            assert any(t in theme for t in expected_themes), f"{obj_type} 应包含主题 {expected_themes}"
            print(f"  {obj_type}: footprint={footprint}, theme={theme}")

        print("  [OK] 属性推断正确")


if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("缺失素材自动生成测试")
        print("="*60)

        test_missing_asset_detection()
        test_auto_generate_single_asset()
        test_auto_generate_and_backfill()
        test_object_property_inference()

        print("\n" + "="*60)
        print("[全部通过] 缺失素材自动生成测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
