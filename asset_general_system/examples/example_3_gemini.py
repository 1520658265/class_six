#!/usr/bin/env python
"""
实战示例 3：使用真实 Gemini 生成（需要 API key）

这个示例演示如何使用 Gemini 生成真实的像素画素材。
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    print("="*60)
    print("实战示例 3：使用 Gemini 真实 AI 生成")
    print("="*60)
    print()

    # 检查 API key
    has_config = (Path.home().parent.parent / "AI" / "class_six" / "tools" / "ai" / "config.local.json").exists()
    has_env = os.getenv("GEMINI_IMAGE_API_KEY") is not None

    if not has_config and not has_env:
        print("❌ 未配置 Gemini API key")
        print()
        print("配置方法（二选一）：")
        print()
        print("方式 1：配置文件（推荐）")
        print("  编辑: D:\\AI\\class_six\\tools\\ai\\config.local.json")
        print("  添加:")
        print('    {')
        print('      "services": {')
        print('        "gemini_image": {')
        print('          "api_host": "bobdong.cn",')
        print('          "api_key": "你的-API-key",')
        print('          "model": "gemini-3.1-flash-image-preview"')
        print('        }')
        print('      }')
        print('    }')
        print()
        print("方式 2：环境变量")
        print("  set GEMINI_IMAGE_API_KEY=你的-API-key")
        print()
        print("获取免费 API key:")
        print("  https://aistudio.google.com/app/apikey")
        print()
        sys.exit(1)

    print("✓ 检测到 Gemini 配置")
    print()

    # 导入 Gemini 生成器
    from generator.assets.gemini_generator import GeminiImageGenerator
    from generator.assets.object_generator import ObjectGenerator, ObjectGenerationRequest

    output_dir = Path("output/example_gemini")

    print("创建 Gemini 生成器...")
    gemini_gen = GeminiImageGenerator(output_dir / "gemini")
    obj_gen = ObjectGenerator(gemini_gen, output_dir / "objects")

    print("✓ 初始化完成")
    print()

    # 生成一个魔法树
    print("生成魔法树（真实 AI）...")
    print("  这可能需要 5-10 秒...")
    print()

    request = ObjectGenerationRequest(
        object_type="magic_tree",
        description="a glowing magical tree with blue sparkling leaves and mystical particles around it, pixel art style",
        footprint=(2, 3),
        tags=["tree", "magic", "fantasy"],
        seed=5001,
    )

    result = obj_gen.generate(request)

    if result.success:
        print("✓ 生成成功！")
        print(f"  asset_id: {result.asset_id}")
        print(f"  图像: {result.sprite_path}")
        print(f"  metadata: {result.metadata_path}")
        print()
        print(f"  footprint: {result.metadata.footprint}")
        print(f"  collision: {result.metadata.collision}")
        print(f"  anchor: {result.metadata.anchor.value}")
        print(f"  tags: {', '.join(result.metadata.tags)}")
        print()
        print("查看生成的图像:")
        print(f"  {Path(result.sprite_path).absolute()}")
    else:
        print(f"✗ 生成失败: {result.error}")
        print()
        print("可能的原因：")
        print("  1. API key 无效")
        print("  2. 网络连接问题")
        print("  3. API 配额用完")

    print()
    print("="*60)
    print("提示：")
    print("  - Gemini 生成速度: 约 5-10 秒/张")
    print("  - 免费配额: 每天有限制")
    print("  - 国内访问: 使用 bobdong.cn 代理")
    print("  - 批量生成: 建议使用付费账号")


if __name__ == "__main__":
    main()
