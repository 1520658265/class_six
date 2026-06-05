from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from ..models import ValidationIssue, ValidationReport


REQUIRED_TILE_LAYERS = ("terrain", "path", "building", "decoration", "collision")
REQUIRED_OBJECT_LAYERS = ("objects", "events")


class TiledJsonValidator:
    def validate(self, tiled: dict[str, Any]) -> ValidationReport:
        errors: list[ValidationIssue] = []
        warnings: list[ValidationIssue] = []

        width = self._int_field(tiled, "width", errors)
        height = self._int_field(tiled, "height", errors)
        tile_width = self._int_field(tiled, "tilewidth", errors)
        tile_height = self._int_field(tiled, "tileheight", errors)
        if tiled.get("type") != "map":
            errors.append(ValidationIssue(code="TILED_MAP_TYPE", message="Tiled JSON top-level type must be 'map'."))
        if tiled.get("orientation") != "orthogonal":
            errors.append(ValidationIssue(code="TILED_ORIENTATION", message="Tiled JSON orientation must be 'orthogonal'."))

        layers = tiled.get("layers")
        if not isinstance(layers, list) or not layers:
            errors.append(ValidationIssue(code="TILED_LAYERS", message="Tiled JSON must contain non-empty layers array."))
            layers = []
        layer_names = {layer.get("name") for layer in layers if isinstance(layer, dict)}
        for name in REQUIRED_TILE_LAYERS + REQUIRED_OBJECT_LAYERS:
            if name not in layer_names:
                errors.append(ValidationIssue(code="TILED_REQUIRED_LAYER", message=f"Missing required Tiled layer: {name}.", target=name))

        max_gid = self._max_gid(tiled, errors)
        layer_ids: set[int] = set()
        object_ids: set[int] = set()
        for layer in layers:
            if not isinstance(layer, dict):
                errors.append(ValidationIssue(code="TILED_LAYER_OBJECT", message="Each Tiled layer must be an object."))
                continue
            layer_id = layer.get("id")
            if not isinstance(layer_id, int) or layer_id <= 0:
                errors.append(ValidationIssue(code="TILED_LAYER_ID", message=f"Layer {layer.get('name')} has invalid id."))
            elif layer_id in layer_ids:
                errors.append(ValidationIssue(code="TILED_LAYER_ID_UNIQUE", message=f"Duplicate layer id: {layer_id}."))
            else:
                layer_ids.add(layer_id)

            if layer.get("type") == "tilelayer":
                self._validate_tile_layer(layer, width, height, max_gid, errors)
            elif layer.get("type") == "objectgroup":
                self._validate_object_layer(layer, tile_width, tile_height, object_ids, errors)
            else:
                errors.append(
                    ValidationIssue(
                        code="TILED_LAYER_TYPE",
                        message=f"Layer {layer.get('name')} has unsupported type {layer.get('type')}.",
                        target=str(layer.get("name")),
                    )
                )

        next_layer_id = tiled.get("nextlayerid")
        if isinstance(next_layer_id, int) and layer_ids and next_layer_id <= max(layer_ids):
            errors.append(ValidationIssue(code="TILED_NEXT_LAYER_ID", message="nextlayerid must be greater than existing layer ids."))
        next_object_id = tiled.get("nextobjectid")
        if isinstance(next_object_id, int) and object_ids and next_object_id <= max(object_ids):
            errors.append(ValidationIssue(code="TILED_NEXT_OBJECT_ID", message="nextobjectid must be greater than existing object ids."))

        collision_layer = next((layer for layer in layers if isinstance(layer, dict) and layer.get("name") == "collision"), None)
        if collision_layer and collision_layer.get("visible") is not False:
            warnings.append(
                ValidationIssue(
                    code="TILED_COLLISION_VISIBLE",
                    severity="warning",
                    message="Collision layer should be hidden by default.",
                    target="collision",
                )
            )

        return ValidationReport(
            passed=not errors,
            errors=errors,
            warnings=warnings,
            metrics={
                "layer_count": len(layers),
                "tile_layer_count": sum(1 for layer in layers if isinstance(layer, dict) and layer.get("type") == "tilelayer"),
                "object_layer_count": sum(1 for layer in layers if isinstance(layer, dict) and layer.get("type") == "objectgroup"),
                "tileset_count": len(tiled.get("tilesets", [])) if isinstance(tiled.get("tilesets"), list) else 0,
                "object_count": len(object_ids),
                "max_gid": max_gid,
            },
        )

    def _validate_tile_layer(self, layer: dict[str, Any], width: int, height: int, max_gid: int, errors: list[ValidationIssue]) -> None:
        name = str(layer.get("name"))
        if layer.get("width") != width or layer.get("height") != height:
            errors.append(ValidationIssue(code="TILED_LAYER_SIZE", message=f"Tile layer {name} size does not match map size.", target=name))
        data = layer.get("data")
        if not isinstance(data, list):
            errors.append(ValidationIssue(code="TILED_LAYER_DATA", message=f"Tile layer {name} data must be an array.", target=name))
            return
        expected = width * height
        if len(data) != expected:
            errors.append(
                ValidationIssue(
                    code="TILED_LAYER_DATA_LENGTH",
                    message=f"Tile layer {name} data length is {len(data)}, expected {expected}.",
                    target=name,
                )
            )
        for index, gid in enumerate(data):
            if not isinstance(gid, int) or gid < 0:
                errors.append(
                    ValidationIssue(
                        code="TILED_GID",
                        message=f"Tile layer {name} contains invalid gid at index {index}: {gid}.",
                        target=name,
                    )
                )
                return
            if max_gid and gid > max_gid:
                errors.append(
                    ValidationIssue(
                        code="TILED_GID_RANGE",
                        message=f"Tile layer {name} gid {gid} exceeds max tileset gid {max_gid}.",
                        target=name,
                    )
                )
                return

    def _validate_object_layer(
        self,
        layer: dict[str, Any],
        tile_width: int,
        tile_height: int,
        object_ids: set[int],
        errors: list[ValidationIssue],
    ) -> None:
        objects = layer.get("objects")
        if not isinstance(objects, list):
            errors.append(ValidationIssue(code="TILED_OBJECTS", message=f"Object layer {layer.get('name')} objects must be an array."))
            return
        for obj in objects:
            if not isinstance(obj, dict):
                errors.append(ValidationIssue(code="TILED_OBJECT", message=f"Object layer {layer.get('name')} contains a non-object entry."))
                continue
            object_id = obj.get("id")
            if not isinstance(object_id, int) or object_id <= 0:
                errors.append(ValidationIssue(code="TILED_OBJECT_ID", message=f"Object {obj.get('name')} has invalid id."))
            elif object_id in object_ids:
                errors.append(ValidationIssue(code="TILED_OBJECT_ID_UNIQUE", message=f"Duplicate object id: {object_id}."))
            else:
                object_ids.add(object_id)
            for key in ("x", "y", "width", "height"):
                if not isinstance(obj.get(key), (int, float)) or obj[key] < 0:
                    errors.append(ValidationIssue(code="TILED_OBJECT_COORD", message=f"Object {obj.get('name')} has invalid {key}."))
            if tile_width <= 0 or tile_height <= 0:
                errors.append(ValidationIssue(code="TILED_TILE_SIZE", message="tilewidth and tileheight must be positive."))

    def _max_gid(self, tiled: dict[str, Any], errors: list[ValidationIssue]) -> int:
        tilesets = tiled.get("tilesets")
        if not isinstance(tilesets, list) or not tilesets:
            errors.append(ValidationIssue(code="TILED_TILESETS", message="Tiled JSON must contain at least one tileset."))
            return 0
        max_gid = 0
        for tileset in tilesets:
            if not isinstance(tileset, dict):
                errors.append(ValidationIssue(code="TILED_TILESET", message="Each tileset must be an object."))
                continue
            firstgid = tileset.get("firstgid")
            tilecount = tileset.get("tilecount")
            if not isinstance(firstgid, int) or firstgid <= 0:
                errors.append(ValidationIssue(code="TILED_TILESET_FIRSTGID", message="Tileset firstgid must be a positive integer."))
                continue
            if not isinstance(tilecount, int) or tilecount <= 0:
                errors.append(ValidationIssue(code="TILED_TILESET_TILECOUNT", message="Tileset tilecount must be a positive integer."))
                continue
            image = tileset.get("image")
            if not isinstance(image, str) or not image:
                errors.append(ValidationIssue(code="TILED_TILESET_IMAGE", message="Tileset image must be a relative path string."))
            elif self._is_absolute_path(image):
                errors.append(ValidationIssue(code="TILED_TILESET_IMAGE_RELATIVE", message="Tileset image path must be relative."))
            max_gid = max(max_gid, firstgid + tilecount - 1)
        return max_gid

    def _int_field(self, tiled: dict[str, Any], field: str, errors: list[ValidationIssue]) -> int:
        value = tiled.get(field)
        if not isinstance(value, int) or value <= 0:
            errors.append(ValidationIssue(code="TILED_INT_FIELD", message=f"Tiled JSON field {field} must be a positive integer."))
            return 0
        return value

    def _is_absolute_path(self, value: str) -> bool:
        return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()

