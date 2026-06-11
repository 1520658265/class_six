---
name: linsen-asset-scene
description: Scene-driven RPG/tilemap asset workflow for Linsen/class_six. Use when creating, continuing, testing, reviewing, or debugging a scene asset pipeline from scene.md through map_spec.json, style_profile.json, background concept/review, tile assets, sprites, art_manifest.json, and final Godot export. Also use for Chinese-language requests about scene assets, tilemap scenes, map assets, background review, Gemini asset generation, rice-field tests, or scene.md-to-preview workflows.
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
9. Run `python -B generate.py scene-background-assets <scene_dir> [--gemini] [--force]` after the reviewed plan is saved back to `background_plan.json`.
10. Write `entities.json` from `art_request.json`; do not invent target ids.
11. Write `prompts.json`.
12. Run `python -B generate.py scene-validate <scene_dir> --stage prompts`.
13. Run `python -B generate.py scene-images <scene_dir> [--gemini] [--force] [--variants N] [--target TARGET_ID]`.
14. Run `python -B generate.py scene-pack <scene_dir> [--force] [--resource-base RES_PATH]`.
15. Run `python -B generate.py scene-status <scene_dir>`.

If the user asks for a single stage, execute only the needed stage and its prerequisite validation. By default, pause at every Human Review Gate below. Skip gates only when the user explicitly requests `--auto`, `--no-review`, `skip confirmations`, or equivalent.

## Human Review Gates

Default mode is review-gated. Do not run the next stage until the user explicitly approves the current reviewed artifact.

Mandatory gates:

1. After writing `map_spec.json`, stop and ask the user to confirm semantic entities, `base_terrain`, `composites[]`, object categories, footprints, and placements.
2. After writing `style_profile.json`, stop and ask the user to confirm visual style, palette, view, lighting, and forbidden terms.
3. After `scene-concept`, stop and ask the user to inspect the concept image before building/extracting background tiles.
4. After `scene-background-review`, stop and wait for the user to copy the reviewed JSON from `background_review.html` and replace `background_plan.json`.
5. After writing `entities.json` and `prompts.json`, stop and ask the user to confirm target ids, prompts, transparency expectations, and source canvas sizes before image generation.
6. After `scene-images`, stop and ask the user to inspect generated assets before `scene-pack`.

`--review-all` is accepted as an explicit reminder to enforce all gates, but it is redundant because gates are the default.

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
- `facing` is part of the art contract, not just placement metadata. For `faces_south` / `faces_player`, prompts must positively state that the object must face directly toward the viewer / south side of the map with a centered front view.
- `blocking` controls collision.
- `placement` may reference a region id/type or a placement hint.
- `facade_overlay` and `text_sign` must include `properties.attached_to`, referencing a region id or predictable object id.
- `text_sign.properties.text` is runtime metadata for Godot Label text. Never ask the PNG generator to draw readable text.

For tilemap scenes, model the map in grid units. Do not turn a large ground feature into one big sprite when it should be assembled from tiles.

- Use `base_terrain` when the whole map background is one terrain, such as a wheat field. It identifies the dominant material family and fills the terrain layer.
- Use `composites[]` for shapes such as crossroads, roads, fences, rivers, and tracks. The model must analyze and split the entity into reusable `parts[]`, then provide `layout[]` cells that place those parts on the grid.
- `composites[].parts[]` are the art targets. `composites[].layout[]` are map instances. A composite id such as `oval_track_01` should not become one generated PNG unless the user explicitly asks for a single prop image.
- Every `layout[]` cell is one tile coordinate inside the composite footprint and references a part key. Python should only instantiate that grid layout; it should not guess the semantic decomposition.
- Background tile art should be grouped by material or transition family. Do not generate adjacent terrain, road, track, or surface tiles as isolated one-off images.
- A material such as grass, wheat field, plaza brick, road asphalt, or track surface should have a coordinated `material_group`. A boundary between two materials should have a coordinated `transition_group`.
- Each tile group should be generated as one cohesive sprite sheet, then sliced into fixed slots. This keeps palette, texture scale, lighting, outline weight, and edge continuity consistent.

