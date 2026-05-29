extends Node

var resource_dir: String = "res://resources/portraits"

var _cache: Dictionary = {}

func get_expression(character_id: String, expression: String) -> Texture2D:
    var ps: PortraitSet = _get_set(character_id)
    assert(ps.expressions.has(expression),
        "Missing portrait expression: %s/%s" % [character_id, expression])
    return ps.expressions[expression]

func get_set(character_id: String) -> PortraitSet:
    return _get_set(character_id)

func _get_set(character_id: String) -> PortraitSet:
    if _cache.has(character_id):
        return _cache[character_id]
    var path := "%s/%s.tres" % [resource_dir, character_id]
    assert(ResourceLoader.exists(path), "Missing PortraitSet: %s" % path)
    var res := load(path) as PortraitSet
    assert(res != null, "Invalid PortraitSet at %s" % path)
    _cache[character_id] = res
    return res
