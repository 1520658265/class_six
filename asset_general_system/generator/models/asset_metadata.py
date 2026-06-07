"""
Asset metadata models for object sprites and other game assets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class AssetKind(str, Enum):
    """Asset type enumeration."""
    TILE = "tile"
    TILE_OBJECT = "tile_object"
    SPRITE_SHEET = "sprite_sheet"
    VFX = "vfx"


class AssetSourceType(str, Enum):
    """Asset source type."""
    GENERATED = "generated"
    UPLOADED = "uploaded"
    BUILTIN = "builtin"
    THIRD_PARTY = "third_party"


class AnchorPoint(str, Enum):
    """Visual anchor point for sprite placement."""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    FEET_CENTER = "feet_center"


@dataclass
class VisualBounds:
    """Actual pixel bounding box within sprite, for rendering optimization."""
    x: int
    y: int
    width: int
    height: int


@dataclass
class GenerationMetadata:
    """Metadata for AI-generated assets."""
    timestamp: str
    generator: str
    prompt: str
    seed: int
    model: str


@dataclass
class SourceMetadata:
    """Source and licensing information."""
    type: AssetSourceType
    attribution: str | None = None
    license: str | None = None
    url: str | None = None


@dataclass
class AssetMetadata:
    """
    Complete metadata for a single asset (tile, object, sprite sheet, or VFX).

    Attributes:
        asset_id: Unique identifier, e.g., 'tree_oak_01'
        kind: Asset type
        tags: Semantic tags for search, e.g., ['tree', 'forest', 'blocking']
        tile_size: Base tile size [width, height], e.g., [32, 32]
        theme: Compatible themes, e.g., ['forest', 'village']
        footprint: Occupied grid size [columns, rows], e.g., [1, 2]
        collision: Collision cells in footprint coords, e.g., [[0, 1]]
        anchor: Visual anchor point
        visual_bounds: Actual pixel bounding box
        sprite_path: Relative path to PNG
        metadata_path: Relative path to this JSON
        generated: Generation metadata if AI-generated
        source: Source and licensing info
    """
    asset_id: str
    kind: AssetKind
    tags: list[str]
    tile_size: tuple[int, int]
    theme: list[str] = field(default_factory=list)
    footprint: tuple[int, int] | None = None
    collision: list[tuple[int, int]] = field(default_factory=list)
    anchor: AnchorPoint = AnchorPoint.BOTTOM_CENTER
    visual_bounds: VisualBounds | None = None
    sprite_path: str | None = None
    metadata_path: str | None = None
    generated: GenerationMetadata | None = None
    source: SourceMetadata | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "asset_id": self.asset_id,
            "kind": self.kind.value,
            "tags": self.tags,
            "tile_size": list(self.tile_size),
        }

        if self.theme:
            result["theme"] = self.theme

        if self.footprint:
            result["footprint"] = list(self.footprint)

        if self.collision:
            result["collision"] = [list(c) for c in self.collision]

        result["anchor"] = self.anchor.value

        if self.visual_bounds:
            result["visual_bounds"] = {
                "x": self.visual_bounds.x,
                "y": self.visual_bounds.y,
                "width": self.visual_bounds.width,
                "height": self.visual_bounds.height,
            }

        if self.sprite_path:
            result["sprite_path"] = self.sprite_path

        if self.metadata_path:
            result["metadata_path"] = self.metadata_path

        if self.generated:
            result["generated"] = {
                "timestamp": self.generated.timestamp,
                "generator": self.generated.generator,
                "prompt": self.generated.prompt,
                "seed": self.generated.seed,
                "model": self.generated.model,
            }

        if self.source:
            source_dict = {"type": self.source.type.value}
            if self.source.attribution:
                source_dict["attribution"] = self.source.attribution
            if self.source.license:
                source_dict["license"] = self.source.license
            if self.source.url:
                source_dict["url"] = self.source.url
            result["source"] = source_dict

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetMetadata:
        """Load from JSON dict."""
        kwargs: dict[str, Any] = {
            "asset_id": data["asset_id"],
            "kind": AssetKind(data["kind"]),
            "tags": data["tags"],
            "tile_size": tuple(data["tile_size"]),
        }

        if "theme" in data:
            kwargs["theme"] = data["theme"]

        if "footprint" in data:
            kwargs["footprint"] = tuple(data["footprint"])

        if "collision" in data:
            kwargs["collision"] = [tuple(c) for c in data["collision"]]

        if "anchor" in data:
            kwargs["anchor"] = AnchorPoint(data["anchor"])

        if "visual_bounds" in data:
            vb = data["visual_bounds"]
            kwargs["visual_bounds"] = VisualBounds(
                x=vb["x"], y=vb["y"], width=vb["width"], height=vb["height"]
            )

        if "sprite_path" in data:
            kwargs["sprite_path"] = data["sprite_path"]

        if "metadata_path" in data:
            kwargs["metadata_path"] = data["metadata_path"]

        if "generated" in data:
            g = data["generated"]
            kwargs["generated"] = GenerationMetadata(
                timestamp=g["timestamp"],
                generator=g["generator"],
                prompt=g["prompt"],
                seed=g["seed"],
                model=g["model"],
            )

        if "source" in data:
            s = data["source"]
            kwargs["source"] = SourceMetadata(
                type=AssetSourceType(s["type"]),
                attribution=s.get("attribution"),
                license=s.get("license"),
                url=s.get("url"),
            )

        return cls(**kwargs)
