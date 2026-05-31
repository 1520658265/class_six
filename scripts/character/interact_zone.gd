## 互动区域。挂在 NPC 或物体上，主角进入后按 Z 触发 interact 信号。
## 只检测主角；主角必须在 group "player" 中。
class_name InteractZone
extends Area2D

signal interacted(by_player: Node2D)

@export var prompt_text: String = "按 Z"
@export var enabled: bool = true

var _player_inside: Node2D = null

func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	collision_layer = 0
	collision_mask = 2  ## 仅扫描 player layer 2

func _on_body_entered(body: Node2D) -> void:
	if not enabled:
		return
	if body.is_in_group("player"):
		_player_inside = body

func _on_body_exited(body: Node2D) -> void:
	if body == _player_inside:
		_player_inside = null

func _unhandled_input(event: InputEvent) -> void:
	if not enabled or _player_inside == null:
		return
	if event.is_action_pressed("interact"):
		interacted.emit(_player_inside)
		get_viewport().set_input_as_handled()
