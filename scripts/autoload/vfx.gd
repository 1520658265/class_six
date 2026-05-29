extends Node

var resource_dir: String = "res://resources/vfx"

var _cache: Dictionary = {}

func spawn(vfx_name: String, pos: Vector2, direction: float = 1.0) -> AnimatedSprite2D:
    var clip := _load_clip(vfx_name)
    var sprite := AnimatedSprite2D.new()
    sprite.sprite_frames = clip.frames
    sprite.global_position = pos + Vector2(clip.offset.x * direction, clip.offset.y)
    sprite.scale = clip.scale_from
    if direction < 0:
        sprite.flip_h = true

    var parent := get_tree().current_scene
    if parent == null:
        parent = self
    parent.add_child(sprite)
    sprite.play("default")

    var tween := sprite.create_tween()
    tween.tween_property(sprite, "scale", clip.scale_to, clip.scale_dur).set_ease(Tween.EASE_OUT)
    tween.parallel().tween_property(sprite, "modulate:a", clip.alpha_to, clip.alpha_dur).from(clip.alpha_from)
    tween.tween_callback(sprite.queue_free)
    return sprite

func _load_clip(vfx_name: String) -> VfxClip:
    if _cache.has(vfx_name):
        return _cache[vfx_name]
    var path := "%s/%s.tres" % [resource_dir, vfx_name]
    assert(ResourceLoader.exists(path), "Missing VfxClip: %s" % path)
    var res := load(path) as VfxClip
    assert(res != null, "Invalid VfxClip at %s" % path)
    _cache[vfx_name] = res
    return res
