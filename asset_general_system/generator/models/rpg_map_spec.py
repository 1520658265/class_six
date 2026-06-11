from __future__ import annotations

from typing import Any

from pydantic import Field

from ..config import DEFAULT_TILE_SIZE, VERSION
from .base import StrictModel


class MapConfig(StrictModel):
    width: int = Field(default=64, ge=16, le=256)
    height: int = Field(default=64, ge=16, le=256)
    tile_width: int = Field(default=DEFAULT_TILE_SIZE[0], ge=8, le=128)
    tile_height: int = Field(default=DEFAULT_TILE_SIZE[1], ge=8, le=128)
    orientation: str = "orthogonal"


class RegionSpec(StrictModel):
    id: str
    type: str
    position: str = "random"
    size: str = "medium"
    priority: int = 50


class PathSpec(StrictModel):
    from_id: str = Field(alias="from")
    to: str
    kind: str = "dirt_road"


class ObjectSpec(StrictModel):
    type: str
    count: int = Field(default=1, ge=0)
    placement: str = "random"
    label: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class EntitySpec(StrictModel):
    id: str | None = None
    type: str
    count: int = Field(default=1, ge=0)
    position: str | None = None
    placement: str | None = None


class BaseTerrainSpec(StrictModel):
    object_key: str
    display_name: str
    tile: str = "grass"
    source_clause: str | None = None
    source_canvas: list[int] = Field(default_factory=lambda: [32, 32])
    properties: dict[str, Any] = Field(default_factory=dict)


class CompositePartSpec(StrictModel):
    key: str
    display_name: str
    source_clause: str | None = None
    source_canvas: list[int] = Field(default_factory=lambda: [32, 32])
    blocking: bool = False
    properties: dict[str, Any] = Field(default_factory=dict)


class CompositeLayoutCellSpec(StrictModel):
    part: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)


class CompositeSpec(StrictModel):
    id: str
    type: str
    placement: str
    display_name: str
    footprint: list[int]
    source_clause: str | None = None
    parts: list[CompositePartSpec]
    layout: list[CompositeLayoutCellSpec]
    properties: dict[str, Any] = Field(default_factory=dict)


class TileGroupMemberSpec(StrictModel):
    tile_id: str
    role: str
    source_ref: str | None = None
    display_name: str | None = None
    notes: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class TileGroupSpec(StrictModel):
    group_id: str
    kind: str
    generation_mode: str = "sprite_sheet"
    tile_size: list[int] = Field(default_factory=lambda: [64, 64])
    from_material: str | None = Field(default=None, alias="from")
    to: str | None = None
    display_name: str | None = None
    prompt: str | None = None
    members: list[TileGroupMemberSpec] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class ConstraintsSpec(StrictModel):
    walkable_spawn: bool = True
    connect_key_regions: bool = True
    no_blocked_doors: bool = True
    objects_require_walkable_neighbor: bool = True


class RPGMapSpec(StrictModel):
    version: str = VERSION
    id: str
    title: str
    theme: str
    art_tile_size: int | None = Field(default=None, ge=8, le=256)
    map: MapConfig
    regions: list[RegionSpec] = Field(default_factory=list)
    paths: list[PathSpec] = Field(default_factory=list)
    objects: list[ObjectSpec] = Field(default_factory=list)
    base_terrain: BaseTerrainSpec | None = None
    composites: list[CompositeSpec] = Field(default_factory=list)
    tile_groups: list[TileGroupSpec] = Field(default_factory=list)
    entities: list[EntitySpec] = Field(default_factory=list)
    constraints: ConstraintsSpec = Field(default_factory=ConstraintsSpec)
    seed: int
    tileset_id: str = "default_rpg_32"
