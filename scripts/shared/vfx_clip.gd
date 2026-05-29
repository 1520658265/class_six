class_name VfxClip
extends Resource

@export var name: String = ""
## SpriteFrames，单 animation 名为 "default"
@export var frames: SpriteFrames

## tween preset
@export var scale_from: Vector2 = Vector2.ONE
@export var scale_to: Vector2 = Vector2.ONE
@export var scale_dur: float = 0.0
@export var alpha_from: float = 1.0
@export var alpha_to: float = 0.0
@export var alpha_dur: float = 0.0
@export var offset: Vector2 = Vector2.ZERO
