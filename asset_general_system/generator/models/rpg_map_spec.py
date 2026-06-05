from __future__ import annotations

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


class EntitySpec(StrictModel):
    id: str | None = None
    type: str
    count: int = Field(default=1, ge=0)
    position: str | None = None
    placement: str | None = None


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
    map: MapConfig
    regions: list[RegionSpec] = Field(default_factory=list)
    paths: list[PathSpec] = Field(default_factory=list)
    objects: list[ObjectSpec] = Field(default_factory=list)
    entities: list[EntitySpec] = Field(default_factory=list)
    constraints: ConstraintsSpec = Field(default_factory=ConstraintsSpec)
    seed: int
    tileset_id: str = "default_rpg_32"
