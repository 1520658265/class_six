"""
Phase 6 测试：VFX 生成。
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.image_generation import MockImageGenerator
from generator.models.vfx import (
    BlendMode,
    VFXAnchor,
    VFXCategory,
    VFXMetadata,
)
from generator.vfx import (
    VFXGenerationRequest,
    VFXGenerator,
    generate_standard_vfx,
)


def test_vfx_metadata_serialization():
    """测试 VFXMetadata 序列化。"""
    print("测试 VFXMetadata 序列化...")

    metadata = VFXMetadata(
        asset_id="fireball_01",
        image="fireball_01.png",
        frame_size=(64, 64),
        frames=8,
        fps=12,
        loop=False,
        blend=BlendMode.ADDITIVE,
        anchor=VFXAnchor.CENTER,
        category=VFXCategory.COMBAT,
        tags=["fireball", "fire"],
    )

    data = metadata.to_dict()
    assert data["asset_id"] == "fireball_01"
    assert data["blend"] == "additive"

    restored = VFXMetadata.from_dict(data)
    assert restored.frames == 8
    assert restored.blend == BlendMode.ADDITIVE

    print("  [OK] VFXMetadata 序列化通过")


def test_vfx_generator_basic():
    """测试基础 VFX 生成。"""
    print("\n测试基础 VFX 生成...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        vfx_gen = VFXGenerator(mock_gen, Path(tmpdir) / "vfx")

        request = VFXGenerationRequest(
            vfx_type="fireball",
            description="orange fireball",
            frame_size=(64, 64),
            frames=8,
            fps=12,
            loop=False,
            blend=BlendMode.ADDITIVE,
            seed=1000,
        )

        result = vfx_gen.generate(request)
        assert result.success, f"生成失败: {result.error}"
        assert Path(result.sheet_path).exists()
        assert Path(result.metadata_path).exists()

        # 验证 metadata
        assert result.metadata.frames == 8
        assert result.metadata.fps == 12
        assert result.metadata.blend == BlendMode.ADDITIVE
        assert not result.metadata.loop

        # 验证 sprite sheet 尺寸（一行）
        from PIL import Image
        sheet = Image.open(result.sheet_path)
        sheet_size = sheet.size
        sheet.close()
        assert sheet_size == (64 * 8, 64), f"应为 (512, 64), 实际 {sheet_size}"

        print(f"  [OK] 生成 VFX: {result.asset_id}")
        print(f"       帧数: {result.metadata.frames}, fps: {result.metadata.fps}")
        print(f"       sheet 尺寸: {sheet_size}")


def test_generate_10_vfx():
    """测试 10 种标准 VFX 生成。"""
    print("\n测试 10 种标准 VFX...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        vfx_gen = VFXGenerator(mock_gen, Path(tmpdir) / "vfx")

        results = generate_standard_vfx(vfx_gen, seed_offset=2000)

        assert len(results) == 10
        success_count = sum(1 for r in results if r.success)
        print(f"  生成成功: {success_count}/10")

        # 按类别统计
        categories = {}
        for r in results:
            if r.success:
                cat = r.metadata.category.value
                categories[cat] = categories.get(cat, 0) + 1

        print(f"  按类别:")
        for cat, count in categories.items():
            print(f"    {cat}: {count}")

        # 验证：4 战斗 + 3 魔法 + 3 环境
        assert categories.get("combat", 0) == 4
        assert categories.get("magic", 0) == 3
        assert categories.get("environment", 0) == 3

        # 验证特定特效属性
        loop_count = sum(1 for r in results if r.success and r.metadata.loop)
        non_loop_count = sum(1 for r in results if r.success and not r.metadata.loop)
        print(f"  循环特效: {loop_count}, 一次性特效: {non_loop_count}")

        assert success_count == 10


def test_vfx_blend_modes():
    """测试不同 blend mode。"""
    print("\n测试 blend mode...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        vfx_gen = VFXGenerator(mock_gen, Path(tmpdir) / "vfx")

        for blend in [BlendMode.ADDITIVE, BlendMode.NORMAL, BlendMode.MULTIPLY]:
            request = VFXGenerationRequest(
                vfx_type=f"test_{blend.value}",
                description=f"test effect with {blend.value} blend",
                frames=4,
                blend=blend,
                seed=3000 + hash(blend.value) % 1000,
            )

            result = vfx_gen.generate(request)
            assert result.success
            assert result.metadata.blend == blend
            print(f"  [OK] blend={blend.value}: {result.asset_id}")


if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("Phase 6: VFX 生成测试")
        print("="*60)

        test_vfx_metadata_serialization()
        test_vfx_generator_basic()
        test_generate_10_vfx()
        test_vfx_blend_modes()

        print("\n" + "="*60)
        print("[全部通过] Phase 6 测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n[失败] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
