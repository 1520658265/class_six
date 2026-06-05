from __future__ import annotations

from typing import Any

from pydantic import Field

from ..models.base import StrictModel
from ..models.tilemap_data import TilemapData


class SelectionRect(StrictModel):
    x: int
    y: int
    width: int = Field(gt=0)
    height: int = Field(gt=0)

    @classmethod
    def from_points(cls, x1: int, y1: int, x2: int, y2: int) -> "SelectionRect":
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        return cls(x=left, y=top, width=right - left + 1, height=bottom - top + 1)

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def bounds(self) -> list[int]:
        return [self.x, self.y, self.width, self.height]

    def clamp(self, map_width: int, map_height: int) -> "SelectionRect | None":
        left = max(0, self.x)
        top = max(0, self.y)
        right = min(map_width, self.right)
        bottom = min(map_height, self.bottom)
        if left >= right or top >= bottom:
            return None
        return SelectionRect(x=left, y=top, width=right - left, height=bottom - top)

    def contains(self, x: int, y: int) -> bool:
        return self.x <= x < self.right and self.y <= y < self.bottom

    def intersects(self, other: "SelectionRect") -> bool:
        return self.x < other.right and self.right > other.x and self.y < other.bottom and self.bottom > other.y

    def iter_cells(self):
        for y in range(self.y, self.bottom):
            for x in range(self.x, self.right):
                yield x, y


class LayerVisibility(StrictModel):
    layers: dict[str, bool]

    @classmethod
    def from_layer_names(cls, layer_names: list[str]) -> "LayerVisibility":
        return cls(layers={name: name != "collision" for name in layer_names})

    def is_visible(self, layer_name: str) -> bool:
        self._require_layer(layer_name)
        return self.layers[layer_name]

    def set_visible(self, layer_name: str, visible: bool) -> None:
        self._require_layer(layer_name)
        self.layers[layer_name] = visible

    def toggle(self, layer_name: str) -> bool:
        self._require_layer(layer_name)
        self.layers[layer_name] = not self.layers[layer_name]
        return self.layers[layer_name]

    def _require_layer(self, layer_name: str) -> None:
        if layer_name not in self.layers:
            raise KeyError(f"Unknown layer: {layer_name}")


class LockedRegion(StrictModel):
    id: str
    rect: SelectionRect
    layers: list[str] | None = None
    reason: str = "user_locked"

    def contains(self, x: int, y: int, layer_name: str | None = None) -> bool:
        if layer_name is not None and self.layers is not None and layer_name not in self.layers:
            return False
        return self.rect.contains(x, y)


class EditAction(StrictModel):
    kind: str
    description: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class EditorSnapshot(StrictModel):
    selection: SelectionRect | None = None
    layer_visibility: LayerVisibility
    locked_regions: list[LockedRegion] = Field(default_factory=list)


class HistoryEntry(StrictModel):
    action: EditAction
    before: EditorSnapshot
    after: EditorSnapshot


