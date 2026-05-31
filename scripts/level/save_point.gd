## 存档点：主角进入 Area2D 后按 Z 触发存档（demo 简化为 slot 0 自动覆盖）。
## 视觉是子节点 Light/ColorRect 自己处理。
class_name SavePoint
extends Area2D

signal save_requested(slot: int)

@export var slot: int = 0
## 存档时使用的 scene_id；通常等于场景路由器的 current_scene_id，也可在场景里覆盖
@export var scene_id_override: String = ""

var _player_inside: Node2D = null

func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	collision_layer = 0
	collision_mask = 2

func _on_body_entered(body: Node2D) -> void:
	if body.is_in_group("player"):
		_player_inside = body

func _on_body_exited(body: Node2D) -> void:
	if body == _player_inside:
		_player_inside = null

func _unhandled_input(event: InputEvent) -> void:
	if _player_inside == null:
		return
	if event.is_action_pressed("interact"):
		get_viewport().set_input_as_handled()
		_save_now()

func _save_now() -> void:
	var sid := scene_id_override
	if sid == "":
		sid = SceneRouter.current_scene_id
	var pos: Vector2 = _player_inside.global_position
	var facing: String = _player_inside.get_facing() if _player_inside.has_method("get_facing") else "down"
	if SaveManager.save(slot, sid, pos, facing):
		save_requested.emit(slot)
