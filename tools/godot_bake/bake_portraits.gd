class_name BakePortraits
extends RefCounted

const PortraitSetCls = preload("res://scripts/shared/portrait_set.gd")

static func bake(portraits: Dictionary, output_dir: String) -> Dictionary:
    DirAccess.make_dir_recursive_absolute(output_dir)
    var ok := 0
    var skipped := 0
    var errors: Array[String] = []

    for entry_id in portraits.keys():
        var entry: Dictionary = portraits[entry_id]
        var sheet_path: String = entry.get("sheet", "")
        if not ResourceLoader.exists(sheet_path):
            errors.append("[ERR] portraits/%s: sheet not found %s" % [entry_id, sheet_path])
            skipped += 1
            continue
        var tex := load(sheet_path) as Texture2D

        var ps: Resource = PortraitSetCls.new()
        ps.character_id = entry_id

        var slice_mode: String = entry.get("slice_mode", "grid")
        var ok_entry := true

        if slice_mode == "regions":
            var regions: Dictionary = entry.get("regions", {})
            var sheet_rect := Rect2i(0, 0, tex.get_width(), tex.get_height())
            for expr_name in entry.get("expressions", {}).keys():
                var expr_entry: Dictionary = entry["expressions"][expr_name]
                var rect_data = regions.get(expr_entry.get("region", ""), null)
                if rect_data == null or rect_data.size() != 4:
                    errors.append("[ERR] portraits/%s/%s: missing region" % [entry_id, expr_name])
                    ok_entry = false
                    break
                var r := Rect2i(rect_data[0], rect_data[1], rect_data[2], rect_data[3])
                if r.size.x <= 0 or r.size.y <= 0 or not sheet_rect.encloses(r):
                    errors.append("[ERR] portraits/%s/%s: region out of bounds" % [entry_id, expr_name])
                    ok_entry = false
                    break
                var at := AtlasTexture.new()
                at.atlas = tex
                at.region = Rect2(r.position.x, r.position.y, r.size.x, r.size.y)
                ps.expressions[expr_name] = at
        else:
            var tile_w: int = entry.get("tile_w", 0)
            var tile_h: int = entry.get("tile_h", 0)
            var rows: int = entry.get("rows", 0)
            var cols: int = entry.get("cols", 0)
            if tex.get_width() != tile_w * cols or tex.get_height() != tile_h * rows:
                errors.append("[ERR] portraits/%s: sheet size mismatch" % entry_id)
                skipped += 1
                continue
            for expr_name in entry.get("expressions", {}).keys():
                var ex: Dictionary = entry["expressions"][expr_name]
                var at := AtlasTexture.new()
                at.atlas = tex
                at.region = Rect2(ex.get("col", 0) * tile_w, ex.get("row", 0) * tile_h, tile_w, tile_h)
                ps.expressions[expr_name] = at

        if not ok_entry:
            skipped += 1
            continue

        var out_path := "%s/%s.tres" % [output_dir, entry_id]
        var save_err := ResourceSaver.save(ps, out_path)
        if save_err != OK:
            errors.append("[ERR] portraits/%s: save failed %s" % [entry_id, save_err])
            skipped += 1
            continue

        print("[OK] portraits/%s -> %s (%d exprs)" % [entry_id, out_path, ps.expressions.size()])
        ok += 1

    return { "ok": ok, "skipped": skipped, "errors": errors }
