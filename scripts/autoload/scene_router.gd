## 场景路由器：管理 demo 内 scene_id <-> .tscn 路径的映射，
## 处理 fade in/out 切场，按入场点把主角放到正确坐标，
## 与 SaveManager 协作做"存档时记住当前场景"+"读档时回到那个场景"。
extends Node

signal scene_will_change(from_id: String, to_id: String)
signal scene_changed(scene_id: String)

const FADE_DURATION := 0.4

const SCENE_REGISTRY := {
	"demo_room": "res://scenes/main.tscn",
	"home": "res://scenes/levels/home.tscn",
	"mountain_road_autumn": "res://scenes/levels/mountain_road_autumn.tscn",
	"school_gate": "res://scenes/levels/school_gate.tscn",
	"corridor_stairs": "res://scenes/levels/corridor_stairs.tscn",
	"classroom_2b": "res://scenes/levels/classroom_2b.tscn",
	"xiaomaibu": "res://scenes/levels/xiaomaibu.tscn",
	"dorm": "res://scenes/levels/dorm.tscn",
	"cafeteria_steam": "res://scenes/levels/cafeteria_steam.tscn",
}

var current_scene_id: String = "demo_room"

## 待主角生成时定位到的入场点 ID，由 change_scene 设置，由场景的 _ready 读取
var pending_spawn_point: String = ""
## 加载存档时直接覆盖坐标用
var pending_player_pos: Vector2 = Vector2.ZERO
var pending_player_facing: String = "down"
var pending_use_explicit_pos: bool = false

@onready var _fade_layer: CanvasLayer

func _ready() -> void:
	_fade_layer = CanvasLayer.new()
	_fade_layer.layer = 100
	add_child(_fade_layer)
	var rect := ColorRect.new()
	rect.color = Color.BLACK
	rect.modulate.a = 0.0
	rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	rect.name = "FadeRect"
	_fade_layer.add_child(rect)

func change_scene(scene_id: String, spawn_point: String = "default") -> void:
	if not SCENE_REGISTRY.has(scene_id):
		push_error("[SceneRouter] unknown scene_id: %s" % scene_id)
		return
	scene_will_change.emit(current_scene_id, scene_id)
	pending_spawn_point = spawn_point
	pending_use_explicit_pos = false
	await _fade_out()
	var err := get_tree().change_scene_to_file(SCENE_REGISTRY[scene_id])
	if err != OK:
		push_error("[SceneRouter] failed to change scene: %s" % SCENE_REGISTRY[scene_id])
		await _fade_in()
		return
	current_scene_id = scene_id
	await get_tree().process_frame
	await _fade_in()
	scene_changed.emit(scene_id)

func change_scene_to_explicit(scene_id: String, pos: Vector2, facing: String) -> void:
	if not SCENE_REGISTRY.has(scene_id):
		push_error("[SceneRouter] unknown scene_id: %s" % scene_id)
		return
	pending_player_pos = pos
	pending_player_facing = facing
	pending_use_explicit_pos = true
	await _fade_out()
	var err := get_tree().change_scene_to_file(SCENE_REGISTRY[scene_id])
	if err != OK:
		push_error("[SceneRouter] failed: %s" % SCENE_REGISTRY[scene_id])
		await _fade_in()
		return
	current_scene_id = scene_id
	await get_tree().process_frame
	await _fade_in()
	scene_changed.emit(scene_id)

## 场景的 _ready 调这个把主角放到对的位置
func place_player_in_scene(scene_root: Node) -> void:
	var player := scene_root.get_node_or_null("Yuansheng")
	if player == null:
		return
	if pending_use_explicit_pos:
		player.global_position = pending_player_pos
		if player.has_method("set_facing"):
			player.set_facing(pending_player_facing)
		pending_use_explicit_pos = false
		return
	var sp := _find_spawn_point(scene_root, pending_spawn_point)
	if sp == null and pending_spawn_point != "default":
		sp = _find_spawn_point(scene_root, "default")
	if sp != null:
		player.global_position = sp.global_position
		var facing: String = sp.get_meta("facing", "down")
		if player.has_method("set_facing"):
			player.set_facing(facing)

func _find_spawn_point(scene_root: Node, spawn_id: String) -> Node2D:
	var spawn_root := scene_root.get_node_or_null("SpawnPoints")
	if spawn_root == null:
		return null
	for child in spawn_root.get_children():
		if child.name == spawn_id:
			return child as Node2D
	return null

func _fade_out() -> void:
	var rect: ColorRect = _fade_layer.get_node("FadeRect")
	var tween := create_tween()
	tween.tween_property(rect, "modulate:a", 1.0, FADE_DURATION)
	await tween.finished

func _fade_in() -> void:
	var rect: ColorRect = _fade_layer.get_node("FadeRect")
	var tween := create_tween()
	tween.tween_property(rect, "modulate:a", 0.0, FADE_DURATION)
	await tween.finished

## 加载存档时调用：从 SaveManager 拿到 scene_id + player.x/y/facing，跳过去
func resume_from_save(save_data: Dictionary) -> void:
	var scene_id: String = save_data.get("scene_id", "demo_room")
	var p: Dictionary = save_data.get("player", {})
	var pos := Vector2(p.get("x", 0.0), p.get("y", 0.0))
	var facing: String = p.get("facing", "down")
	change_scene_to_explicit(scene_id, pos, facing)
