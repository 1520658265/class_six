---
name: linsen-asset-scene
description: Scene-driven RPG map asset workflow for Linsen/class_six. Use when creating or continuing a scene directory from scene.md through map_spec.json, style_profile.json, entities.json, prompts.json, scene image sprites, art_manifest.json, and final Godot scene export with category-based object placement.
---

# Linsen Asset Scene

Use this skill to produce one scene asset pipeline in `asset_general_system`. The human-authored input is `scene.md`; Python owns validation, placement, image generation calls, packing, and Godot export.

## Stage Flow

1. Locate or create a scene directory containing `scene.md`.
2. Write `map_spec.json` for the `spec` stage.
3. Run `python -B generate.py scene-validate <scene_dir> --stage spec` from `asset_general_system`.
4. Run `python -B generate.py scene-map-build <scene_dir> [--force]`.
5. Write `style_profile.json`.
6. Run `python -B generate.py scene-concept <scene_dir> [--gemini] [--force]` to create the background-only concept prompt/image.
7. Run `python -B generate.py scene-background-plan <scene_dir> [--concept-image PATH] [--force]`.
8. Run `python -B generate.py scene-background-review <scene_dir> [--force]` and have the user mark which background blocks can be extracted, cleaned, regenerated, or ignored.
9. Run `python -B generate.py scene-background-assets <scene_dir> [--force]` after the reviewed plan is saved back to `background_plan.json`.
10. Write `entities.json` from `art_request.json`; do not invent target ids.
11. Write `prompts.json`.
12. Run `python -B generate.py scene-validate <scene_dir> --stage prompts`.
13. Run `python -B generate.py scene-images <scene_dir> [--gemini | --pixai] [--force] [--variants N] [--target TARGET_ID]`.
14. Run `python -B generate.py scene-pack <scene_dir> [--force] [--resource-base RES_PATH]`.
15. Run `python -B generate.py scene-status <scene_dir>`.

If the user asks for a single stage, execute only the needed stage and its prerequisite validation. If `--review-all` is requested, pause for user review after writing `map_spec.json`, `style_profile.json`, `entities.json`, and `prompts.json`; do not pause after Python-only stages.

## Scene Spec Rules

`objects[].type` is a semantic placement category, not a concrete item name. Use only:

`building`, `large_prop`, `small_prop`, `thin_prop`, `npc`, `facade_overlay`, `text_sign`.

Concrete identity lives in:

- `properties.object_key`: stable ASCII snake_case key, such as `ping_pong_table`.
- `label`: human display label.
- `properties.display_name`: concrete item name.

Stable generated ids use `{object_key}_{index:02d}`. For two ping-pong tables, expect `ping_pong_table_01` and `ping_pong_table_02`.

Keep these fields straight:

- `properties.footprint` is map occupancy and must be a string like `"3x2"`.
- `source_canvas` is image generation canvas and must be `[W, H]`, such as `[128, 96]`.
- `blocking` controls collision.
- `placement` may reference a region id/type or a placement hint.
- `facade_overlay` and `text_sign` must include `properties.attached_to`, referencing a region id or predictable object id.
- `text_sign.properties.text` is runtime metadata for Godot Label text. Never ask the PNG generator to draw readable text.

For tilemap scenes, model the map in grid units. Do not turn a large ground feature into one big sprite when it should be assembled from tiles.

- Use `base_terrain` when the whole map background is one terrain, such as a wheat field. It generates one tile asset and fills the terrain layer.
- Use `composites[]` for shapes such as crossroads, roads, fences, rivers, and tracks. The model must analyze and split the entity into reusable `parts[]`, then provide `layout[]` cells that place those parts on the grid.
- `composites[].parts[]` are the art targets. `composites[].layout[]` are map instances. A composite id such as `oval_track_01` should not become one generated PNG unless the user explicitly asks for a single prop image.
- Every `layout[]` cell is one tile coordinate inside the composite footprint and references a part key. Python should only instantiate that grid layout; it should not guess the semantic decomposition.

## Background Concept And Review

Generate and review the background before foreground entities. Gemini is preferred for `scene-concept` because it is better at whole-scene composition. The concept image is a layout/style reference, not automatically the final tilemap.

