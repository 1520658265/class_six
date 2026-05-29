extends SceneTree

const ManifestLoader = preload("res://tools/godot_bake/manifest_loader.gd")
const BakeSprites = preload("res://tools/godot_bake/bake_sprites.gd")
const BakePortraits = preload("res://tools/godot_bake/bake_portraits.gd")
const BakeVFX = preload("res://tools/godot_bake/bake_vfx.gd")
const BakeAtlas = preload("res://tools/godot_bake/bake_atlas.gd")
const BakeAssetIds = preload("res://tools/godot_bake/bake_asset_ids.gd")

const MANIFEST_PATH := "res://tools/godot_bake/manifest.json"
const SPRITE_FRAMES_DIR := "res://resources/sprite_frames"
const PORTRAITS_DIR := "res://resources/portraits"
const VFX_DIR := "res://resources/vfx"
const ATLAS_DIR := "res://resources/atlas"
const ASSET_IDS_PATH := "res://scripts/autoload/asset_ids.gd"

func _init():
    var manifest = ManifestLoader.load_file(MANIFEST_PATH)
    if manifest == null:
        push_error("[bake_all] manifest load failed")
        quit(2)
        return
    if not ManifestLoader.is_valid_version(manifest):
        push_error("[bake_all] unsupported manifest version: %s" % str(manifest.get("version")))
        quit(2)
        return

    var total_skipped := 0
    var total_errors: Array[String] = []

    var r1 = BakeSprites.bake(ManifestLoader.section(manifest, "sprites"), SPRITE_FRAMES_DIR)
    total_skipped += r1.skipped
    total_errors.append_array(r1.errors)

    var r2 = BakePortraits.bake(ManifestLoader.section(manifest, "portraits"), PORTRAITS_DIR)
    total_skipped += r2.skipped
    total_errors.append_array(r2.errors)

    var r3 = BakeVFX.bake(ManifestLoader.section(manifest, "vfx"), VFX_DIR)
    total_skipped += r3.skipped
    total_errors.append_array(r3.errors)

    var r4 = BakeAtlas.bake(ManifestLoader.section(manifest, "atlas"), ATLAS_DIR)
    total_skipped += r4.skipped
    total_errors.append_array(r4.errors)

    var r5 = BakeAssetIds.bake(manifest, ASSET_IDS_PATH)
    total_skipped += r5.skipped
    total_errors.append_array(r5.errors)

    print("---")
    print("Summary: sprites %d/%d, portraits %d/%d, vfx %d/%d, atlas %d/%d, asset_ids %d/%d" % [
        r1.ok, r1.ok + r1.skipped,
        r2.ok, r2.ok + r2.skipped,
        r3.ok, r3.ok + r3.skipped,
        r4.ok, r4.ok + r4.skipped,
        r5.ok, r5.ok + r5.skipped,
    ])
    if total_errors.size() > 0:
        print("Errors:")
        for e in total_errors:
            print("  " + e)

    if total_skipped > 0:
        quit(1)
    else:
        quit(0)
