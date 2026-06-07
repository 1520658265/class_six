"""
Test style consistency checker.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.asset_library import AssetLibrary
from generator.assets.image_generation import MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.assets.style_checker import StyleConsistencyChecker


def test_theme_consistency():
    """测试主题一致性检查。"""
    print("测试主题一致性检查...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 生成标准对象集
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")
        results = generate_standard_objects(obj_gen, seed_offset=9000)

        library = AssetLibrary(Path(tmpdir) / "objects")
        checker = StyleConsistencyChecker(library)

        # 检查森林主题
        forest_report = checker.check_theme_consistency("forest")
        print(f"  森林主题:")
        print(f"    素材数: {forest_report['asset_count']}")
        print(f"    一致性分数: {forest_report['consistency_score']:.2f}")
        print(f"    状态: {forest_report['status']}")

        assert forest_report["asset_count"] > 0, "森林主题应有素材"
        assert forest_report["consistency_score"] >= 0.6, "一致性分数应合格"

        # 检查村庄主题
        village_report = checker.check_theme_consistency("village")
        print(f"  村庄主题:")
        print(f"    素材数: {village_report['asset_count']}")
        print(f"    一致性分数: {village_report['consistency_score']:.2f}")
        print(f"    状态: {village_report['status']}")

        print("  [OK] 主题一致性检查正常")


def test_all_themes():
    """测试所有主题一致性。"""
    print("\n测试所有主题一致性...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")
        results = generate_standard_objects(obj_gen, seed_offset=9000)

        library = AssetLibrary(Path(tmpdir) / "objects")
        checker = StyleConsistencyChecker(library)

        # 检查所有主题
        full_report = checker.check_all_themes()

        print(f"  总主题数: {full_report['total_themes']}")
        print(f"  平均一致性: {full_report['average_consistency']:.2f}")
        print(f"  总体问题: {len(full_report['overall_issues'])}")

        if full_report['overall_issues']:
            for issue in full_report['overall_issues']:
                print(f"    - {issue}")

        print(f"\n  建议: {full_report['recommendation']}")

        assert full_report["total_themes"] > 0, "应检测到主题"
        assert full_report["average_consistency"] >= 0.5, "平均一致性应合理"

        print("  [OK] 所有主题检查完成")


def test_image_style_analysis():
    """测试图像风格分析。"""
    print("\n测试图像风格分析...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 生成一个测试对象
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        obj_gen = ObjectGenerator(mock_gen, Path(tmpdir) / "objects")

        from generator.assets.object_generator import ObjectGenerationRequest
        from generator.assets.image_generation import ImageStyle

        request = ObjectGenerationRequest(
            object_type="test_tree",
            description="test tree for style analysis",
            style=ImageStyle.PIXEL_ART,
            footprint=(1, 2),
            tile_size=(32, 32),
            seed=10000,
        )

        result = obj_gen.generate(request)
        assert result.success, "应成功生成测试对象"

        # 分析风格
        library = AssetLibrary(Path(tmpdir) / "objects")
        checker = StyleConsistencyChecker(library)

        analysis = checker.analyze_image_style(result.sprite_path)

        if "error" in analysis:
            print(f"  跳过图像分析: {analysis['error']}")
        else:
            print(f"  图像尺寸: {analysis['size']}")
            print(f"  风格类型: {analysis['style_type']}")
            print(f"  主色调数: {len(analysis.get('dominant_colors', []))}")

            assert analysis["style_type"] in ["pixel_art", "low_res", "high_res"]

        print("  [OK] 图像风格分析完成")


if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("风格一致性检查测试")
        print("="*60)

        test_theme_consistency()
        test_all_themes()
        test_image_style_analysis()

        print("\n" + "="*60)
        print("[全部通过] 风格一致性检查测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
