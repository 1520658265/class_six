---
name: rpg-asset-gen
description: Gemini-only RPG asset generation workflow for creating high-quality game art packs. Use when the user asks to generate or plan RPG assets such as characters, portraits, faces, walk/battle animation frames, tilesets, map tiles, items, icons, UI, or effects, especially when the only required upfront parameter is type and the assistant must ask for missing style/reference details before producing assets.
---

# RPG Asset Gen

Use this skill to run a Gemini-only RPG asset pipeline. Do not use ControlNet, OpenPose, LoRA, IP-Adapter, or other pose-control systems. Treat Gemini as a candidate generator and the pipeline as the quality system.

## Input Contract

Accept one required parameter:

```text
type=<character|portrait|face|animation|tileset|tile|item|icon|ui|effect|pack>
```

If the user provides only `type`, ask for the minimum missing details before generating:

- `style`: visual style, e.g. `q_chibi`, `hd2d`, `rpg_maker`, `gba_pixel`, `dark_fantasy`, or a custom description.
- `reference`: one or more image paths or a clear text reference. For character-derived assets, require at least one reference image or an existing approved master asset.
- `subject`: what to generate, including identity, outfit, palette, era, role, and required props.
- `scope`: exact output set, counts, sizes, and engine needs.
- `output_dir`: where to write files. Default to `tools/ai/out/<slug>_<type>/` in this repo if not specified.

Ask no more than three questions at once. If generation would call an external image service, state that network/API access may be required before running commands.

When only `type` is provided, respond with exactly three grouped questions:

1. Ask for `style`.
2. Ask for `reference` and `subject` together.
3. Ask for `scope`, including size/counts/output directory.

## Workflow

1. **Classify `type`** and load the relevant section from `references/types.md`.
2. **Build a production brief** from user answers: style, references, subject, dimensions, output directory, naming, and acceptance criteria.
3. **Create a style lock** before bulk generation:
   - Generate or select a `style_reference.png`.
   - Record palette, line weight, shading rules, camera angle, and background keying in `manifest.json`.
4. **Generate masters before variants**:
   - Characters: create approved master front/back/side views before animation.
   - Tilesets: create style board and repeatable base tile before variants.
   - Items/icons/UI/effects: create 2-4 candidates before final resizing.
5. **Generate candidates, not final by default**:
   - Use 2-4 candidates for important assets.
   - Keep prompts and raw outputs under `prompts/` and `raw/`.
   - Promote only QA-passing assets to `final/`.
6. **Run QA gates** from `references/qa.md`.
7. **Create previews**:
   - HTML preview for any pack.
   - GIF or strip preview for animation.
   - 3x3 repeat preview for tiles.
   - Contact sheet for candidates.
8. **Report outcome** with file links, QA status, failures, and recommended retries.

## Gemini-Only Rules

- For walking animation, prefer complete sprite-sheet candidates over free-generating frames one by one. Gemini is more consistent when it sees the full cycle and all directions in one composition.
- Never trust a generated sprite sheet without slicing, playback preview, and QA.
- Start with 4x4 walk sheets for reliability unless the user or engine needs smoother visible motion.
- Use 4x8 smooth walk sheets only as candidates until Gemini proves it obeyed exactly 8 columns x 4 rows. Reject sheets with extra rows, mixed directions, or repeated idle poses.
- For left/right, prefer the cleaner side row and mirror it when acceptable, then touch up only visible asymmetric details if needed.
- Free-generated single frames are for localized repair only, not the primary animation workflow.
- Use magenta or plain background for cutout, then convert to transparent PNG.
- Keep approved masters immutable. New frames should reference masters, not earlier failed candidates.

## Type References

Read only the needed section:

- `references/types.md`: type-specific pipelines and prompt strategy.
- `references/qa.md`: QA gates, preview requirements, and failure handling.

## Output Standard

Every completed run should include:

```text
manifest.json
prompts/
raw/
final/
qa/report.json
preview.html
```

For animation also include:

```text
qa/animation_gifs/
qa/strips/
```

For tiles also include:

```text
qa/repeat_previews/
```

Do not mark a pack complete unless the final assets and previews pass QA or the user explicitly accepts known defects.
