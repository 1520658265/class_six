# Type Pipelines

Use the section matching the user's `type`. All flows are Gemini-only.

Type aliases:

- `tile` uses the `tile` section for one tile or small tile family.
- `tileset` uses the `tileset` section for a coordinated map tile sheet.
- `icon` uses the `icon` section for UI/inventory icons.
- `item` uses the `item` section for RPG inventory/world objects.

## character

Goal: create a reusable character master pack.

Required details: style, reference image, subject description, outfit, era/world, output size.

Pipeline:
1. Generate 2-4 full-body concept candidates from the reference.
2. Pick or ask user to pick one approved concept.
3. Generate master views: front, back, left side, right side. If side views fail, generate one side and mirror the other.
4. Generate portrait and face close-up from the approved master.
5. Create `character_manifest.json` with palette, outfit constraints, hair/face notes, and camera angle.

Acceptance:
- One character only.
- Same outfit and hair across all views.
- Clear silhouette at intended game scale.
- No weapon/prop unless requested.

## portrait

Goal: create a full-body or bust portrait suitable for dialogue/UI.

Pipeline:
1. Use reference image plus style lock.
2. Generate 2-4 candidates.
3. Promote one final portrait.
4. Crop optional face icon from the final portrait if requested.

Prompt constraints:
- State composition explicitly: full body, bust, or head-and-shoulders.
- Use a simple background unless transparent output is required.
- Avoid asking for both concept sheet and portrait in one prompt.

## face

Goal: create expression set from an approved portrait or face master.

Pipeline:
1. Require approved face or portrait reference.
2. Generate expressions one by one, not as a grid, unless only rough candidates are needed.
3. Keep framing identical: head size, shoulder crop, camera angle.
4. Use safe wording for discomfort expressions: "tired", "dizzy", "uneasy", "sweat drop"; avoid gore/injury wording.

Default expressions:
`neutral`, `happy`, `angry`, `sad`, `surprised`, `shy`, `hurt`, `eyes_closed`.

## animation

Goal: create usable RPG animation frames.

Required details: animation kind, directions, frame count, master image, target size.

Rules:
- Do not rely on one generated sheet as final.
- Generate complete sprite-sheet candidates first for walk cycles. Do not free-generate independent frames as the main path.
- Always align frames after cutout: center X and feet/bottom anchor.
- For normal RPG import, start with 4x4 `down, left, right, up` sheet candidates because Gemini obeys this layout more reliably.
- For high-resolution previews or visible character sprites, test 4x8 smooth walk sheets with small pose deltas. Accept them only if the sheet is exactly 8 columns x 4 rows and each row is one continuous direction.
- Use 4-frame `idle, left-step, idle, right-step` only when the target engine or tiny in-game scale requires compact output.
- Do not treat repeated idle frames as smoothness. If `idle -> stride -> idle -> stride` looks choppy in preview, regenerate as 8 frames instead of only repairing anchors.
- Do not free-generate every frame of an 8-frame cycle and assume it will be smooth. If Gemini drifts, repeats idle poses, adds extra rows, or produces tiny/odd limb deltas, reject the 8-frame final and either retry the full sheet with stricter layout or reduce to fewer approved keyframes.
- Generate `walk-down` and `walk-up` directly. For left/right, prefer generating the cleaner side and mirroring the other.
- For battle actions keep frame counts compact:
  - idle: 2-4
  - attack: 4
  - hurt: 3-4
  - victory/skill/dead: ask user before generating larger sets

Prompt pattern:
- Sheet prompts must state exact grid count, exact row order, exact canvas aspect, and "no extra rows or columns".
- For 4x8 prompts, require eight named phases: contact, down, passing, up, opposite contact, opposite down, opposite passing, opposite up.
- Local repair prompts must say "same character, same size, same camera, same outfit; only limb pose changes".
- Avoid dramatic pose changes unless the action requires them.

Animation QA is mandatory. See `qa.md`.

## tileset

Goal: create a coordinated repeatable RPG map tileset.

Required details: style, biome/theme, tile size, list of tile types.

Pipeline:
1. Generate a style board for the environment.
2. Generate base tiles individually: grass, dirt, path, water, wall, floor, roof, etc.
3. For each tile, create a 3x3 repeat preview.
4. Generate transition tiles only after base tiles pass repeat QA.
5. Assemble tileset sheet and `tileset_manifest.json`.

Prompt constraints:
- "Top-down orthographic RPG tile, no perspective horizon."
- "Seamless tile, edges match when repeated."
- "No text, no frame, no drop shadow, no object crossing tile boundary unless designed as a transition."

Reject:
- Non-repeatable edge seams.
- Lighting direction that changes per tile.
- Random decorative objects baked into all base tiles.

## tile

Goal: create one repeatable RPG map tile or a small family of closely related tiles.

Pipeline:
1. Generate 2-4 candidates for the requested tile.
2. Build 3x3 repeat preview for each candidate.
3. Promote only seamless candidates to `final/`.
4. If this tile must connect to existing tiles, test it against those neighbors.

Prompt constraints:
- Use the same constraints as `tileset`.
- Prefer one material per base tile.
- Avoid unique landmarks in base tiles.

## item

Goal: create RPG inventory or world object assets.

Required details: style, object description/reference, size, background.

Pipeline:
1. Generate 4 candidates on plain/magenta background.
2. Pick best silhouette.
3. Cut to transparent PNG.
4. Export requested sizes, commonly 32, 64, 128, 256.
5. Create contact sheet and single-object QA.

Prompt constraints:
- Single object only.
- Centered, no hand holding it unless requested.
- Strong readable silhouette.
- Use a three-quarter view for inventory icons unless the user requests flat UI icons.

## icon

Goal: create compact UI or inventory icons.

Pipeline:
1. Generate 4 candidates with the requested style and silhouette.
2. Cut to transparent PNG.
3. Export requested sizes, usually 32, 64, 128, and 256.
4. Preview all sizes on dark and light backgrounds.

Prompt constraints:
- Single symbol or object only.
- Strong silhouette at 32x32.
- No text unless explicitly requested.
- Prefer flat or three-quarter view based on the user's UI style.

## ui

Goal: create UI components or panels.

Required details: component list, style, resolution, engine.

Pipeline:
1. Generate style board for UI material, borders, icons, and palette.
2. Generate individual components, not a crowded mockup, unless the user asks for concept art.
3. Slice and export named PNGs.
4. Provide a preview page showing normal/hover/disabled states if applicable.

Reject:
- Text baked into UI unless explicitly requested.
- Inconsistent border radius or lighting.
- Components that cannot be sliced cleanly.

## effect

Goal: create VFX sprites such as impact, sparkle, smoke, magic, status icons.

Required details: effect type, frame count, style, target background.

Pipeline:
1. Generate a small candidate sheet or single frames depending on complexity.
2. Prefer 4-8 frames for effects.
3. Ensure transparent background and no hard frame borders.
4. Preview as GIF over dark and light backgrounds.

Reject:
- Large opaque background haze.
- Text, symbols, or UI marks not requested.
- Frame-to-frame color/style jumps.

## pack

Goal: create a coordinated set containing multiple types.

Pipeline:
1. Ask user to choose the included types.
2. Create one style lock and manifest for the whole pack.
3. Generate in this order: style board, character masters, portraits/faces, animation, tiles, items, UI/effects.
4. QA each type independently before creating the final pack preview.
