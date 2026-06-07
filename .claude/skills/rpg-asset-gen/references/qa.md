# QA Gates

Use QA as the quality system. Gemini outputs are candidates until they pass.

## Universal Structural QA

Check every final PNG:

- Opens without error.
- Expected dimensions.
- Correct mode and alpha if transparent output is required.
- No text, watermark, signature, or frame border unless explicitly requested.
- Single subject when single subject was requested.
- No visible magenta or matte residue after cutout.
- Subject is centered with adequate padding.

Fail hard on missing files, wrong dimensions, opaque backgrounds, duplicate subjects, or visible background residue.

## Character QA

Check:

- Identity and outfit remain consistent across masters.
- Front/back/side views use the same proportions and palette.
- Silhouette remains readable when scaled to intended sprite size.
- Props and accessories appear only when requested.

If side direction is wrong, prefer mirror from the correct opposite side over retrying blindly.

## Animation QA

Create both GIF and strip previews.

Measure:

- Alpha bbox center X range.
- Bottom/feet anchor range.
- Bbox width/height ratio.
- Opaque area ratio.
- Visible magenta residue.

Human-review:

- Sheet has the exact requested row and column count before any frame-quality review.
- Direction matches filename.
- Camera angle is stable.
- Frame order reads as motion.
- Loop returns cleanly to frame 1.
- Character face/outfit does not flicker.
- For 8-frame walk cycles, frames must form a continuous gait. Repeating the same idle pose or jumping directly from idle to full stride fails smoothness even if anchors pass.

Recommended thresholds for chibi 512 frames:

- Center X range <= 8 px after normalization.
- Bottom anchor range <= 2 px after normalization.
- Walk bbox width ratio <= 1.25.
- Idle bbox width ratio <= 1.15.
- Attack/hurt bbox width ratio may be higher, but action must read naturally.

Do not mark animation complete from numeric QA alone. A GIF/strip human pass is required.

## Tileset QA

For each tile:

- Build 3x3 repeat preview.
- Check for visible seams on all four edges.
- Check tile scale consistency across the set.
- Check lighting direction and palette consistency.
- Check no accidental object repeats too conspicuously unless it is a decorative tile.

Transition tiles:

- Confirm edges match the named neighbors.
- Confirm corners and T-junctions do not create gaps.

## Item/Icon QA

Check:

- One object only.
- Strong silhouette at smallest requested size.
- Transparent background.
- Object not cropped.
- Visual angle consistent across the item set.
- No baked shadows unless requested.

Create a contact sheet at all target sizes.

## UI QA

Check:

- Components can be sliced cleanly.
- No baked text unless requested.
- States are consistent: normal, hover, pressed, disabled.
- Edges and corners align on pixel grid.
- Palette matches the style lock.

## Effect QA

Check:

- Frame order and timing.
- Transparent background.
- No hard square matte.
- Looks acceptable over dark and light backgrounds.
- Start/end frames work for loop or one-shot use.

## Failure Handling

When QA fails:

1. Classify the failure:
   - prompt failure
   - cutout/background failure
   - framing/anchor failure
   - semantic failure
   - animation continuity failure
2. Apply deterministic repair if safe: crop, alpha cleanup, anchor normalization, mirroring, resizing.
3. Retry Gemini only when deterministic repair cannot fix the failure.
4. Keep failed candidates under `raw/rejected/` with a note in `qa/report.json`.
5. If repeated retries fail, reduce scope: fewer frames, simpler pose, simpler style, or split the asset into smaller tasks.

## Preview Requirements

Always create:

- `preview.html` for the pack or asset set.
- `qa/contact_sheet.png` for candidate/final comparison.

Also create:

- Animation: `qa/animation_gifs/*.gif` and `qa/strips/*.png`.
- Tiles: `qa/repeat_previews/*.png`.
- Items/icons: multi-size contact sheet.
