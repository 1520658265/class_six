class_name BakeVFX
extends RefCounted

const VfxClipCls = preload("res://scripts/shared/vfx_clip.gd")

static func bake(vfx: Dictionary, output_dir: String) -> Dictionary:
    DirAccess.make_dir_recursive_absolute(output_dir)
    var ok := 0
    var skipped := 0
    var errors: Array[String] = []

    for entry_id in vfx.keys():
        var entry: Dictionary = vfx[entry_id]
        var sheet_path: String = entry.get("sheet", "")
        if not ResourceLoader.exists(sheet_path):
            errors.append("[ERR] vfx/%s: sheet not found %s" % [entry_id, sheet_path])
            skipped += 1
            continue
        var tex := load(sheet_path) as Texture2D

        var tile_w: int = entry.get("tile_w", 0)
        var tile_h: int = entry.get("tile_h", 0)
        var rows: int = entry.get("rows", 0)
        var cols: int = entry.get("cols", 0)
        if tex.get_width() != tile_w * cols or tex.get_height() != tile_h * rows:
            errors.append("[ERR] vfx/%s: sheet size mismatch" % entry_id)
            skipped += 1
            continue

        var sf := SpriteFrames.new()
        var frame_indices: Array = entry.get("frames", [0])
        for idx in frame_indices:
            var row: int = int(idx) / cols
            var col: int = int(idx) % cols
            var at := AtlasTexture.new()
            at.atlas = tex
            at.region = Rect2(col * tile_w, row * tile_h, tile_w, tile_h)
            sf.add_frame("default", at)

        var clip: Resource = VfxClipCls.new()
        clip.name = entry_id
        clip.frames = sf
        var preset: Dictionary = entry.get("preset", {})
        clip.scale_from = _to_vec2(preset.get("scale_from", [1.0, 1.0]))
        clip.scale_to = _to_vec2(preset.get("scale_to", [1.0, 1.0]))
        clip.scale_dur = preset.get("scale_dur", 0.0)
        clip.alpha_from = preset.get("alpha_from", 1.0)
        clip.alpha_to = preset.get("alpha_to", 0.0)
        clip.alpha_dur = preset.get("alpha_dur", 0.0)
        clip.offset = _to_vec2(preset.get("offset", [0.0, 0.0]))

        var out_path := "%s/%s.tres" % [output_dir, entry_id]
        var save_err := ResourceSaver.save(clip, out_path)
        if save_err != OK:
            errors.append("[ERR] vfx/%s: save failed %s" % [entry_id, save_err])
            skipped += 1
            continue

        print("[OK] vfx/%s -> %s (%d frames)" % [entry_id, out_path, frame_indices.size()])
        ok += 1

    return { "ok": ok, "skipped": skipped, "errors": errors }

static func _to_vec2(arr: Array) -> Vector2:
    if arr.size() < 2:
        return Vector2.ZERO
    return Vector2(arr[0], arr[1])