class EditorState(StrictModel):
    map_width: int = Field(gt=0)
    map_height: int = Field(gt=0)
    tile_width: int = Field(gt=0)
    tile_height: int = Field(gt=0)
    map_id: str | None = None
    layer_visibility: LayerVisibility
    selection: SelectionRect | None = None
    locked_regions: list[LockedRegion] = Field(default_factory=list)
    undo_stack: list[HistoryEntry] = Field(default_factory=list)
    redo_stack: list[HistoryEntry] = Field(default_factory=list)
    max_history: int = Field(default=50, gt=0)

    @classmethod
    def from_tilemap(cls, tilemap: TilemapData, map_id: str | None = None) -> "EditorState":
        inferred_id = map_id or tilemap.metadata.get("id") or tilemap.metadata.get("task_id")
        return cls(
            map_width=tilemap.map.width,
            map_height=tilemap.map.height,
            tile_width=tilemap.map.tile_width,
            tile_height=tilemap.map.tile_height,
            map_id=inferred_id,
            layer_visibility=LayerVisibility.from_layer_names(list(tilemap.layers)),
        )

    def select_rect(self, rect: SelectionRect) -> None:
        before = self._snapshot()
        self.selection = rect.clamp(self.map_width, self.map_height)
        self._record("select", before, {"rect": self.selection.bounds if self.selection else None})

    def clear_selection(self) -> None:
        if self.selection is None:
            return
        before = self._snapshot()
        self.selection = None
        self._record("clear_selection", before, {})

    def set_layer_visible(self, layer_name: str, visible: bool) -> None:
        self.layer_visibility._require_layer(layer_name)
        if self.layer_visibility.layers[layer_name] == visible:
            return
        before = self._snapshot()
        self.layer_visibility.set_visible(layer_name, visible)
        self._record("set_layer_visible", before, {"layer": layer_name, "visible": visible})

    def toggle_layer(self, layer_name: str) -> bool:
        self.layer_visibility._require_layer(layer_name)
        before = self._snapshot()
        visible = self.layer_visibility.toggle(layer_name)
        self._record("toggle_layer", before, {"layer": layer_name, "visible": visible})
        return visible

    def lock_selection(
        self,
        region_id: str | None = None,
        layers: list[str] | None = None,
        reason: str = "user_locked",
    ) -> LockedRegion:
        if self.selection is None:
            raise ValueError("Cannot lock an empty selection.")
        if layers is not None:
            for layer in layers:
                self.layer_visibility._require_layer(layer)
        before = self._snapshot()
        locked = LockedRegion(
            id=region_id or self._next_locked_region_id(),
            rect=self.selection.model_copy(deep=True),
            layers=list(layers) if layers is not None else None,
            reason=reason,
        )
        self.locked_regions.append(locked)
        self._record("lock_selection", before, {"id": locked.id, "bounds": locked.rect.bounds})
        return locked

    def unlock_region(self, region_id: str) -> bool:
        kept = [region for region in self.locked_regions if region.id != region_id]
        if len(kept) == len(self.locked_regions):
            return False
        before = self._snapshot()
        self.locked_regions = kept
        self._record("unlock_region", before, {"id": region_id})
        return True

    def is_locked(self, x: int, y: int, layer_name: str | None = None) -> bool:
        return any(region.contains(x, y, layer_name) for region in self.locked_regions)

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        entry = self.undo_stack.pop()
        self._apply_snapshot(entry.before)
        self.redo_stack.append(entry)
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        entry = self.redo_stack.pop()
        self._apply_snapshot(entry.after)
        self.undo_stack.append(entry)
        return True

    def _record(self, kind: str, before: EditorSnapshot, payload: dict[str, Any]) -> None:
        after = self._snapshot()
        if before == after:
            return
        entry = HistoryEntry(
            action=EditAction(kind=kind, payload=payload),
            before=before,
            after=after,
        )
        self.undo_stack.append(entry)
        if len(self.undo_stack) > self.max_history:
            self.undo_stack = self.undo_stack[-self.max_history :]
        self.redo_stack.clear()

    def _snapshot(self) -> EditorSnapshot:
        return EditorSnapshot(
            selection=self.selection.model_copy(deep=True) if self.selection else None,
            layer_visibility=self.layer_visibility.model_copy(deep=True),
            locked_regions=[region.model_copy(deep=True) for region in self.locked_regions],
        )

    def _apply_snapshot(self, snapshot: EditorSnapshot) -> None:
        self.selection = snapshot.selection.model_copy(deep=True) if snapshot.selection else None
        self.layer_visibility = snapshot.layer_visibility.model_copy(deep=True)
        self.locked_regions = [region.model_copy(deep=True) for region in snapshot.locked_regions]

    def _next_locked_region_id(self) -> str:
        existing = {region.id for region in self.locked_regions}
        index = len(existing) + 1
        candidate = f"locked_{index:03d}"
        while candidate in existing:
            index += 1
            candidate = f"locked_{index:03d}"
        return candidate
