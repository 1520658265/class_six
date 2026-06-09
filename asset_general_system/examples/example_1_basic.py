#!/usr/bin/env python
"""
实战示例 1：生成一个完整的秋季村庄地图

这个示例演示最常见的使用场景：
1. 生成地图
2. 生成素材
3. 放置素材到地图
4. 导出到游戏引擎
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.map import MapGenerator
from generator.assets.image_generation import MockImageGenerator
from generator.assets.object_generator import ObjectGenerator
from generator.map.object_placer import ObjectPlacer
from generator.assets.asset_library import AssetLibrary
from generator.export import GodotExporter
from generator.render import PreviewRenderer


def main():
    print("="*60)
    print("实战示例：生成秋季村庄地图")
    print("="*60)
    print()

    output_dir = Path("output/example_autumn_village")

    # ==================== 步骤 1：生成地图 ====================
    print("步骤 1：生成地图")
    print("-"*60)

    # 1.1 创建 prompt
    prompt = """
    生成一个秋季森林村庄地图
    - 中间是村庄广场，有集市
    - 左侧有小河流过
    - 右上角有一座小神庙
    - 村庄周围是树林
    - 地图尺寸 32x32
    """

    print(f"Prompt: {prompt.strip()}")
    print()

    # 1.2 解析 prompt 为 spec
    parser = RulePromptParser()
    request = GenerateRequest(prompt=prompt, seed=12345)
    spec = parser.parse(request)
    print(f"✓ 解析完成: 主题={spec.theme}, 种子={spec.seed}")

    # 1.3 生成地图
    generator = MapGenerator()
    tilemap = generator.generate(spec)
    print(f"✓ 生成完成: {tilemap.map.width}x{tilemap.map.height}")
    print(f"  - 区域数: {len(tilemap.regions)}")
    print(f"  - 层数: {len(tilemap.layers)}")
    print()

    # ==================== 步骤 2：生成素材 ====================
    print("步骤 2：生成素材")
    print("-"*60)

    # 使用 Mock 生成器（快速演示）
    # 真实使用时替换为 GeminiImageGenerator
    image_gen = MockImageGenerator(output_dir / "mock")
    obj_gen = ObjectGenerator(image_gen, output_dir / "objects")

    # 2.1 生成橡树
    from generator.assets.object_generator import ObjectGenerationRequest

    print("生成素材：橡树、松树、岩石、宝箱...")
    objects_to_generate = [
        ObjectGenerationRequest(
            object_type="oak_tree",
            description="oak tree with green leaves",
            footprint=(1, 2),
            tags=["tree", "oak", "nature"],
            seed=1001,
        ),
        ObjectGenerationRequest(
            object_type="pine_tree",
            description="pine tree with dark green needles",
            footprint=(1, 2),
            tags=["tree", "pine", "nature"],
            seed=1002,
        ),
        ObjectGenerationRequest(
            object_type="rock",
            description="small gray rock",
            footprint=(1, 1),
            tags=["rock", "stone", "nature"],
            seed=1003,
        ),
        ObjectGenerationRequest(
            object_type="chest",
            description="wooden treasure chest",
            footprint=(1, 1),
            tags=["chest", "treasure", "container"],
            seed=1004,
        ),
        ObjectGenerationRequest(
            object_type="market_stall",
            description="wooden market stall with striped canopy",
            footprint=(2, 1),
            tags=["stall", "market", "shop"],
            seed=1005,
        ),
    ]

    results = []
    for req in objects_to_generate:
        result = obj_gen.generate(req)
        results.append(result)
        if result.success:
            print(f"  ✓ {result.asset_id}")

    print(f"✓ 生成完成: {len([r for r in results if r.success])}/{len(objects_to_generate)}")
    print()

    # ==================== 步骤 3：放置素材到地图 ====================
    print("步骤 3：放置素材到地图")
    print("-"*60)

    # 3.1 加载素材库
    library = AssetLibrary(output_dir / "objects")
    placer = ObjectPlacer(library)

    # 3.2 根据区域类型放置对象
    for region in tilemap.regions:
        cx, cy = region.center

        if region.type == "market":
            # 集市：放置摊位
            print(f"  在集市区域 ({cx}, {cy}) 放置摊位...")
            for i in range(-2, 3):
                placer.place_decoration_objects(
                    tilemap,
                    object_type="market_stall",
                    positions=[(cx + i, cy)]
                )

        elif region.type == "forest":
            # 森林：放置树木
            print(f"  在森林区域 ({cx}, {cy}) 放置树木...")
            import random
            random.seed(region.id.__hash__())
            for _ in range(5):
                x = random.randint(region.bounds[0], region.bounds[2])
                y = random.randint(region.bounds[1], region.bounds[3])
                tree_type = random.choice(["oak_tree", "pine_tree"])
                placer.place_decoration_objects(
                    tilemap,
                    object_type=tree_type,
                    positions=[(x, y)]
                )

        elif region.type == "temple":
            # 神庙：放置宝箱
            print(f"  在神庙区域 ({cx}, {cy}) 放置宝箱...")
            placer.place_decoration_objects(
                tilemap,
                object_type="chest",
                positions=[(cx, cy)]
            )

    print(f"✓ 放置完成: 共 {len(tilemap.objects)} 个对象")
    print()

    # ==================== 步骤 4：生成预览图 ====================
    print("步骤 4：生成预览图")
    print("-"*60)

    renderer = PreviewRenderer()
    preview_path = output_dir / "preview.png"
    renderer.render(tilemap, preview_path)
    print(f"✓ 预览图: {preview_path.absolute()}")
    print()

    # ==================== 步骤 5：导出到 Godot ====================
    print("步骤 5：导出到 Godot")
    print("-"*60)

    exporter = GodotExporter()
    report = exporter.export(tilemap, output_dir / "godot", scene_name="autumn_village")

    print(f"✓ 导出完成:")
    for filename in report['files']:
        print(f"  - {filename}")
    print()

    # ==================== 完成 ====================
    print("="*60)
    print("✓ 全部完成！")
    print("="*60)
    print()
    print(f"输出目录: {output_dir.absolute()}")
    print()
    print("生成的文件：")
    print(f"  1. 预览图: {preview_path.name}")
    print(f"  2. Godot 场景: godot/autumn_village.tscn")
    print(f"  3. 对象素材: objects/*.png")
    print()
    print("下一步：")
    print("  1. 查看预览图")
    print("  2. 在 Godot 中打开场景文件")
    print("  3. 或修改上面的代码，生成不同的地图")
    print()
    print("提示：要使用真实 AI 生成，替换第 56 行：")
    print("  from generator.assets.gemini_generator import GeminiImageGenerator")
    print("  image_gen = GeminiImageGenerator(output_dir / 'gemini')")


if __name__ == "__main__":
    main()
