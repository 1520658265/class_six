from __future__ import annotations

from pydantic import Field

from ..config import DEFAULT_MAP_SIZE, DEFAULT_TILESET_ID, DEFAULT_TILE_SIZE
from .base import StrictModel


class GenerateRequest(StrictModel):
    prompt: str = Field(min_length=1)
    theme: str | None = None
    map_size: tuple[int, int] = DEFAULT_MAP_SIZE
    tile_size: tuple[int, int] = DEFAULT_TILE_SIZE
    seed: int | None = None
    tileset_id: str = DEFAULT_TILESET_ID
