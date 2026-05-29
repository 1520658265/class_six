extends Node

var resource_dir: String = "res://resources/atlas"

var _cache: Dictionary = {}

func get_item(category: String, item_name: String) -> Texture2D:
    var atlas: AtlasSet = _get_set(category)
    assert(atlas.items.has(item_name),
        "Missing atlas item: %s/%s" % [category, item_name])
    return atlas.items[item_name]

func get_set(category: String) -> AtlasSet:
    return _get_set(category)

func _get_set(category: String) -> AtlasSet:
    if _cache.has(category):
        return _cache[category]
    var path := "%s/%s.tres" % [resource_dir, category]
    assert(ResourceLoader.exists(path), "Missing AtlasSet: %s" % path)
    var res := load(path) as AtlasSet
    assert(res != null, "Invalid AtlasSet at %s" % path)
    _cache[category] = res
    return res
