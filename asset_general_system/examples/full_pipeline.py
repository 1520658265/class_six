#!/usr/bin/env python
"""
完整流程示例：从 prompt 到引擎资源包

这个脚本演示如何使用本系统生成完整的 RPG 资源包。
"""

import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.parser import RulePromptParser
from generator.models import GenerateRequest
from generator.map import MapGenerator
from generator.assets.image_generation import MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.characters import CharacterGenerator, generate_standard_characters
from generator.vfx import VFXGenerator, generate_standard_vfx
from generator.map.object_placer import ObjectPlacer
from generator.assets.asset_library import AssetLibrary
from generator.export import GodotExporter, UnityExporter, PhaserExporter
from generator.render import PreviewRenderer


def main():
    output_base = Path("output/full_demo")

    print("="*60)
    print("完整 RPG 资源生成流程 Demo")
    print("="*60)
    print()
    print("注意：本 Demo 使用 MockImageGenerator（纯色块）")
    print("要使用真实 AI 生成，请配置 Gemini API key")
    print("详见：docs/USAGE.md")
    print()

    # 使用 Mock 生成器（快速演示）
    # 要用真实 AI，替换成：
    # from generator.assets.gemini_generator import GeminiImageGenerator
    # image_gen = GeminiImageGenerator(output_base / "gemini")
    image_gen = MockImageGenerator(output_base / "mock")

    # 1. 生成素材库
    print("\n[1/6] 生成素材库...")

    # 1a. 对象
    print("  生成 20 种对象...")
    obj_gen = ObjectGenerator(image_gen, output_base / "objects")
    obj_results = generate_standard_objects(obj_gen, seed_offset=5000)
    success_objs = [r for r in obj_results if r.success]
    print(f"  [OK] {len(success_objs)}/20 对象")

    # 1b. 角色
    print("  生成 10 个角色...")
    char_gen = CharacterGenerator(image_gen, output_base / "characters")
    char_results = generate_standard_characters(char_gen, seed_offset=6000)
    success_chars = [r for r in char_results if r.success]
    print(f"  [OK] {len(success_chars)}/10 角色")

    # 1c. 特效
    print("  生成 10 种 VFX...")
    vfx_gen = VFXGenerator(image_gen, output_base / "vfx")
    vfx_results = generate_standard_vfx(vfx_gen, seed_offset=7000)
    success_vfx = [r for r in vfx_results if r.success]
    print(f"  [OK] {len(success_vfx)}/10 VFX")

    # 2. 生成地图
    print("\n[2/6] 生成地图...")
    parser = RulePromptParser()
    request = GenerateRequest(prompt="生成一个秋季森林村庄，中间有集市，左侧有河流")
    spec = parser.parse(request)
    generator = MapGenerator()
    tilemap = generator.generate(spec)
    print(f"  [OK] 地图尺寸: {tilemap.map.width}x{tilemap.map.height}")
    print(f"  [OK] 区域数: {len(tilemap.regions)}")

    # 3. 放置对象
    print("\n[3/6] 放置对象到地图...")
    library = AssetLibrary(output_base / "objects")
    placer = ObjectPlacer(library)

    # 在集市区域放置摊位
    for region in tilemap.regions:
        if region.type == "market":
            cx, cy = region.center
            for i in range(-2, 3):
                placer.place_decoration_objects(
                    tilemap,
                    object_type="stall",
                    positions=[(cx + i, cy)]
                )
    print(f"  [OK] 已放置 {len(tilemap.objects)} 个对象")

    # 4. 生成预览图
    print("\n[4/6] 生成预览图...")
    renderer = PreviewRenderer()
    preview_path = output_base / "preview.png"
    renderer.render(tilemap, preview_path)
    print(f"  [OK] 预览图: {preview_path}")

    # 5. 导出到三个引擎
    print("\n[5/6] 导出到游戏引擎...")

    # 5a. Godot
    print("  导出到 Godot...")
    godot_exp = GodotExporter()
    godot_report = godot_exp.export(tilemap, output_base / "godot", "demo_map")
    print(f"    [OK] {len(godot_report['files'])} 个文件")

    # 5b. Unity
    print("  导出到 Unity...")
    unity_exp = UnityExporter()
    unity_report = unity_exp.export(tilemap, output_base / "unity")
    print(f"    [OK] {len(unity_report['files'])} 个文件")

    # 5c. Phaser
    print("  导出到 Phaser...")
    phaser_exp = PhaserExporter()
    phaser_report = phaser_exp.export(tilemap, output_base / "phaser", "DemoScene")
    print(f"    [OK] {len(phaser_report['files'])} 个文件")

    # 6. 生成报告
    print("\n[6/6] 生成总结报告...")
    report_path = output_base / "REPORT.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("="*60 + "\n")
        f.write("RPG 资源生成报告\n")
        f.write("="*60 + "\n\n")

        f.write("素材统计：\n")
        f.write(f"  对象：{len(success_objs)}/20\n")
        f.write(f"  角色：{len(success_chars)}/10\n")
        f.write(f"  特效：{len(success_vfx)}/10\n\n")

        f.write("地图信息：\n")
        f.write(f"  尺寸：{tilemap.map.width}x{tilemap.map.height}\n")
        f.write(f"  区域数：{len(tilemap.regions)}\n")
        f.write(f"  对象数：{len(tilemap.objects)}\n")
        f.write(f"  事件数：{len(tilemap.events)}\n\n")

        f.write("导出引擎：\n")
        f.write(f"  Godot 4.x：godot/demo_map.tscn\n")
        f.write(f"  Unity：unity/map.unity.json\n")
        f.write(f"  Phaser 3：phaser/tilemap.json\n\n")

        f.write("对象列表：\n")
        for r in success_objs[:10]:
            f.write(f"  - {r.asset_id}\n")
        if len(success_objs) > 10:
            f.write(f"  ... 还有 {len(success_objs) - 10} 个\n")

        f.write("\n角色列表：\n")
        for r in success_chars:
            f.write(f"  - {r.asset_id} ({len(r.metadata.animations)} 动画)\n")

        f.write("\nVFX 列表：\n")
        for r in success_vfx:
            f.write(f"  - {r.asset_id} ({r.metadata.category.value})\n")

    print(f"  [OK] 报告: {report_path}")

    print("\n" + "="*60)
    print("[全部完成!]")
    print("="*60)
    print(f"\n输出目录: {output_base.absolute()}")
    print()
    print("目录结构：")
    print("  objects/    - 20 种对象素材 + metadata")
    print("  characters/ - 10 个角色 sprite sheet + metadata")
    print("  vfx/        - 10 种特效 + metadata")
    print("  godot/      - Godot 4.x 场景和资源")
    print("  unity/      - Unity 数据和导入脚本")
    print("  phaser/     - Phaser 3 tilemap 和场景")
    print("  preview.png - 地图预览图")
    print("  REPORT.txt  - 生成报告")
    print()
    print("下一步：")
    print("  1. 查看预览图：output/full_demo/preview.png")
    print("  2. 在 Godot 中打开：output/full_demo/godot/demo_map.tscn")
    print("  3. 或在浏览器打开：output/full_demo/phaser/index.html")
    print()
    print("使用真实 AI 生成：")
    print("  1. 配置 Gemini API key（见 docs/USAGE.md）")
    print("  2. 替换 MockImageGenerator 为 GeminiImageGenerator")
    print("  3. 重新运行本脚本")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
