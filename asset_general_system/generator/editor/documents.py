from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from ..config import VERSION
from ..models.base import StrictModel
from ..models.reports import ValidationIssue, ValidationReport
from ..models.tilemap_data import TilemapData
from .state import LockedRegion, SelectionRect


class EditorMapDocument(StrictModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    tile_width: int = Field(gt=0)
    tile_height: int = Field(gt=0)


class EditorLockedRegionDocument(StrictModel):
    id: str
    x: int
    y: int
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    layers: list[str] | None = None
    reason: str = "user_locked"

    @property
    def rect(self) -> SelectionRect:
        return SelectionRect(x=self.x, y=self.y, width=self.width, height=self.height)

    def to_locked_region(self) -> LockedRegion:
        return LockedRegion(id=self.id, rect=self.rect, layers=self.layers, reason=self.reason)


class EditorStateDocument(StrictModel):
    version: str = VERSION
    source_file: str | None = None
    map: EditorMapDocument
    layer_visibility: dict[str, bool]
    selection: SelectionRect | None = None
    locked_regions: list[EditorLockedRegionDocument] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_bounds_and_layers(self) -> "EditorStateDocument":
        known_layers = set(self.layer_visibility)
        if self.selection and self.selection.clamp(self.map.width, self.map.height) != self.selection:
            raise ValueError("selection is outside map bounds")
        for region in self.locked_regions:
            if region.rect.clamp(self.map.width, self.map.height) != region.rect:
                raise ValueError(f"locked region {region.id} is outside map bounds")
            if region.layers:
                unknown = sorted(set(region.layers) - known_layers)
                if unknown:
                    raise ValueError(f"locked region {region.id} references unknown layers: {unknown}")
        return self

    @classmethod
    def from_tilemap(cls, tilemap: TilemapData, source_file: str | None = None) -> "EditorStateDocument":
        layers = {name: name != "collision" for name in tilemap.layers}
        return cls(
            source_file=source_file,
            map=EditorMapDocument(
                width=tilemap.map.width,
                height=tilemap.map.height,
                tile_width=tilemap.map.tile_width,
                tile_height=tilemap.map.tile_height,
            ),
            layer_visibility=layers,
        )

    def locked_regions_for_runtime(self) -> list[LockedRegion]:
        return [region.to_locked_region() for region in self.locked_regions]


def validate_editor_state_document(
    editor_state: EditorStateDocument,
    tilemap: TilemapData | None = None,
) -> ValidationReport:
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    if tilemap:
        if editor_state.map.width != tilemap.map.width or editor_state.map.height != tilemap.map.height:
            errors.append(
                ValidationIssue(
                    code="EDITOR_STATE_MAP_SIZE_MISMATCH",
                    message="Editor state map size does not match map_data.json.",
                )
            )
        if editor_state.map.tile_width != tilemap.map.tile_width or editor_state.map.tile_height != tilemap.map.tile_height:
            errors.append(
                ValidationIssue(
                    code="EDITOR_STATE_TILE_SIZE_MISMATCH",
                    message="Editor state tile size does not match map_data.json.",
                )
            )
        missing_layers = sorted(set(tilemap.layers) - set(editor_state.layer_visibility))
        unknown_layers = sorted(set(editor_state.layer_visibility) - set(tilemap.layers))
        if missing_layers:
            warnings.append(
                ValidationIssue(
                    code="EDITOR_STATE_LAYER_VISIBILITY_MISSING",
                    severity="warning",
                    message=f"Editor state does not include visibility for layers: {missing_layers}",
                )
            )
        if unknown_layers:
            errors.append(
                ValidationIssue(
                    code="EDITOR_STATE_UNKNOWN_LAYER",
                    message=f"Editor state references unknown layers: {unknown_layers}",
                )
            )

    return ValidationReport(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        metrics={
            "locked_region_count": len(editor_state.locked_regions),
            "has_selection": editor_state.selection is not None,
            "visible_layer_count": sum(1 for value in editor_state.layer_visibility.values() if value),
        },
    )
