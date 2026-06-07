"""
Phase 4 端到端集成测试：
- 创建带外部美术引用的 tilemap
- 导出 Tiled JSON，验证 sprite 信息在输出中
- 渲染预览，验证能正确处理有 sprite 和无 sprite 的对象
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.export.tiled_exporter import TiledExporter
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


def _create_tilemap_with_external_art_refs() -> TilemapData:
    """创建已由外部美术流程回填 sprite 引用的 tilemap。"""
    tilemap = create_test_tilemap()
    tilemap.objects.extend(
        [
            ObjectData(
                id="tree_01",
                type="tree_oak",
                x=5,
                y=5,
                width=1,
                height=2,
                sprite_ref="tree_oak_1000",
                sprite_path="art/objects/tree_oak_1000.png",
            ),
            ObjectData(
                id="rock_01",
                type="rock_small",
                x=10,
                y=10,
                sprite_ref="rock_small_1001",
                sprite_path="art/objects/rock_small_1001.png",
            ),
            ObjectData(
                id="rock_02",
                type="rock_small",
                x=12,
                y=10,
                sprite_ref="rock_small_1001",
                sprite_path="art/objects/rock_small_1001.png",
            ),
            ObjectData(
                id="chest_01",
                type="chest",
                x=20,
                y=15,
                sprite_ref="chest_1002",
                sprite_path="art/objects/chest_1002.png",
            ),
            ObjectData(
                id="unknown_01",
                type="mystery_artifact",
                x=25,
                y=25,
            ),
        ]
    )
    return tilemap


def test_tilemap_can_hold_external_art_references():
    tilemap = _create_tilemap_with_external_art_refs()

    assert len(tilemap.objects) == 5
    assert sum(1 for obj in tilemap.objects if obj.sprite_ref) == 4
    assert next(obj for obj in tilemap.objects if obj.id == "unknown_01").sprite_ref is None


@pytest.fixture
def tilemap() -> TilemapData:
    return _create_tilemap_with_external_art_refs()


def test_tiled_export_contains_sprite_info(tilemap: TilemapData, tmp_path: Path):
    """测试：Tiled JSON 导出中包含 sprite_ref 和 sprite_path 属性。"""
    print("\n[测试] Tiled JSON 导出 sprite 信息...")

    # Act: 导出 Tiled JSON
    exporter = TiledExporter()
    output_path = tmp_path / "output" / "map.tiled.json"
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


def test_preview_render_with_sprites(tilemap: TilemapData, tmp_path: Path):
    """测试：预览渲染器正确处理有 sprite 和无 sprite 的对象。"""
    print("\n[测试] 预览渲染 sprite 对象...")

    # Act: 渲染预览图
    renderer = PreviewRenderer()
    preview_path = tmp_path / "output" / "preview.png"
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


def test_preview_render_debug_mode(tilemap: TilemapData, tmp_path: Path):
    """测试：debug 模式渲染不崩溃。"""
    print("\n[测试] Debug 模式预览渲染...")

    renderer = PreviewRenderer()
    debug_path = tmp_path / "output" / "preview_debug.png"
    renderer.render(tilemap, debug_path, debug=True)

    assert debug_path.exists(), "Debug 预览图应存在"
    print(f"  Debug 预览图生成成功: {debug_path}")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
