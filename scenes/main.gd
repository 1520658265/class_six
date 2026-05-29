extends Node2D

func _ready() -> void:
    var sf := Sprites.walk_frames(AssetIds.Char.YUANSHENG)
    var s := $Yuansheng as AnimatedSprite2D
    s.sprite_frames = sf
    s.play("walk_down")
    print("[smoke] yuansheng SpriteFrames loaded, animations: ", sf.get_animation_names())
