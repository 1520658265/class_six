## 场景门：主角踩到 Area2D 后切到目标场景。
##
## 关键约束：
##   1. 切场刚完成时，主角胶囊体可能正好生成在某个返回门的 Area2D 里，
##      会立刻触发 body_entered。需要一个短暂的 grace 期把这种"出生即在门里"
##      的初次触发吞掉。
##   2. 对话播放期间也不能切场（避免 cutscene 中途断掉）；对话结束后
##      要重新检查是否还在门里。
class_name SceneDoor
extends Area2D

const GRACE_PERIOD := 0.4  ## 切场后这么久内的 body_entered 视为"出生即重叠"，忽略

@export var target_scene_id: String = ""
@export var target_spawn_point: String = "default"
## 是否需要按 interact 才触发（false 则碰到就传送）
@export var requires_interact: bool = false

var _player_inside: Node2D = null
var _initialized: bool = false

func _ready() -> void:
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)
	Dialogue.dialogue_finished.connect(_on_dialogue_finished)
	collision_layer = 0
	collision_mask = 2
	get_tree().create_timer(GRACE_PERIOD).timeout.connect(_on_grace_done)

func _on_grace_done() -> void:
	_initialized = true
	## grace 期结束后再重新评估：如果主角是真的"走进来了"才算
	## 但出生时已经站在门里的情况下也不能直接传 — 等他先离开再重新进
	if _player_inside != null and not requires_interact:
		## 如果主角现在在门里，先标记为"等待离开"，等他离开再触发
		_player_inside = null

func _on_body_entered(body: Node2D) -> void:
	if not body.is_in_group("player"):
		return
	_player_inside = body
	_maybe_trigger()

func _on_body_exited(body: Node2D) -> void:
	if body == _player_inside:
		_player_inside = null

func _on_dialogue_finished(_start_line_id: String) -> void:
	## 对话结束后重新评估：如果主角还在门里说明他真的要进
	_maybe_trigger()

func _unhandled_input(event: InputEvent) -> void:
	if not requires_interact or _player_inside == null:
		return
	if not _initialized:
		return
	if Dialogue.is_playing():
		return
	if event.is_action_pressed("interact"):
		get_viewport().set_input_as_handled()
		_trigger()

func _maybe_trigger() -> void:
	if not _initialized:
		return
	if _player_inside == null:
		return
	if requires_interact:
		return
	if Dialogue.is_playing():
		return
	_trigger()

func _trigger() -> void:
	if target_scene_id == "":
		push_error("[SceneDoor:%s] target_scene_id 未配置" % name)
		return
	## 防止 trigger 后还有信号回来重复触发
	_initialized = false
	_player_inside = null
	SceneRouter.change_scene(target_scene_id, target_spawn_point)