After concept generation, build `background_plan.json` and use `background_review.html` to classify background blocks:

- `extract_from_concept`: crop directly from the concept image.
- `extract_and_cleanup`: crop from the concept image, then clean/snap/resize before use.
- `regenerate`: do not crop; generate this tile/composite part separately.
- `ignore`: do not produce this block.

Use extraction for clean, grid-aligned, reusable terrain or surface patches. Use regeneration for curves, edge pieces, unclear areas, non-grid-aligned areas, and anything polluted by foreground entities.

Reviewed crops are written to `background_tiles/{asset_id}.png`. During `scene-pack`, these reviewed background tiles take precedence over `images/{asset_id}.png`, so approved terrain, road, and track blocks appear in the final tileset and preview.

## Category Placement Intent

- `building`: large boundary/front-facing structure, blocking.
- `large_prop`: zone-contained large facility, usually blocking.
- `small_prop`: decoration near buildings or paths, usually non-blocking unless specified.
- `thin_prop`: one-tile-wide vertical object such as poles or hoops, blocking.
- `npc`: character/person/activity object, non-blocking.
- `facade_overlay`: wall-attached sprite, non-blocking.
- `text_sign`: wall/front sign sprite plus separate runtime text label, non-blocking.

## Composite Examples

For a crossroad, prefer parts such as:

`road_center`, `road_edge_top`, `road_edge_bottom`, `road_edge_left`, `road_edge_right`.

For an oval track, prefer parts such as:

`track_center`, `track_curve_top_left`, `track_curve_top_right`, `track_curve_bottom_left`, `track_curve_bottom_right`.

Add straight or edge parts when the requested shape needs them; keep each part a tile-scale sprite unless there is a concrete reason to use a larger footprint.

## File Contracts

Write only valid JSON for machine stage files. Use the schemas under `asset_general_system/specs/`:

- `scene_map_spec.schema.json`
- `scene_style_profile.schema.json`
- `scene_entities.schema.json`
- `scene_prompts.schema.json`
- `background_plan.schema.json`
- `art_manifest.schema.json`
- `progress.schema.json`

Use the examples in this skill's `examples/` directory as compact shape references. The repository example at `asset_general_system/examples/scenes/dingbu_primary_school_1998/` is a fuller end-to-end fixture.

## Image Prompt Rules

For transparent sprite targets, request a PNG with true alpha outside the asset. Do not ask for a white, flat-color, checkerboard, chroma-key, or matte background, and do not plan a later cutout step for PixAI/PixelLab outputs. For opaque terrain or composite-source targets, request an opaque image that fills the full canvas. Use the style profile for shared era, palette, view, and forbidden terms.

For `text_sign`, the prompt body should describe a blank sign or blank notice papers. Put `readable text`, `Chinese characters`, and `letters` in `negative`. The actual readable text belongs only in `properties.text` / `entities[].text`.

Do not add a new image quality gate. `scene-images` may call Gemini or the mock backend and writes stable `images/{target_id}.png` plus `images/{target_id}.json`.

## CLI Notes

Run commands from `asset_general_system` unless using paths adjusted for the repo root:

```powershell
python -B generate.py scene-validate examples/scenes/dingbu_primary_school_1998 --stage spec
python -B generate.py scene-map-build examples/scenes/dingbu_primary_school_1998 --force
python -B generate.py scene-concept examples/scenes/dingbu_primary_school_1998 --gemini --force
python -B generate.py scene-background-plan examples/scenes/dingbu_primary_school_1998 --force
python -B generate.py scene-background-review examples/scenes/dingbu_primary_school_1998 --force
python -B generate.py scene-background-assets examples/scenes/dingbu_primary_school_1998 --force
python -B generate.py scene-images examples/scenes/dingbu_primary_school_1998 --pixai --target notice_board_01 --force
python -B generate.py scene-pack examples/scenes/dingbu_primary_school_1998 --force
python -B generate.py scene-status examples/scenes/dingbu_primary_school_1998
```

Use `--target TARGET_ID` for single-sprite regeneration. Use `--force` only for the current generated stage; do not delete or overwrite human-authored source files unless explicitly requested.
