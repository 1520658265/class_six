from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.base import read_json
from ..models.tilemap_data import MapInfo, ObjectData, RegionData, TilemapData, TilesetInfo


class TiledImporter:
    def import_file(self, path: str | Path) -> TilemapData:
        return self.from_dict(read_json(path), source_path=str(path))

    def from_dict(self, data: dict[str, Any], source_path: str | None = None) -> TilemapData:
        if data.get("type") != "map":
            raise ValueError("Tiled JSON root type must be 'map'.")
        width = int(data["width"])
        height = int(data["height"])
        tile_width = int(data["tilewidth"])
        tile_height = int(data["tileheight"])
        layer_by_name = {layer["name"]: layer for layer in data.get("layers", [])}
        required = ["terrain", "path", "building", "decoration", "collision"]
        missing = [name for name in required if name not in layer_by_name]
        if missing:
            raise ValueError(f"Tiled JSON is missing tile layers: {missing}")

        layers = {}
        expected = width * height
        for name in required:
            layer = layer_by_name[name]
            values = [int(value) for value in layer.get("data", [])]
            if len(values) != expected:
                raise ValueError(f"Layer {name} has {len(values)} tiles; expected {expected}.")
            layers[name] = values

        tileset_data = (data.get("tilesets") or [{}])[0]
        tileset = TilesetInfo(
            id=str(tileset_data.get("name", "default_rpg_32")),
            image=str(tileset_data.get("image", "tilesets/default_rpg_32.png")),
            tile_width=int(tileset_data.get("tilewidth", tile_width)),
            tile_height=int(tileset_data.get("tileheight", tile_height)),
            columns=int(tileset_data.get("columns", 16)),
            tile_count=int(tileset_data.get("tilecount", 32)),
        )

        objects = self._objects_from_layer(layer_by_name.get("objects"), tile_width, tile_height)
        events = self._objects_from_layer(layer_by_name.get("events"), tile_width, tile_height)
        regions = self._regions_from_events(events)
        metadata = self._metadata_from_properties(data.get("properties", []))
        if source_path:
            metadata["imported_from_tiled_json"] = source_path

        return TilemapData(
            map=MapInfo(width=width, height=height, tile_width=tile_width, tile_height=tile_height),
            tileset=tileset,
            layers=layers,
            objects=objects,
            events=events,
            regions=regions,
            metadata=metadata,
        )

    def _objects_from_layer(self, layer: dict[str, Any] | None, tile_width: int, tile_height: int) -> list[ObjectData]:
        if not layer:
            return []
        result = []
        for item in layer.get("objects", []):
            properties = self._metadata_from_properties(item.get("properties", []))
            result.append(
                ObjectData(
                    id=str(item.get("name") or f"object_{item.get('id', len(result) + 1)}"),
                    type=str(item.get("type", "")),
                    x=round(float(item.get("x", 0)) / tile_width),
                    y=round(float(item.get("y", 0)) / tile_height),
                    width=max(1, round(float(item.get("width", tile_width)) / tile_width)),
                    height=max(1, round(float(item.get("height", tile_height)) / tile_height)),
                    properties=properties,
                )
            )
        return result

    def _regions_from_events(self, events: list[ObjectData]) -> list[RegionData]:
        regions = []
        for event in events:
            if event.type != "area_marker":
                continue
            region_id = str(event.properties.get("region", event.id.removesuffix("_marker")))
            region_type = str(event.properties.get("region_type", "area"))
            regions.append(
                RegionData(
                    id=region_id,
                    type=region_type,
                    bounds=[event.x, event.y, 1, 1],
                    center=[event.x, event.y],
                    access=[event.x, event.y],
                    priority=50,
                )
            )
        return regions

    def _metadata_from_properties(self, properties: list[dict[str, Any]]) -> dict[str, Any]:
        result = {}
        for item in properties:
            name = item.get("name")
            if name:
                result[str(name)] = item.get("value")
        return result
