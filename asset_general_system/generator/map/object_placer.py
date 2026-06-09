"""
Object placement helper for map generator.

Integrates generated objects into tilemap generation.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..assets.asset_library import AssetLibrary
    from ..models import ObjectData, TilemapData


class ObjectPlacer:
    """
    Helper for placing generated objects into tilemaps.
    """

    def __init__(self, asset_library: AssetLibrary | None = None):
        """
        Initialize object placer.

        Args:
            asset_library: Optional asset library for sprite lookup
        """
        self.asset_library = asset_library

    def create_object_with_sprite(
        self,
        object_id: str,
        object_type: str,
        x: int,
        y: int,
        properties: dict | None = None,
    ) -> "ObjectData":
        """
        Create ObjectData with sprite reference if available.

        Args:
            object_id: Unique object ID
            object_type: Object type (tree, rock, chest, etc.)
            x: X coordinate in tiles
            y: Y coordinate in tiles
            properties: Optional properties

        Returns:
            ObjectData with sprite_ref and sprite_path if found
        """
        from ..models import ObjectData

        obj = ObjectData(
            id=object_id,
            type=object_type,
            x=x,
            y=y,
            properties=properties or {},
        )

        # Try to find sprite in library
        if self.asset_library:
            # Search by type tag
            matches = self.asset_library.search_by_tags([object_type], use_synonyms=True)
            if matches:
                # Use first match
                asset = matches[0]
                obj.sprite_ref = asset.asset_id
                obj.sprite_path = asset.sprite_path

                # Set width/height from footprint
                if asset.footprint:
                    obj.width = asset.footprint[0]
                    obj.height = asset.footprint[1]

        return obj

    def place_decoration_objects(
        self,
        tilemap: "TilemapData",
        object_type: str,
        positions: list[tuple[int, int]],
        id_prefix: str | None = None,
    ) -> list["ObjectData"]:
        """
        Place multiple decoration objects at specified positions.

        Args:
            tilemap: Tilemap to add objects to
            object_type: Type of object to place
            positions: List of (x, y) positions
            id_prefix: Optional prefix for object IDs

        Returns:
            List of created ObjectData
        """
        prefix = id_prefix or object_type
        objects = []

        for idx, (x, y) in enumerate(positions, start=1):
            obj = self.create_object_with_sprite(
                object_id=f"{prefix}_{idx:02d}",
                object_type=object_type,
                x=x,
                y=y,
            )
            objects.append(obj)
            tilemap.objects.append(obj)

        return objects

    def replace_tile_with_object(
        self,
        tilemap: "TilemapData",
        tile_type: str,
        object_type: str,
        max_replacements: int = -1,
    ) -> int:
        """
        Replace tile-based decorations with proper objects.

        This is useful for converting old tile-based objects (like market_stall
        tiles) into proper ObjectData entries with sprite references.

        Args:
            tilemap: Tilemap to process
            tile_type: Tile type to search for (e.g., "market_stall")
            object_type: Object type to create
            max_replacements: Maximum number to replace, -1 for all

        Returns:
            Number of replacements made
        """
        from ..config import TILE_ID_BY_NAME

        tile_id = TILE_ID_BY_NAME.get(tile_type)
        if not tile_id:
            return 0

        width = tilemap.map.width
        decoration = tilemap.layers.get("decoration", [])

        positions = []
        for y in range(tilemap.map.height):
            for x in range(width):
                idx = y * width + x
                if idx < len(decoration) and decoration[idx] == tile_id:
                    positions.append((x, y))
                    if max_replacements > 0 and len(positions) >= max_replacements:
                        break

        # Create objects
        count = 0
        for x, y in positions:
            # Check if object already exists at this position
            existing = any(obj.x == x and obj.y == y for obj in tilemap.objects)
            if not existing:
                obj = self.create_object_with_sprite(
                    object_id=f"{object_type}_{count + 1:02d}",
                    object_type=object_type,
                    x=x,
                    y=y,
                )
                tilemap.objects.append(obj)
                count += 1

        return count

    def get_missing_object_types(self, tilemap: "TilemapData") -> list[str]:
        """
        Get list of object types in tilemap that don't have sprite references.

        Args:
            tilemap: Tilemap to analyze

        Returns:
            List of object types without sprites
        """
        missing = []
        seen = set()

        for obj in tilemap.objects:
            if not obj.sprite_ref and obj.type not in seen:
                missing.append(obj.type)
                seen.add(obj.type)

        return missing

    def report_object_coverage(self, tilemap: "TilemapData") -> dict:
        """
        Generate a report on object sprite coverage.

        Args:
            tilemap: Tilemap to analyze

        Returns:
            Dictionary with coverage statistics
        """
        total = len(tilemap.objects)
        with_sprite = sum(1 for obj in tilemap.objects if obj.sprite_ref)

        by_type = {}
        for obj in tilemap.objects:
            obj_type = obj.type
            if obj_type not in by_type:
                by_type[obj_type] = {"total": 0, "with_sprite": 0}
            by_type[obj_type]["total"] += 1
            if obj.sprite_ref:
                by_type[obj_type]["with_sprite"] += 1

        return {
            "total_objects": total,
            "with_sprite": with_sprite,
            "without_sprite": total - with_sprite,
            "coverage_percent": (with_sprite / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "missing_types": self.get_missing_object_types(tilemap),
        }
