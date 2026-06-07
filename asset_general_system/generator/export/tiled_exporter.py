from __future__ import annotations

from pathlib import Path

from ..models import TilemapData
from ..models.base import write_json


class TiledExporter:
    def export(self, tilemap: TilemapData, output_path: str | Path) -> dict:
        data = self.to_dict(tilemap)
        write_json(output_path, data)
        return data

    def to_dict(self, tilemap: TilemapData) -> dict:
        width = tilemap.map.width
        height = tilemap.map.height
        tile_width = tilemap.map.tile_width
        tile_height = tilemap.map.tile_height
        layers = []
        layer_id = 1
        for name in ("terrain", "path", "building", "decoration", "collision"):
            layers.append(
                {
                    "id": layer_id,
                    "name": name,
                    "type": "tilelayer",
                    "x": 0,
                    "y": 0,
                    "width": width,
                    "height": height,
                    "opacity": 1,
                    "visible": name != "collision",
                    "data": tilemap.layers[name],
                    "properties": [{"name": "semantic", "type": "string", "value": name}],
                }
            )
            layer_id += 1

        objects, next_object_id = self._object_layer(tilemap.objects, tilemap, 1)
        layers.append(
            {
                "id": layer_id,
                "name": "objects",
                "type": "objectgroup",
                "x": 0,
                "y": 0,
                "opacity": 1,
                "visible": True,
                "objects": objects,
            }
        )
        layer_id += 1

        events, next_object_id = self._object_layer(tilemap.events, tilemap, next_object_id)
        layers.append(
            {
                "id": layer_id,
                "name": "events",
                "type": "objectgroup",
                "x": 0,
                "y": 0,
                "opacity": 1,
                "visible": True,
                "objects": events,
            }
        )
        layer_id += 1

        return {
            "type": "map",
            "version": "1.10",
            "tiledversion": "1.11.0",
            "orientation": tilemap.map.orientation,
            "renderorder": "right-down",
            "width": width,
            "height": height,
            "tilewidth": tile_width,
            "tileheight": tile_height,
            "infinite": False,
            "nextlayerid": layer_id,
            "nextobjectid": next_object_id,
            "layers": layers,
            "tilesets": [
                {
                    "firstgid": 1,
                    "name": tilemap.tileset.id,
                    "image": tilemap.tileset.image,
                    "imagewidth": tilemap.tileset.columns * tile_width,
                    "imageheight": ((tilemap.tileset.tile_count + tilemap.tileset.columns - 1) // tilemap.tileset.columns) * tile_height,
                    "tilewidth": tile_width,
                    "tileheight": tile_height,
                    "columns": tilemap.tileset.columns,
                    "tilecount": tilemap.tileset.tile_count,
                    "margin": 0,
                    "spacing": 0,
                }
            ],
            "properties": [
                {"name": "theme", "type": "string", "value": str(tilemap.metadata.get("theme", ""))},
                {"name": "seed", "type": "int", "value": int(tilemap.metadata.get("seed", 0))},
            ],
        }

    def _object_layer(self, objects, tilemap: TilemapData, start_id: int) -> tuple[list[dict], int]:
        result = []
        object_id = start_id
        for obj in objects:
            properties = [
                {"name": key, "type": self._property_type(value), "value": value}
                for key, value in sorted(obj.properties.items())
                if isinstance(value, (str, int, float, bool))
            ]

            # 写入 sprite 引用信息，供 Tiled 和运行时识别
            if obj.sprite_ref:
                properties.append({"name": "sprite_ref", "type": "string", "value": obj.sprite_ref})
            if obj.sprite_path:
                properties.append({"name": "sprite_path", "type": "string", "value": obj.sprite_path})

            result.append(
                {
                    "id": object_id,
                    "name": obj.id,
                    "type": obj.type,
                    "x": obj.x * tilemap.map.tile_width,
                    "y": obj.y * tilemap.map.tile_height,
                    "width": obj.width * tilemap.map.tile_width,
                    "height": obj.height * tilemap.map.tile_height,
                    "visible": True,
                    "properties": properties,
                }
            )
            object_id += 1
        return result, object_id

    def _property_type(self, value) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        return "string"
