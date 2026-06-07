"""
Phase 5 测试：角色 sprite sheet 生成。
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.image_generation import ImageStyle, MockImageGenerator
from generator.characters import (
    CharacterGenerationRequest,
    CharacterGenerator,
    generate_standard_characters,
)
from generator.models.sprite_sheet import (
    AnimationClip,
    CharacterAnchor,
    Direction,
    HitBox,
    SpriteSheetMetadata,
)


def test_sprite_sheet_metadata_serialization():
    """测试 SpriteSheetMetadata 序列化。"""
    print("测试 SpriteSheetMetadata 序列化...")

    metadata = SpriteSheetMetadata(
        asset_id="villager_01",
        image="villager_01.png",
        frame_size=(32, 48),
        directions=[Direction.DOWN, Direction.LEFT, Direction.RIGHT, Direction.UP],
        animations={
            "walk_down": AnimationClip(row=0, frames=4, fps=8, loop=True, direction=Direction.DOWN),
            "idle_down": AnimationClip(row=4, frames=4, fps=4, loop=True, direction=Direction.DOWN),
        },
        anchor=CharacterAnchor.FEET_CENTER,
        hitbox=HitBox(x=8, y=28, width=16, height=16),
        tags=["villager", "merchant"],
    )

    data = metadata.to_dict()
    assert data["asset_id"] == "villager_01"
    assert data["frame_size"] == [32, 48]
    assert "walk_down" in data["animations"]

    restored = SpriteSheetMetadata.from_dict(data)
    assert restored.asset_id == metadata.asset_id
    assert restored.frame_size == metadata.frame_size
    assert restored.hitbox.x == 8

    print("  [OK] SpriteSheetMetadata 序列化通过")


def test_character_generator_basic():
    """测试基础角色生成。"""
    print("\n测试基础角色生成...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        char_gen = CharacterGenerator(mock_gen, Path(tmpdir) / "characters")

        request = CharacterGenerationRequest(
            character_type="merchant",
            description="merchant in green robes",
            seed=1000,
            tags=["merchant", "civilian"],
        )

        result = char_gen.generate(request)
        assert result.success, f"生成失败: {result.error}"
        assert result.asset_id is not None
        assert Path(result.sheet_path).exists()
        assert Path(result.metadata_path).exists()

        # 验证 metadata
        metadata = result.metadata
        assert metadata.asset_id == result.asset_id
        assert len(metadata.directions) == 4

        # 应有 8 个动画（idle/walk x 4 方向）
        assert len(metadata.animations) == 8
        assert "walk_down" in metadata.animations
        assert "idle_down" in metadata.animations
        assert "walk_left" in metadata.animations

        # 验证 hitbox 默认值
        assert metadata.hitbox is not None

        print(f"  [OK] 生成角色: {result.asset_id}")
        print(f"       动画数: {len(metadata.animations)}")
        print(f"       图像尺寸: {Path(result.sheet_path).name}")


def test_generate_10_characters():
    """测试 10 个标准角色生成。"""
    print("\n测试 10 个标准角色...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        char_gen = CharacterGenerator(mock_gen, Path(tmpdir) / "characters")

        results = generate_standard_characters(char_gen, seed_offset=2000)

        assert len(results) == 10
        success_count = sum(1 for r in results if r.success)
        print(f"  生成成功: {success_count}/10")

        # 列出所有角色
        for r in results:
            if r.success:
                print(f"    - {r.asset_id}: {len(r.metadata.animations)} 动画")

        assert success_count == 10, "应全部成功"


def test_animation_inference():
    """测试 fps 和 loop 自动推断。"""
    print("\n测试动画属性推断...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        char_gen = CharacterGenerator(mock_gen, Path(tmpdir) / "characters")

        request = CharacterGenerationRequest(
            character_type="hero",
            description="hero",
            animations=["idle", "walk"],
            seed=3000,
        )

        result = char_gen.generate(request)
        assert result.success

        # idle 应是 4 fps + loop
        idle_clip = result.metadata.animations["idle_down"]
        assert idle_clip.fps == 4
        assert idle_clip.loop is True

        # walk 应是 8 fps + loop
        walk_clip = result.metadata.animations["walk_down"]
        assert walk_clip.fps == 8
        assert walk_clip.loop is True

        print(f"  [OK] idle: {idle_clip.fps}fps, loop={idle_clip.loop}")
        print(f"  [OK] walk: {walk_clip.fps}fps, loop={walk_clip.loop}")


def test_sprite_sheet_dimensions():
    """测试 sprite sheet 尺寸正确。"""
    print("\n测试 sprite sheet 尺寸...")

    with tempfile.TemporaryDirectory() as tmpdir:
        mock_gen = MockImageGenerator(Path(tmpdir) / "mock")
        char_gen = CharacterGenerator(mock_gen, Path(tmpdir) / "characters")

        request = CharacterGenerationRequest(
            character_type="test",
            description="test character",
            frame_size=(32, 48),
            frames_per_animation=4,
            seed=4000,
        )

        result = char_gen.generate(request)
        assert result.success

        from PIL import Image
        sheet = Image.open(result.sheet_path)
        sheet_size = sheet.size
        sheet.close()  # 关闭文件句柄

        # 8 行（4 方向 x 2 动作），4 列（每动作 4 帧）
        expected_width = 32 * 4
        expected_height = 48 * 8
        assert sheet_size == (expected_width, expected_height), \
            f"尺寸应为 {expected_width}x{expected_height}, 实际 {sheet_size}"

        print(f"  [OK] sprite sheet 尺寸: {sheet_size}")


if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("Phase 5: 角色 Sprite Sheet 生成测试")
        print("="*60)

        test_sprite_sheet_metadata_serialization()
        test_character_generator_basic()
        test_generate_10_characters()
        test_animation_inference()
        test_sprite_sheet_dimensions()

        print("\n" + "="*60)
        print("[全部通过] Phase 5 测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n[失败] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
