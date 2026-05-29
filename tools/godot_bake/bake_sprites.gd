class_name BakeSprites
extends RefCounted

## 把 sprites section 烤成 SpriteFrames .tres，逐条目落到 output_dir。
## 返回 { ok: int, skipped: int, errors: Array[String] }
static func bake(sprites: Dictionary, output_dir: String) -> Dictionary:
    DirAccess.make_dir_recursive_absolute(output_dir)
    var ok := 0
    var skipped := 0
    var errors: Array[String] = []

    for entry_id in sprites.keys():
        var entry: Dictionary = sprites[entry_id]
        var sheet_path: String = entry.get("sheet", "")
        if not ResourceLoader.exists(sheet_path):
            errors.append("[ERR] sprites/%s: sheet not found %s" % [entry_id, sheet_path])
            skipped += 1
            continue

        var tex := load(sheet_path) as Texture2D
        var actual_w := tex.get_width()
        var actual_h := tex.get_height()
        var tile_w: int = entry.get("tile_w", 0)
        var tile_h: int = entry.get("tile_h", 0)
        var rows: int = entry.get("rows", 0)
        var cols: int = entry.get("cols", 0)
        var expected_w := tile_w * cols
        var expected_h := tile_h * rows
        if actual_w != expected_w or actual_h != expected_h:
            errors.append("[ERR] sprites/%s: sheet %dx%d but manifest expects %dx%d" %
                [entry_id, actual_w, actual_h, expected_w, expected_h])
            skipped += 1
            continue

        var sf := SpriteFrames.new()
        sf.remove_animation("default")
        var anims: Dictionary = entry.get("animations", {})
        for anim_name in anims.keys():
            var anim: Dictionary = anims[anim_name]
            sf.add_animation(anim_name)
            sf.set_animation_speed(anim_name, anim.get("fps", 6))
            sf.set_animation_loop(anim_name, anim.get("loop", true))
            var row: int = anim.get("row", 0)
            for col in anim.get("frames", []):
                var at := AtlasTexture.new()
                at.atlas = tex
                at.region = Rect2(col * tile_w, row * tile_h, tile_w, tile_h)
                sf.add_frame(anim_name, at)

        var out_path := "%s/%s.tres" % [output_dir, entry_id]
        var save_err := ResourceSaver.save(sf, out_path)
        if save_err != OK:
            errors.append("[ERR] sprites/%s: save failed %s" % [entry_id, save_err])
            skipped += 1
            continue

        print("[OK] sprites/%s -> %s (%d anims)" % [entry_id, out_path, anims.size()])
        ok += 1

    return { "ok": ok, "skipped": skipped, "errors": errors }
