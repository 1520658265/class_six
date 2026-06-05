import pytest

from generator.editor import EditorState, SelectionRect
from generator.models import MapInfo, TilemapData


def _tilemap() -> TilemapData:
    return TilemapData(
        map=MapInfo(width=4, height=3),
        layers={
            "terrain": [1] * 12,
            "path": [0] * 12,
            "collision": [0] * 12,
        },
    )


def test_selection_rect_from_points_clamps_and_iterates_cells():
    rect = SelectionRect.from_points(5, 4, 2, 1)
    assert rect.bounds == [2, 1, 4, 4]

    clamped = rect.clamp(map_width=4, map_height=3)

    assert clamped is not None
    assert clamped.bounds == [2, 1, 2, 2]
    assert clamped.contains(3, 2)
    assert not clamped.contains(4, 2)
    assert list(clamped.iter_cells()) == [(2, 1), (3, 1), (2, 2), (3, 2)]


def test_layer_visibility_defaults_collision_hidden_and_toggles_layers():
    state = EditorState.from_tilemap(_tilemap())

    assert state.layer_visibility.is_visible("terrain")
    assert state.layer_visibility.is_visible("path")
    assert not state.layer_visibility.is_visible("collision")

    state.set_layer_visible("path", False)
    assert not state.layer_visibility.is_visible("path")
    assert state.toggle_layer("path") is True

    with pytest.raises(KeyError):
        state.toggle_layer("unknown")


def test_lock_and_unlock_selected_area():
    state = EditorState.from_tilemap(_tilemap())
    state.select_rect(SelectionRect.from_points(-2, -1, 1, 1))

    locked = state.lock_selection("terrain_lock", layers=["terrain"])

    assert locked.rect.bounds == [0, 0, 2, 2]
    assert state.is_locked(1, 1, "terrain")
    assert not state.is_locked(1, 1, "path")
    assert state.unlock_region("terrain_lock") is True
    assert not state.is_locked(1, 1, "terrain")
    assert state.unlock_region("missing") is False


def test_editor_state_undo_and_redo_restores_edit_state():
    state = EditorState.from_tilemap(_tilemap())
    state.select_rect(SelectionRect.from_points(0, 0, 1, 1))
    state.lock_selection("lock_a")
    state.set_layer_visible("path", False)

    assert state.selection is not None
    assert len(state.locked_regions) == 1
    assert not state.layer_visibility.is_visible("path")

    assert state.undo() is True
    assert state.layer_visibility.is_visible("path")
    assert len(state.locked_regions) == 1

    assert state.undo() is True
    assert state.locked_regions == []
    assert state.selection is not None

    assert state.undo() is True
    assert state.selection is None
    assert state.undo() is False

    assert state.redo() is True
    assert state.selection is not None
    assert state.redo() is True
    assert len(state.locked_regions) == 1
