# Phase 3 Editor Preview Baseline

Updated: 2026-06-05

## 1. Current Scope

This baseline covers the Phase 3 work that does not depend on the local Tiled editor.

Completed in this pass:

- Internal editor state model for selection, layer visibility, locked regions, and undo/redo.
- Local browser preview that reads an existing `map_data.json` with a file picker.
- Layer show/hide controls.
- Object, event, and region overlays.
- Drag selection on the map canvas.
- Lock selected area and export editor state JSON.

Not included yet:

- Opening generated maps in the real Tiled editor.
- Editing tile values and writing back `map_data.json`.
- Calling the generator for partial regeneration.
- Real tileset image rendering in the browser.
- Server-side Web editor/API.

## 2. Python Editor State

Module:

```text
generator/editor/
  __init__.py
  state.py
```

Core models:

- `SelectionRect`: normalized tile rectangle with clamp, contains, intersects, and cell iteration helpers.
- `LayerVisibility`: visibility flags keyed by tile layer name.
- `LockedRegion`: locked rectangle, optionally scoped to specific layers.
- `EditorState`: map-level edit state with selection, layer visibility, locked regions, undo, and redo.
- `HistoryEntry`: before/after snapshot for reversible state edits.

The state model only depends on `TilemapData`, so it can be used by CLI tools, tests, and future Web/API layers.

## 3. Local Preview

Files:

```text
editor_preview/
  index.html
  style.css
  app.js
```

Usage:

1. Open `editor_preview/index.html` in a browser.
2. Choose any generated `map_data.json`, for example:

```text
examples/outputs/autumn_village/map_data.json
```

The preview currently uses the same debug color mapping as the Python preview renderer. This is expected for the current stage because the project still uses a fixed debug tileset.

## 4. Editor State Export

The preview can export a JSON file shaped for future partial regeneration:

```json
{
  "version": "0.1.0",
  "source_file": "map_data.json",
  "map": {
    "width": 64,
    "height": 64,
    "tile_width": 32,
    "tile_height": 32
  },
  "layer_visibility": {
    "terrain": true,
    "path": true,
    "building": true,
    "decoration": true,
    "collision": false
  },
  "selection": {
    "x": 10,
    "y": 12,
    "width": 8,
    "height": 6
  },
  "locked_regions": [
    {
      "id": "locked_001",
      "x": 10,
      "y": 12,
      "width": 8,
      "height": 6,
      "layers": null,
      "reason": "user_locked"
    }
  ]
}
```

This is not yet wired into map generation. The next generator-side step is to accept this state as a constraint input and preserve locked cells during partial regeneration.

## 5. Verification

Added tests:

```text
tests/test_editor_state.py
```

Covered behavior:

- Selection normalization and map-bound clamping.
- Layer visibility defaults and toggles.
- Lock/unlock selected area.
- Undo/redo for selection, lock, and visibility changes.

## 6. Next Phase 3 Steps

Recommended next work:

- Add an `editor_state.schema.json`.
- Add a CLI command to validate exported editor state.
- Add a partial-regeneration request model that accepts prompt, source `map_data.json`, selection, and locked regions.
- Implement tile editing in the local preview, then save a patched `map_data.json`.
- Replace debug color rendering with tileset PNG rendering after asset quality improves.
