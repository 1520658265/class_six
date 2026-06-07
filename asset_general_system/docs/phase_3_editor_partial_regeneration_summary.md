# Phase 3 Editor And Partial Regeneration Summary

Updated: 2026-06-05

## 1. Current Conclusion

Phase 3 now has a usable local iteration loop:

```text
map_data.json
  -> editor_preview/index.html
  -> editor_state.json
  -> partial-regenerate CLI
  -> regenerated asset package
  -> validation + Tiled JSON export
```

This keeps the project in structured tilemap data. It does not depend on hand-editing a flat preview image.

## 2. Completed Capabilities

- Local Web preview:
  - Load `map_data.json`.
  - Show/hide tile layers.
  - Show/hide objects, events, and regions.
  - Drag-select a tile rectangle.
  - Lock selected regions.
  - Undo/redo preview-state operations.
  - Export and import `editor_state.json`.

- Editor protocol:
  - `EditorStateDocument`
  - `SelectionRect`
  - `LockedRegion`
  - `specs/editor_state.schema.json`
  - CLI validation through `validate-editor-state`

- Partial regeneration:
  - CLI command: `partial-regenerate`
  - Reads source `map_data.json`.
  - Reads exported `editor_state.json`.
  - Applies a local prompt to the selected region.
  - Preserves locked cells.
  - Repairs simple paths from spawn to key regions.
  - Regenerates collision, preview PNG, Tiled JSON, and reports.

- Tiled import:
  - CLI command: `import-tiled`
  - Converts Tiled JSON tile/object/event layers back to `map_data.json`.

## 3. CLI Commands

Validate editor state:

```bash
python -m generator.cli validate-editor-state --editor-state examples\editor_states\autumn_village_partial_market_state.json --map-data examples\outputs\autumn_village\map_data.json
```

Partial regenerate:

```bash
python -m generator.cli partial-regenerate --map-data examples\outputs\autumn_village\map_data.json --editor-state examples\editor_states\autumn_village_partial_market_state.json --prompt "把这里改成集市" --seed 303 --output examples\outputs\phase3_partial_market_demo --debug-preview
```

Import Tiled JSON:

```bash
python -m generator.cli import-tiled --tiled-json examples\outputs\autumn_village\map.tiled.json --output tmp\imported_map_data.json
```

## 4. Acceptance Demo

Input editor state:

```text
examples/editor_states/autumn_village_partial_market_state.json
```

Output asset package:

```text
examples/outputs/phase3_partial_market_demo/
  map_data.json
  map.tiled.json
  preview.png
  preview_debug.png
  validation_report.json
  tiled_validation_report.json
  partial_regeneration_report.json
  editor_state.json
  generation_report.json
  tilesets/default_rpg_32.png
```

Latest CLI result:

```text
operation=market
changed_tiles=127
validation_passed=True
tiled_validation_passed=True
```

## 5. Current Limits

- Partial regeneration is rule-based, not LLM-driven.
- Supported local prompt classes are intentionally small: market, forest, water, road, playground, snow, sand, and clear.
- Boundary blending is simple.
- The browser preview still renders debug color tiles, not final art.
- Tiled import restores layers and objects/events; full region bounds are only recoverable when present in internal `map_data.json`.

## 6. Next Recommended Work

- Add better boundary blending around regenerated regions.
- Add tile paint/erase tools in `editor_preview`.
- Add per-layer lock UI.
- Expand partial prompt operations with reusable semantic patchers.
- Add a headless browser smoke test for `editor_preview`.
