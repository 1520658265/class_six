## 关卡基类。所有 demo level 场景挂这个脚本。
## 职责：
##  1. 把 SceneRouter.pending_spawn_point 转成主角实际位置
##  2. 自动 instantiate 主角（如果场景没有内置 Yuansheng 节点）
##  3. 给主角 Camera2D 设置 limit，避免视野超出背景
##  4. 进入时按 chapter 选择性播放对应 cutscene 链
##  5. 章节标题卡：第一次进入此章节首场景时弹出
class_name LevelBase
extends Node2D

const PLAYER_SCENE := preload("res://scenes/characters/yuansheng.tscn")

@export var scene_id: String = ""
@export var level_size: Vector2i = Vector2i(0, 0)
## prologue 期间第一次进入时播放的 event_id
@export var first_visit_event: String = ""
## ch1 期间该场景按顺序播放的 event_id 列表（已触发的会跳过）
@export var ch1_events: Array[String] = []

func _ready() -> void:
	y_sort_enabled = true
	if scene_id != "":
		SceneRouter.current_scene_id = scene_id
	_ensure_player()
	SceneRouter.place_player_in_scene(self)
	_apply_camera_limits()
	call_deferred("_after_ready")

func _apply_camera_limits() -> void:
	if level_size.x <= 0 or level_size.y <= 0:
		return
	var player := get_node_or_null("Yuansheng")
	if player == null:
		return
	var cam: Camera2D = player.get_node_or_null("Camera2D")
	if cam == null:
		return
	cam.limit_left = 0
	cam.limit_top = 0
	cam.limit_right = level_size.x
	cam.limit_bottom = level_size.y

func _after_ready() -> void:
	await get_tree().create_timer(0.1).timeout
	var chapter: String = GlobalState.get_chapter()
	if chapter == "prologue" and not GlobalState.has_triggered("_intro/prologue_title"):
		GlobalState.mark_triggered("_intro/prologue_title")
		UIRoot.show_chapter_title("序章 · 二楼的窗")
		await get_tree().create_timer(2.8).timeout
	if chapter == "prologue":
		await _maybe_play_prologue_event()
	elif chapter == "ch1":
		await _maybe_play_ch1_events()

func _maybe_play_prologue_event() -> void:
	if first_visit_event == "":
		return
	if GlobalState.has_triggered(first_visit_event):
		return
	var steps: Array = [{"type": "dialogue", "line_id": first_visit_event + "/01"}]
	var runner := CutsceneRunner.new()
	await runner.run(self, steps)

func _maybe_play_ch1_events() -> void:
	for ev in ch1_events:
		if GlobalState.has_triggered(ev):
			continue
		var steps: Array = [{"type": "dialogue", "line_id": ev + "/01"}]
		var runner := CutsceneRunner.new()
		await runner.run(self, steps)

func _ensure_player() -> void:
	if has_node("Yuansheng"):
		return
	var p := PLAYER_SCENE.instantiate()
	p.name = "Yuansheng"
	add_child(p)
