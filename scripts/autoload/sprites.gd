extends Node

## 默认从 res://resources/sprite_frames 加载；测试可改写到 user://...
var resource_dir: String = "res://resources/sprite_frames"

var _cache: Dictionary = {}

func walk_frames(character_id: String) -> SpriteFrames:
    if _cache.has(character_id):
        return _cache[character_id]
    var path := "%s/%s.tres" % [resource_dir, character_id]
    assert(ResourceLoader.exists(path), "Missing SpriteFrames: %s" % path)
    var res := load(path) as SpriteFrames
    assert(res != null, "Invalid SpriteFrames at %s" % path)
    _cache[character_id] = res
    return res
