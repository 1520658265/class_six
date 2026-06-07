from __future__ import annotations

from typing import Any

from pydantic import Field

from ..config import DEFAULT_TILE_SIZE, VERSION
from .base import StrictModel


class MapInfo(StrictModel):
    width: int
    height: int
    tile_width: int = DEFAULT_TILE_SIZE[0]
    tile_height: int = DEFAULT_TILE_SIZE[1]
    orientation: str = "orthogonal"


class TilesetInfo(StrictModel):
    id: str = "default_rpg_32"
    image: str = "tilesets/default_rpg_32.png"
    tile_width: int = DEFAULT_TILE_SIZE[0]
    tile_height: int = DEFAULT_TILE_SIZE[1]
    columns: int = 16
    tile_count: int = 32


class RegionData(StrictModel):
    id: str
    type: str
    bounds: list[int]
    center: list[int]
    access: list[int]
    priority: int = 50


class ObjectData(StrictModel):
    id: str
    type: str
    x: int
    y: int
    width: int = 1
    height: int = 1
    properties: dict[str, Any] = Field(default_factory=dict)
    sprite_ref: str | None = None  # Reference to generated sprite asset_id
    sprite_path: str | None = None  # Path to sprite image file


class TilemapData(StrictModel):
    version: str = VERSION
    map: MapInfo
    tileset: TilesetInfo = Field(default_factory=TilesetInfo)
    layers: dict[str, list[int]]
    objects: list[ObjectData] = Field(default_factory=list)
    events: list[ObjectData] = Field(default_factory=list)
    regions: list[RegionData] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