## Background Concept And Review

Generate and review the background before foreground entities. Gemini is preferred for `scene-concept` because it is better at whole-scene composition. The concept image can be used in two reviewed ways:

- As a temporary full-map background or concept validation image when the whole image has rich connected composition and should remain intact.
- As a source for extracting or regenerating reusable tile/composite blocks when the scene needs strict tile-level assembly.

Do not crop a small terrain tile from a strong full-scene concept just because a base terrain review item exists; ask whether the whole concept should become the map background.

The background concept prompt must ask for a whole-scene image that is suitable for extracting reusable 64x64 tile assets: use an invisible crop grid, align road/track/terrain borders to crop cells, avoid boundaries halfway through a crop cell, keep texture scale consistent, and leave clean unobstructed samples for each reusable material or composite part. Do not draw visible grid lines or sprite-sheet frames.

After concept generation, build `background_plan.json` and use `background_review.html` to classify background blocks. The review page is designed to work as a plain `file://` HTML file, so it does not silently write back to disk. Select a right-side item to apply its `suggested_crop_rect`, drag the crop rectangle to adjust it, then use the page's copy button and replace `background_plan.json` manually.

- `use_full_concept`: use `concept/background_concept.png` as `background/background.png`, clear the base terrain tile layer during pack, and render foreground sprites over it.
- `extract_from_concept`: crop directly from the concept image.
- `extract_and_cleanup`: crop from the concept image, then clean/snap/resize before use.
- `regenerate`: do not crop; regenerate this tile through its material or transition tile group sprite sheet.
- `ignore`: do not produce this block.

Use `use_full_concept` when preserving the complete background is more important than tile reuse. Use extraction for clean, grid-aligned, reusable terrain or surface patches. Use regeneration for curves, edge pieces, unclear areas, non-grid-aligned areas, and anything polluted by foreground entities.

Reviewed crops are written to `background_tiles/{asset_id}.png`. During `scene-pack`, all reviewed background tile candidates take precedence over old `images/{asset_id}.png` candidates, so approved terrain, road, and track blocks appear in the final tileset and preview. Composite instances may use numbered ids such as `road_cross_01_road_center_01`; pack may fall back to the reviewed generic part tile `road_cross_01_road_center.png`.

## Background Tile Family Generation

The production background path is tile-family-first:

1. Plan the tilemap layout and identify reusable surface materials and transitions.
2. Group all tiles that may appear adjacent into `material_group` or `transition_group` families.
3. Generate each family as one sprite sheet with fixed 64x64 slots and no visible borders, labels, dividers, frames, grid lines, or text.
4. Slice the sheet into individual tile PNGs and compose the map from those tiles.

Use `material_group` for one surface family. Include center tiles, center variants, edges, corners, and decorative variants as needed.

Use `transition_group` for boundaries between two surface families. Include top, bottom, left, right edges and any required inside/outside corners. Road and track families should include center/no-edge tiles plus all edge and curve pieces needed by the layout.

Tile family prompts must require:

- one shared palette, lighting direction, pixel density, outline weight, and texture scale
- seamless connection between center, edge, corner, and transition pieces
- crop-aligned 64x64 slots with the full slot filled by opaque terrain pixels
- edge/corner details that continue cleanly into neighboring slots
- no isolated icon composition, no shadows that imply a floating object, and no perspective drift between slots

Compact group shape example:

