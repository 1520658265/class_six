"""
测试 Gemini Imagen 集成。
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.gemini_generator import GeminiImageGenerator
from generator.assets.image_generation import (
    ImageGenerationRequest,
    ImageStyle,
    TransparencyMode,
)


def test_gemini_basic():
    """测试基础 Gemini 生成。"""
    print("测试 Gemini Imagen 基础生成...")

    # 检查 API key
    if not os.getenv("GEMINI_API_KEY"):
        print("  [跳过] GEMINI_API_KEY 环境变量未设置")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        generator = GeminiImageGenerator(Path(tmpdir))

        request = ImageGenerationRequest(
            prompt="a small oak tree with green leaves",
            style=ImageStyle.PIXEL_ART,
            size=(64, 64),
            transparency=TransparencyMode.REQUIRED,
            seed=1000,
        )

        response = generator.generate(request)

        if not response.success:
            print(f"  [失败] {response.error}")
            return

        assert Path(response.image_path).exists()
        print(f"  [OK] 生成成功: {Path(response.image_path).name}")
        print(f"       模型: {response.model}")

        # 验证图像
        from PIL import Image
        img = Image.open(response.image_path)
        print(f"       尺寸: {img.size}, 模式: {img.mode}")
        assert img.mode == "RGBA", "应为 RGBA 模式"
        assert img.size == (64, 64), "应为 64x64"


def test_gemini_character():
    """测试角色生成。"""
    print("\n测试 Gemini 角色生成...")

    if not os.getenv("GEMINI_API_KEY"):
        print("  [跳过] GEMINI_API_KEY 未设置")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        generator = GeminiImageGenerator(Path(tmpdir))

        request = ImageGenerationRequest(
            prompt="village merchant character, pixel art style, front view, standing pose, transparent background, RPG game sprite",
            style=ImageStyle.PIXEL_ART,
            size=(32, 48),
            transparency=TransparencyMode.REQUIRED,
            seed=2000,
        )

        response = generator.generate(request)

        if not response.success:
            print(f"  [失败] {response.error}")
            return

        print(f"  [OK] 角色生成: {Path(response.image_path).name}")


def test_gemini_vfx():
    """测试 VFX 生成。"""
    print("\n测试 Gemini VFX 生成...")

    if not os.getenv("GEMINI_API_KEY"):
        print("  [跳过] GEMINI_API_KEY 未设置")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        generator = GeminiImageGenerator(Path(tmpdir))

        request = ImageGenerationRequest(
            prompt="fireball sprite, orange flames, pixel art, transparent background, VFX animation frame, glowing",
            style=ImageStyle.PIXEL_ART,
            size=(64, 64),
            transparency=TransparencyMode.REQUIRED,
            seed=3000,
        )

        response = generator.generate(request)

        if not response.success:
            print(f"  [失败] {response.error}")
            return

        print(f"  [OK] VFX 生成: {Path(response.image_path).name}")


def test_gemini_prompt_preserves_asset_contract_and_negative_prompt():
    generator = object.__new__(GeminiImageGenerator)
    request = ImageGenerationRequest(
        prompt=(
            "TASK: Create one production-ready RPG map object sprite.\n"
            "Asset contract:\n"
            "- Name: concrete ping pong table\n"
            "- Runtime display size: 96x48 px"
        ),
        style=ImageStyle.PIXEL_ART,
        size=(512, 384),
        transparency=TransparencyMode.REQUIRED,
        tile_aligned=True,
        tile_size=(48, 48),
        negative_prompt="background, floor, fake transparency, thin hairline details",
    )

    prompt = generator._build_prompt(request)

    assert "Asset contract:" in prompt
    assert "Runtime display size: 96x48 px" in prompt
    assert "Strictly avoid: background, floor, fake transparency, thin hairline details" in prompt
    assert "8-bit retro" not in prompt
    assert "seamless edges" not in prompt


if __name__ == "__main__":
    print("="*60)
    print("Gemini Imagen 集成测试")
    print("="*60)
    print()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[WARNING] GEMINI_API_KEY 环境变量未设置")
        print()
        print("设置方法：")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print()
        print("获取 API key：")
        print("  https://aistudio.google.com/app/apikey")
        print()
        print("测试将使用 Mock 模式运行...")
        print()

    try:
        test_gemini_basic()
        test_gemini_character()
        test_gemini_vfx()

        print()
        print("="*60)
        if api_key:
            print("[完成] Gemini 集成测试完成")
        else:
            print("[跳过] 需要 GEMINI_API_KEY 才能运行真实测试")
        print("="*60)

    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
