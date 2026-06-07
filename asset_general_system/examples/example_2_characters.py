#!/usr/bin/env python
"""
实战示例 2：只生成角色 sprite sheets

这个示例演示如何单独生成角色素材。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.image_generation import MockImageGenerator
from generator.characters import CharacterGenerator, CharacterGenerationRequest


def main():
    print("="*60)
    print("实战示例 2：生成角色 Sprite Sheets")
    print("="*60)
    print()

    output_dir = Path("output/example_characters")

    # 创建生成器
    image_gen = MockImageGenerator(output_dir / "mock")
    char_gen = CharacterGenerator(image_gen, output_dir / "characters")

    # 定义要生成的角色
    characters = [
        {
            "type": "warrior",
            "desc": "armored warrior with sword and shield",
            "tags": ["warrior", "melee", "hero"],
        },
        {
            "type": "mage",
            "desc": "wizard in blue robe with magic staff",
            "tags": ["mage", "magic", "ranged"],
        },
        {
            "type": "archer",
            "desc": "archer with green cloak and bow",
            "tags": ["archer", "ranged", "agile"],
        },
    ]

    print(f"生成 {len(characters)} 个角色...")
    print()

    for i, char in enumerate(characters, start=1):
        print(f"[{i}/{len(characters)}] 生成 {char['type']}...")

        request = CharacterGenerationRequest(
            character_type=char["type"],
            description=char["desc"],
            frame_size=(32, 48),
            directions=["down", "left", "right", "up"],
            animations=["idle", "walk"],
            frames_per_animation=4,
            seed=2000 + i,
            tags=char["tags"],
        )

        result = char_gen.generate(request)

        if result.success:
            print(f"  ✓ 成功: {result.asset_id}")
            print(f"    sprite sheet: {Path(result.sheet_path).name}")
            print(f"    metadata: {Path(result.metadata_path).name}")
            print(f"    动画数: {len(result.metadata.animations)}")

            # 显示动画列表
            print(f"    动画列表:")
            for anim_name, anim_clip in list(result.metadata.animations.items())[:4]:
                print(f"      - {anim_name}: {anim_clip.frames}帧 @ {anim_clip.fps}fps (loop={anim_clip.loop})")
        else:
            print(f"  ✗ 失败: {result.error}")

        print()

    print("="*60)
    print("✓ 完成！")
    print("="*60)
    print()
    print(f"输出目录: {output_dir.absolute()}")
    print()
    print("生成的文件：")
    print("  - characters/*.png (sprite sheets)")
    print("  - characters/*.json (metadata)")
    print()
    print("如何使用这些 sprite sheets：")
    print("  1. 加载 PNG 文件")
    print("  2. 读取对应的 JSON metadata")
    print("  3. 根据 metadata 中的 animations 定义切分帧")
    print()
    print("示例（伪代码）：")
    print("  sprite_sheet = load_image('warrior_2001.png')")
    print("  metadata = load_json('warrior_2001.json')")
    print("  walk_down = metadata['animations']['walk_down']")
    print("  # walk_down.row = 0, walk_down.frames = 4")
    print("  # 从 sprite_sheet 第 0 行提取 4 帧")


if __name__ == "__main__":
    main()
