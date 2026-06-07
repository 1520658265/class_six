"""
Phase 4 端到端集成测试：
- 生成标准对象集
- 创建 tilemap，使用 ObjectPlacer 放置对象
- 导出 Tiled JSON，验证 sprite 信息在输出中
- 渲染预览，验证能正确处理有 sprite 和无 sprite 的对象
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.assets.asset_library import AssetLibrary
from generator.assets.image_generation import ImageStyle, MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.export.tiled_exporter import TiledExporter
from generator.map.object_placer import ObjectPlacer
from generator.models import MapInfo, ObjectData, TilemapData, TilesetInfo
from generator.render.preview_renderer import PreviewRenderer


def create_test_tilemap() -> TilemapData:
    """创建用于测试的 tilemap 数据。"""
    width, height = 32, 32
    size = width * height
    return TilemapData(
        map=MapInfo(width=width, height=height),
        tileset=TilesetInfo(),
        layers={
            "terrain": [1] * size,
            "path": [0] * size,
            "building": [0] * size,
            "decoration": [0] * size,
            "collision": [0] * size,
        },
        metadata={"theme": "forest_village", "seed": 42},
    )


def test_generate_objects_and_place(tmpdir: Path):
    """测试：生成标准对象集并放置到 tilemap。"""
    print("[测试] 生成标准对象集...")

    # Arrange: 生成对象
    mock_gen = MockImageGenerator(tmpdir / "mock")
    obj_gen = ObjectGenerator(mock_gen, tmpdir / "objects")
    results = generate_standard_objects(obj_gen, seed_offset=5000)

    success_count = sum(1 for r in results if r.success)
    assert success_count == 20, f"期望生成 20 个对象，实际 {success_count}"
    print(f"  生成 {success_count} 个对象成功")

    # 加载资产库
    library = AssetLibrary(tmpdir / "objects")
    assert len(library.assets) == 20, f"库中应有 20 个资产，实际 {len(library.assets)}"
    print(f"  资产库加载 {len(library.assets)} 个资产")

    # Act: 创建 tilemap 并放置对象
    tilemap = create_test_tilemap()
    placer = ObjectPlacer(library)

    # 放置有 sprite 的对象
    tree = placer.create_object_with_sprite("tree_01", "tree_oak", 5, 5)
    tilemap.objects.append(tree)

    rocks = placer.place_decoration_objects(
        tilemap, "rock_small", [(10, 10), (12, 10), (14, 10)]
    )

    chest = placer.create_object_with_sprite("chest_01", "chest", 20, 15)
    tilemap.objects.append(chest)

    # 放置无 sprite 的对象（未知类型）
    no_sprite_obj = ObjectData(
        id="unknown_01", type="mystery_artifact", x=25, y=25
    )
    tilemap.objects.append(no_sprite_obj)

    # Assert: 验证 sprite 引用
    assert tree.sprite_ref is not None, "树应有 sprite_ref"
    assert tree.sprite_path is not None, "树应有 sprite_path"
    assert all(r.sprite_ref for r in rocks), "所有岩石应有 sprite_ref"
    assert chest.sprite_ref is not None, "宝箱应有 sprite_ref"
    assert no_sprite_obj.sprite_ref is None, "未知对象不应有 sprite_ref"

    print(f"  放置 {len(tilemap.objects)} 个对象（{len(tilemap.objects)-1} 有 sprite, 1 无 sprite）")
    return tilemap, library


def test_tiled_export_contains_sprite_info(tilemap: TilemapData, tmpdir: Path):
    """测试：Tiled JSON 导出中包含 sprite_ref 和 sprite_path 属性。"""
    print("\n[测试] Tiled JSON 导出 sprite 信息...")

    # Act: 导出 Tiled JSON
    exporter = TiledExporter()
    output_path = tmpdir / "output" / "map.tiled.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = exporter.export(tilemap, output_path)

    # 找到 objects layer
    objects_layer = None
    for layer in data["layers"]:
        if layer.get("name") == "objects":
            objects_layer = layer
            break

    assert objects_layer is not None, "应存在 objects layer"
    assert objects_layer["type"] == "objectgroup"
    assert len(objects_layer["objects"]) == len(tilemap.objects)

    # Assert: 有 sprite 的对象应包含 sprite_ref/sprite_path 属性
    tree_obj = next(o for o in objects_layer["objects"] if o["name"] == "tree_01")
    tree_props = {p["name"]: p["value"] for p in tree_obj["properties"]}
    assert "sprite_ref" in tree_props, "树对象应有 sprite_ref 属性"
    assert "sprite_path" in tree_props, "树对象应有 sprite_path 属性"
    print(f"  tree_01 sprite_ref = {tree_props['sprite_ref']}")

    # Assert: 无 sprite 的对象不应有 sprite_ref 属性
    unknown_obj = next(o for o in objects_layer["objects"] if o["name"] == "unknown_01")
    unknown_props = {p["name"]: p["value"] for p in unknown_obj["properties"]}
    assert "sprite_ref" not in unknown_props, "未知对象不应有 sprite_ref"
    assert "sprite_path" not in unknown_props, "未知对象不应有 sprite_path"

    # Assert: 验证尺寸正确反映 footprint
    assert tree_obj["width"] == tilemap.map.tile_width * 1  # footprint (1, 2)
    assert tree_obj["height"] == tilemap.map.tile_height * 2

    # 验证 JSON 文件可正常读取
    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["type"] == "map"
    print(f"  Tiled JSON 导出成功: {output_path}")
    print(f"  对象数量: {len(objects_layer['objects'])}")


def test_preview_render_with_sprites(tilemap: TilemapData, tmpdir: Path):
    """测试：预览渲染器正确处理有 sprite 和无 sprite 的对象。"""
    print("\n[测试] 预览渲染 sprite 对象...")

    # Act: 渲染预览图
    renderer = PreviewRenderer()
    preview_path = tmpdir / "output" / "preview.png"
    renderer.render(tilemap, preview_path)

    # Assert: 输出文件存在
    assert preview_path.exists(), f"预览图应存在: {preview_path}"

    # 验证图片尺寸正确
    from PIL import Image
    img = Image.open(preview_path)
    expected_w = tilemap.map.width * tilemap.map.tile_width
    expected_h = tilemap.map.height * tilemap.map.tile_height
    assert img.size == (expected_w, expected_h), (
        f"图片尺寸应为 ({expected_w}, {expected_h})，实际 {img.size}"
    )

    # 验证图片不全黑（确认渲染了内容）
    pixels = list(img.getdata())
    non_black = sum(1 for p in pixels if p != (0, 0, 0))
    assert non_black > 0, "渲染图不应全黑"
    img.close()

    print(f"  预览图生成成功: {preview_path} ({expected_w}x{expected_h})")
    print(f"  非黑色像素: {non_black}")


def test_preview_render_debug_mode(tilemap: TilemapData, tmpdir: Path):
    """测试：debug 模式渲染不崩溃。"""
    print("\n[测试] Debug 模式预览渲染...")

    renderer = PreviewRenderer()
    debug_path = tmpdir / "output" / "preview_debug.png"
    renderer.render(tilemap, debug_path, debug=True)

    assert debug_path.exists(), "Debug 预览图应存在"
    print(f"  Debug 预览图生成成功: {debug_path}")


def run_all_tests():
    """运行所有集成测试。"""
    print("=" * 60)
    print("Phase 4 端到端集成测试")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # 测试 1: 生成和放置对象
        tilemap, library = test_generate_objects_and_place(tmpdir)

        # 测试 2: Tiled JSON 导出包含 sprite 信息
        test_tiled_export_contains_sprite_info(tilemap, tmpdir)

        # 测试 3: 预览渲染处理 sprite 对象
        test_preview_render_with_sprites(tilemap, tmpdir)

        # 测试 4: Debug 模式渲染
        test_preview_render_debug_mode(tilemap, tmpdir)

    print("\n" + "=" * 60)
    print("[全部通过] Phase 4 集成测试全部通过！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        run_all_tests()
    except Exception as e:
        print(f"\n[失败] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
