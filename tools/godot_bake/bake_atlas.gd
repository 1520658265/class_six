class_name BakeAtlas
extends RefCounted

const AtlasSetCls = preload("res://scripts/shared/atlas_set.gd")

static func bake(atlas_section: Dictionary, output_dir: String) -> Dictionary:
    DirAccess.make_dir_recursive_absolute(output_dir)
    var ok := 0
    var skipped := 0
    var errors: Array[String] = []

    for entry_id in atlas_section.keys():
        var entry: Dictionary = atlas_section[entry_id]
        var sheet_path: String = entry.get("sheet", "")
        if not ResourceLoader.exists(sheet_path):
            errors.append("[ERR] atlas/%s: sheet not found %s" % [entry_id, sheet_path])
            skipped += 1
            continue
        var tex := load(sheet_path) as Texture2D

        var atlas_set: Resource = AtlasSetCls.new()
        atlas_set.category = entry_id

        var slice_mode: String = entry.get("slice_mode", "grid")
        var ok_entry := true

        if slice_mode == "regions":
            var regions: Dictionary = entry.get("regions", {})
            var sheet_rect := Rect2i(0, 0, tex.get_width(), tex.get_height())
            for item_name in entry.get("items", {}).keys():
                var item: Dictionary = entry["items"][item_name]
                var rect_data = regions.get(item.get("region", ""), null)
                if rect_data == null or rect_data.size() != 4:
                    errors.append("[ERR] atlas/%s/%s: missing region" % [entry_id, item_name])
                    ok_entry = false
                    break
                var r := Rect2i(rect_data[0], rect_data[1], rect_data[2], rect_data[3])
                if r.size.x <= 0 or r.size.y <= 0 or not sheet_rect.encloses(r):
                    errors.append("[ERR] atlas/%s/%s: region out of bounds" % [entry_id, item_name])
                    ok_entry = false
                    break
                var at := AtlasTexture.new()
                at.atlas = tex
                at.region = Rect2(r.position.x, r.position.y, r.size.x, r.size.y)
                atlas_set.items[item_name] = at
        else:
            var tile_w: int = entry.get("tile_w", 0)
            var tile_h: int = entry.get("tile_h", 0)
            var rows: int = entry.get("rows", 0)
            var cols: int = entry.get("cols", 0)
            if tex.get_width() != tile_w * cols or tex.get_height() != tile_h * rows:
                errors.append("[ERR] atlas/%s: sheet size mismatch" % entry_id)
                skipped += 1
                continue
            for item_name in entry.get("items", {}).keys():
                var it: Dictionary = entry["items"][item_name]
                var at := AtlasTexture.new()
                at.atlas = tex
                at.region = Rect2(it.get("col", 0) * tile_w, it.get("row", 0) * tile_h, tile_w, tile_h)
                atlas_set.items[item_name] = at

        if not ok_entry:
            skipped += 1
            continue

        var out_path := "%s/%s.tres" % [output_dir, entry_id]
        var save_err := ResourceSaver.save(atlas_set, out_path)
        if save_err != OK:
            errors.append("[ERR] atlas/%s: save failed %s" % [entry_id, save_err])
            skipped += 1
            continue

        print("[OK] atlas/%s -> %s (%d items)" % [entry_id, out_path, atlas_set.items.size()])
        ok += 1

    return { "ok": ok, "skipped": skipped, "errors": errors }
