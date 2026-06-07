"""
Godot 引擎导出器。

把 TilemapData 导出为 Godot 4.x 可直接使用的资源：
- TileSet (.tres)
- TileMap 场景 (.tscn)
- 对象/事件层（作为 Node2D 子节点）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import TilemapData


class GodotExporter:
    """
    Godot 4.x 引擎导出器。

    输出文件：
    - tileset.tres: TileSet 资源
    - level.tscn: 包含 TileMap 节点的场景
    - layers/*.tres: 每个 tile layer 的数据
    - objects.json: 对象层数据（运行时加载）
    """

    def export(
        self,
        tilemap: TilemapData,
        output_dir: Path,
        scene_name: str = "level",
    ) -> dict[str, Any]:
        """
        导出 Godot 项目结构。

        Args:
            tilemap: 地图数据
            output_dir: 输出目录
            scene_name: 场景名

        Returns:
            包含导出文件列表的报告
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files = []

        # 1. 导出 TileSet 资源
        tileset_path = output_dir / "tileset.tres"
        self._export_tileset(tilemap, tileset_path)
        files.append(str(tileset_path.relative_to(output_dir)))

        # 2. 导出 TileMap 场景
        scene_path = output_dir / f"{scene_name}.tscn"
        self._export_scene(tilemap, scene_path, tileset_relative_path="tileset.tres")
        files.append(str(scene_path.relative_to(output_dir)))

        # 3. 导出对象数据（运行时加载）
        objects_path = output_dir / "objects.json"
        self._export_objects(tilemap, objects_path)
        files.append(str(objects_path.relative_to(output_dir)))

        # 4. 导出导入指引
        readme_path = output_dir / "README.md"
        self._write_readme(readme_path, scene_name)
        files.append(str(readme_path.relative_to(output_dir)))

        return {
            "engine": "godot_4",
            "output_dir": str(output_dir),
            "scene": scene_name,
            "files": files,
            "layers": list(tilemap.layers.keys()),
            "object_count": len(tilemap.objects),
            "event_count": len(tilemap.events),
        }

    def _export_tileset(self, tilemap: TilemapData, path: Path) -> None:
        """导出 TileSet 资源 (.tres 格式)。"""
        tile_w = tilemap.map.tile_width
        tile_h = tilemap.map.tile_height
        tileset_image = tilemap.tileset.image

        # Godot 4.x .tres 格式
        lines = [
            '[gd_resource type="TileSet" load_steps=2 format=3]',
            "",
            f'[ext_resource type="Texture2D" path="res://{tileset_image}" id="1"]',
            "",
            "[resource]",
            f'tile_size = Vector2i({tile_w}, {tile_h})',
            'physics_layer_0/collision_layer = 1',
            'physics_layer_0/collision_mask = 1',
            "",
            "[sub_resource type=\"TileSetAtlasSource\" id=\"atlas_0\"]",
            'texture = ExtResource("1")',
            f'texture_region_size = Vector2i({tile_w}, {tile_h})',
            "",
            "sources/0 = SubResource(\"atlas_0\")",
        ]

        path.write_text("\n".join(lines), encoding="utf-8")

    def _export_scene(
        self,
        tilemap: TilemapData,
        path: Path,
        tileset_relative_path: str,
    ) -> None:
        """导出 .tscn 场景文件。"""
        width = tilemap.map.width
        height = tilemap.map.height

        # 计算场景中需要多少个外部资源
        ext_resources = [
            f'[ext_resource type="TileSet" path="res://{tileset_relative_path}" id="tileset_1"]',
        ]

        # 场景头
        load_steps = len(ext_resources) + 1
        lines = [
            f'[gd_scene load_steps={load_steps} format=3]',
            "",
            *ext_resources,
            "",
            '[node name="Level" type="Node2D"]',
            "",
        ]

        # 为每个 tile layer 创建一个 TileMap 节点
        layer_order = ["terrain", "path", "building", "decoration", "collision"]
        for layer_name in layer_order:
            if layer_name not in tilemap.layers:
                continue
            data = tilemap.layers[layer_name]
            lines.append(f'[node name="{layer_name.capitalize()}" type="TileMap" parent="."]')
            lines.append('tile_set = ExtResource("tileset_1")')
            lines.append(f'format = 2')
            # collision 层默认隐藏
            if layer_name == "collision":
                lines.append('visible = false')

            # 编码 tile data 为 layer_0/tile_data
            packed = self._encode_tile_data(data, width, height)
            if packed:
                lines.append(f'layer_0/tile_data = PackedInt32Array({packed})')
            lines.append("")

        # objects 父节点
        lines.append('[node name="Objects" type="Node2D" parent="."]')
        lines.append("")

        for obj in tilemap.objects:
            px = obj.x * tilemap.map.tile_width + tilemap.map.tile_width // 2
            py = obj.y * tilemap.map.tile_height + tilemap.map.tile_height // 2
            safe_id = obj.id.replace("-", "_")
            lines.append(f'[node name="{safe_id}" type="Node2D" parent="Objects"]')
            lines.append(f'position = Vector2({px}, {py})')
            lines.append(f'metadata/object_type = "{obj.type}"')
            if obj.sprite_ref:
                lines.append(f'metadata/sprite_ref = "{obj.sprite_ref}"')
            if obj.sprite_path:
                lines.append(f'metadata/sprite_path = "{obj.sprite_path}"')
            lines.append("")

        # events 父节点
        lines.append('[node name="Events" type="Node2D" parent="."]')
        lines.append("")
        for event in tilemap.events:
            px = event.x * tilemap.map.tile_width + tilemap.map.tile_width // 2
            py = event.y * tilemap.map.tile_height + tilemap.map.tile_height // 2
            safe_id = event.id.replace("-", "_")
            lines.append(f'[node name="{safe_id}" type="Marker2D" parent="Events"]')
            lines.append(f'position = Vector2({px}, {py})')
            lines.append(f'metadata/event_type = "{event.type}"')
            lines.append("")

        path.write_text("\n".join(lines), encoding="utf-8")

    def _encode_tile_data(self, data: list[int], width: int, height: int) -> str:
        """
        把 tile id 数组编码为 Godot 的 PackedInt32Array 格式。
        每个 tile 用 3 个 int32 表示: (x, y, source_id_packed)
        """
        items = []
        for y in range(height):
            for x in range(width):
                idx = y * width + x
                if idx >= len(data) or data[idx] == 0:
                    continue
                tile_id = data[idx]
                # Godot tile 编码: x << 16 | y, 0, source 数据
                # 简化为: position_packed, source_id, atlas_coords_packed
                pos_packed = (x & 0xFFFF) | ((y & 0xFFFF) << 16)
                # source_id = 0 (默认 atlas)
                # atlas_coords: 用 tile_id 作为 x，0 作为 y
                atlas_packed = ((tile_id - 1) & 0xFFFF) | (0 << 16)
                items.extend([str(pos_packed), "0", str(atlas_packed)])
        return ", ".join(items)

    def _export_objects(self, tilemap: TilemapData, path: Path) -> None:
        """把对象层导出为 JSON（运行时加载更灵活）。"""
        objects = []
        for obj in tilemap.objects:
            entry = {
                "id": obj.id,
                "type": obj.type,
                "x": obj.x,
                "y": obj.y,
                "width": obj.width,
                "height": obj.height,
                "properties": obj.properties,
            }
            if obj.sprite_ref:
                entry["sprite_ref"] = obj.sprite_ref
            if obj.sprite_path:
                entry["sprite_path"] = obj.sprite_path
            objects.append(entry)

        events = []
        for event in tilemap.events:
            events.append({
                "id": event.id,
                "type": event.type,
                "x": event.x,
                "y": event.y,
                "properties": event.properties,
            })

        regions = []
        for region in tilemap.regions:
            regions.append({
                "id": region.id,
                "type": region.type,
                "bounds": region.bounds,
                "center": region.center,
                "access": region.access,
                "priority": region.priority,
            })

        data = {
            "map": {
                "width": tilemap.map.width,
                "height": tilemap.map.height,
                "tile_width": tilemap.map.tile_width,
                "tile_height": tilemap.map.tile_height,
            },
            "objects": objects,
            "events": events,
            "regions": regions,
        }

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_readme(self, path: Path, scene_name: str) -> None:
        """写入 Godot 导入说明。"""
        content = f"""# Godot 4.x 导入说明

## 文件清单

- `tileset.tres`: TileSet 资源
- `{scene_name}.tscn`: 主场景，包含所有 tile layer 和对象层
- `objects.json`: 对象、事件、区域数据（运行时加载）

## 导入步骤

1. 把整个目录复制到 Godot 项目下，例如 `res://maps/`
2. 确保 tileset 引用的 PNG 文件路径正确（相对 res://）
3. 在 Godot 中打开 `{scene_name}.tscn` 即可看到地图

## 运行时使用对象数据

```gdscript
extends Node2D

var objects_data: Dictionary

func _ready() -> void:
    var file := FileAccess.open("res://maps/objects.json", FileAccess.READ)
    objects_data = JSON.parse_string(file.get_as_text())
    _spawn_objects()

func _spawn_objects() -> void:
    for obj in objects_data["objects"]:
        if obj.has("sprite_path"):
            var sprite := Sprite2D.new()
            sprite.texture = load("res://" + obj["sprite_path"])
            sprite.position = Vector2(
                obj["x"] * objects_data["map"]["tile_width"],
                obj["y"] * objects_data["map"]["tile_height"]
            )
            $Objects.add_child(sprite)
```

## 注意事项

- collision 层默认 visible=false，运行时用作物理碰撞参考
- objects/events 层在场景中是 Node2D 占位符，附带 metadata 属性
- 完整对象逻辑请通过 `objects.json` 加载
"""
        path.write_text(content, encoding="utf-8")