```json
{
  "tile_groups": [
    {
      "group_id": "brick_plaza",
      "kind": "material_group",
      "generation_mode": "sprite_sheet",
      "tile_size": [64, 64],
      "members": [
        {"tile_id": "brick_center", "role": "center"},
        {"tile_id": "brick_variant_01", "role": "center_variant"},
        {"tile_id": "brick_edge_top", "role": "edge_top"},
        {"tile_id": "brick_edge_bottom", "role": "edge_bottom"},
        {"tile_id": "brick_edge_left", "role": "edge_left"},
        {"tile_id": "brick_edge_right", "role": "edge_right"},
        {"tile_id": "brick_corner_tl", "role": "corner_top_left"},
        {"tile_id": "brick_corner_tr", "role": "corner_top_right"},
        {"tile_id": "brick_corner_bl", "role": "corner_bottom_left"},
        {"tile_id": "brick_corner_br", "role": "corner_bottom_right"}
      ]
    },
    {
      "group_id": "grass_to_brick_transition",
      "kind": "transition_group",
      "from": "grass_lawn",
      "to": "brick_plaza",
      "generation_mode": "sprite_sheet",
      "tile_size": [64, 64],
      "members": [
        {"tile_id": "grass_brick_edge_top", "role": "edge_top"},
        {"tile_id": "grass_brick_edge_bottom", "role": "edge_bottom"},
        {"tile_id": "grass_brick_edge_left", "role": "edge_left"},
        {"tile_id": "grass_brick_edge_right", "role": "edge_right"}
      ]
    }
  ]
}
```

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

For transparent sprite targets, write prompts for an isolated object whose final processed asset has alpha outside the object. The Gemini backend may use a temporary `#ff00ff` chroma-key field and remove it after generation, so do not put contradictory text in the prompt such as both "true alpha output" and "never use chroma key". Always forbid fake transparency and background panels: `checkerboard`, `transparency grid`, `gray checker pattern`, `mock transparent background`, `colored rectangle behind the object`, `background panel`, `floor plane`, `white background`.

For transparent sprite composition, require the object to be centered and large enough to occupy roughly 70-85% of the useful canvas without touching the edges. Avoid tiny icon composition, distant characters, and excessive empty margins, especially for `npc` assets.

All generated scene assets should use a cute, charming visual style with rounded friendly shapes and rich, colorful, bright-but-harmonious colors unless the user explicitly requests a different mood. Do not let generic "pixel art" collapse into dull, muddy, monochrome, or overly desaturated palettes.

For opaque terrain or composite-source targets, request an opaque image that fills the full canvas. Use the style profile for shared era, palette, view, and forbidden terms.

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
python -B generate.py scene-background-assets examples/scenes/dingbu_primary_school_1998 --gemini --force
python -B generate.py scene-images examples/scenes/dingbu_primary_school_1998 --gemini --target notice_board_01 --force
python -B generate.py scene-pack examples/scenes/dingbu_primary_school_1998 --force
python -B generate.py scene-status examples/scenes/dingbu_primary_school_1998
```

Use `--target TARGET_ID` for single-sprite regeneration. Use `--force` only for the current generated stage; do not delete or overwrite human-authored source files unless explicitly requested.

## Invocation Parameters

Use these user-level parameters after `$linsen-asset-scene` when requesting a run:

- `--auto` or `--no-review`: run through gates without asking for confirmation. Use only when the user explicitly accepts automatic execution.
- `--review-all`: enforce all Human Review Gates. This is the default, but the flag makes the intent explicit.
- `--stage STAGE`: run one stage and its prerequisites only. Valid stage names: `spec`, `map`, `style`, `concept`, `background-plan`, `background-review`, `background-assets`, `entities`, `prompts`, `images`, `pack`, `status`.
- `--scene-dir PATH`: use or create a specific scene directory.
- `--title NAME`: use `NAME` as the scene directory name when creating a new scene.
- `--gemini`: use Gemini for concept or image generation when the stage supports it.
- `--target TARGET_ID`: generate or regenerate only one asset target.
- `--force`: rerun the current generated stage even if outputs already exist. Do not apply it to human-authored JSON unless the user explicitly asks.
- `--variants N`: request N image variants for image generation when supported.
- `--concept-image PATH`: pass an existing concept image to `scene-background-plan`.
- `--resource-base PATH`: pass a custom resource base to `scene-pack`.

Example:

```text
$linsen-asset-scene --scene-dir examples/scenes/rice_real_test --gemini --review-all
```
