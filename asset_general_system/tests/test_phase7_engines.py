"""
Phase 7 测试：三个引擎导出器（Godot, Unity, Phaser）。
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from generator.export.godot_exporter import GodotExporter
from generator.export.phaser_exporter import PhaserExporter
from generator.export.unity_exporter import UnityExporter
from generator.models import (
    MapInfo,
    ObjectData,
    RegionData,
    TilemapData,
    TilesetInfo,
)


def make_test_tilemap() -> TilemapData:
    """构建测试用的 tilemap。"""
    width = 16
    height = 16

    tilemap = TilemapData(
        map=MapInfo(width=width, height=height, tile_width=32, tile_height=32),
        tileset=TilesetInfo(),
        layers={
            "terrain": [1] * (width * height),
            "path": [0] * (width * height),
            "building": [0] * (width * height),
            "decoration": [0] * (width * height),
            "collision": [0] * (width * height),
        },
        metadata={"theme": "test", "seed": 1},
    )

    # 添加一些路径
    for x in range(2, 14):
        tilemap.layers["path"][8 * width + x] = 10  # dirt_road

    # 添加对象
    tilemap.objects.append(ObjectData(
        id="tree_01",
        type="tree_oak",
        x=4,
        y=4,
        width=1,
        height=2,
        sprite_ref="tree_oak_1000",
        sprite_path="objects/tree_oak_1000.png",
    ))
    tilemap.objects.append(ObjectData(
        id="chest_01",
        type="chest",
        x=10,
        y=10,
        sprite_ref="chest_1001",
        sprite_path="objects/chest_1001.png",
    ))

    # 事件
    tilemap.events.append(ObjectData(
        id="spawn_01",
        type="player_spawn",
        x=2,
        y=8,
    ))

    # 区域
    tilemap.regions.append(RegionData(
        id="area_01",
        type="market",
        bounds=[2, 2, 14, 14],
        center=[8, 8],
        access=[8, 8],
    ))

    return tilemap


def test_godot_exporter():
    """测试 Godot 导出。"""
    print("测试 Godot 导出器...")

    tilemap = make_test_tilemap()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "godot"
        exporter = GodotExporter()
        report = exporter.export(tilemap, output_dir, scene_name="test_level")

        # 验证文件
        assert (output_dir / "tileset.tres").exists(), "应有 tileset.tres"
        assert (output_dir / "test_level.tscn").exists(), "应有 .tscn 场景"
        assert (output_dir / "objects.json").exists(), "应有 objects.json"
        assert (output_dir / "README.md").exists(), "应有 README"

        # 验证 .tscn 内容
        scene_text = (output_dir / "test_level.tscn").read_text(encoding="utf-8")
        assert "[gd_scene" in scene_text, "应是 Godot 场景"
        assert "TileMap" in scene_text, "应包含 TileMap 节点"
        assert "tree_01" in scene_text, "应包含对象节点"
        assert 'metadata/sprite_ref' in scene_text, "应有 sprite_ref metadata"

        # 验证 objects.json
        objects_data = json.loads((output_dir / "objects.json").read_text(encoding="utf-8"))
        assert objects_data["map"]["width"] == 16
        assert len(objects_data["objects"]) == 2
        assert objects_data["objects"][0]["sprite_ref"] == "tree_oak_1000"

        print(f"  [OK] Godot 导出: {len(report['files'])} 个文件")


def test_unity_exporter():
    """测试 Unity 导出。"""
    print("\n测试 Unity 导出器...")

    tilemap = make_test_tilemap()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "unity"
        exporter = UnityExporter()
        report = exporter.export(tilemap, output_dir)

        assert (output_dir / "map.unity.json").exists()
        assert (output_dir / "ImportTilemap.cs").exists()
        assert (output_dir / "README.md").exists()

        # 验证 JSON
        data = json.loads((output_dir / "map.unity.json").read_text(encoding="utf-8"))
        assert data["engine"] == "unity"
        assert data["map"]["width"] == 16
        assert data["map"]["tileWidth"] == 32
        assert len(data["tileLayers"]) == 5  # terrain/path/building/decoration/collision
        assert len(data["objects"]) == 2
        assert data["objects"][0]["spriteRef"] == "tree_oak_1000"

        # collision 层应为 invisible
        collision_layer = next(l for l in data["tileLayers"] if l["name"] == "collision")
        assert collision_layer["visible"] is False

        # 验证 C# 脚本
        cs_text = (output_dir / "ImportTilemap.cs").read_text(encoding="utf-8")
        assert "public class ImportTilemap" in cs_text
        assert "Tilemap" in cs_text

        print(f"  [OK] Unity 导出: {len(report['files'])} 个文件")


def test_phaser_exporter():
    """测试 Phaser 导出。"""
    print("\n测试 Phaser 导出器...")

    tilemap = make_test_tilemap()

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir) / "phaser"
        exporter = PhaserExporter()
        report = exporter.export(tilemap, output_dir, scene_key="TestScene")

        assert (output_dir / "tilemap.json").exists()
        assert (output_dir / "TestScene.js").exists()
        assert (output_dir / "index.html").exists()
        assert (output_dir / "README.md").exists()

        # 验证 tilemap.json 是合法的 Tiled 格式
        data = json.loads((output_dir / "tilemap.json").read_text(encoding="utf-8"))
        assert data["type"] == "map"
        assert data["orientation"] == "orthogonal"
        assert data["width"] == 16
        assert len(data["tilesets"]) == 1

        # 应有 tile layers + objects layer + events layer
        layer_names = [l["name"] for l in data["layers"]]
        assert "terrain" in layer_names
        assert "objects" in layer_names
        assert "events" in layer_names

        # 验证 objects 层包含 sprite_ref
        objects_layer = next(l for l in data["layers"] if l["name"] == "objects")
        tree_obj = next(o for o in objects_layer["objects"] if o["name"] == "tree_01")
        prop_names = [p["name"] for p in tree_obj["properties"]]
        assert "sprite_ref" in prop_names
        assert "sprite_path" in prop_names

        # 验证 JS
        js_text = (output_dir / "TestScene.js").read_text(encoding="utf-8")
        assert "class TestScene extends Phaser.Scene" in js_text
        assert "createLayer" in js_text

        print(f"  [OK] Phaser 导出: {len(report['files'])} 个文件")


def test_all_three_engines_consistent():
    """验证三个引擎导出的数据一致性。"""
    print("\n测试三引擎导出一致性...")

    tilemap = make_test_tilemap()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Godot
        godot_dir = Path(tmpdir) / "godot"
        GodotExporter().export(tilemap, godot_dir)
        godot_objects = json.loads((godot_dir / "objects.json").read_text(encoding="utf-8"))

        # Unity
        unity_dir = Path(tmpdir) / "unity"
        UnityExporter().export(tilemap, unity_dir)
        unity_data = json.loads((unity_dir / "map.unity.json").read_text(encoding="utf-8"))

        # Phaser
        phaser_dir = Path(tmpdir) / "phaser"
        PhaserExporter().export(tilemap, phaser_dir)
        phaser_data = json.loads((phaser_dir / "tilemap.json").read_text(encoding="utf-8"))

        # 一致性检查
        assert godot_objects["map"]["width"] == unity_data["map"]["width"] == phaser_data["width"]
        assert len(godot_objects["objects"]) == len(unity_data["objects"]) == 2

        # Phaser 的 objects 在 layers 中
        phaser_objects_layer = next(l for l in phaser_data["layers"] if l["name"] == "objects")
        assert len(phaser_objects_layer["objects"]) == 2

        print("  [OK] 三引擎数据一致")


if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("Phase 7: 引擎导出器测试")
        print("="*60)

        test_godot_exporter()
        test_unity_exporter()
        test_phaser_exporter()
        test_all_three_engines_consistent()

        print("\n" + "="*60)
        print("[全部通过] Phase 7 测试通过!")
        print("="*60)

    except Exception as e:
        print(f"\n[失败] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
