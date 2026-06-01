## CutsceneRunner: 把一段编排（Array of step dicts）按顺序异步执行。
##
## 步骤格式（dict，type 字段决定行为）：
##   {"type": "dialogue", "line_id": "..."}              ## 阻塞到对话块结束
##   {"type": "wait", "seconds": 1.5}
##   {"type": "walk_to", "node_path": "Yuansheng",       ## 阻塞到角色到位
##     "to": Vector2(100,100), "tolerance": 4.0}
##   {"type": "walk_to_node", "node_path": "Yuansheng",
##     "target_node_path": "Marker", "tolerance": 4.0}
##   {"type": "set_facing", "node_path": "Yuansheng", "facing": "down"}
##   {"type": "spawn_npc", "scene_path": "...", "parent_path": ".",
##     "position": Vector2(0,0), "name": "Wangyan", "character_id": "wangyan"}
##   {"type": "free_node", "node_path": "Wangyan"}
##   {"type": "trigger_event", "event_id": "..."}        ## 等价于 GlobalState.mark_triggered
##   {"type": "set_chapter", "chapter_id": "..."}
##   {"type": "change_scene", "scene_id": "...", "spawn_point": "..."}
##   {"type": "callable", "callable": Callable}          ## 自定义；阻塞当前帧
##
## 主调入口：CutsceneRunner.new().run(scene_root, steps)
class_name CutsceneRunner
extends RefCounted

signal step_started(index: int, step: Dictionary)
signal cutscene_finished()

var _scene_root: Node = null
var _tree: SceneTree = null
var _running: bool = false

func run(scene_root: Node, steps: Array) -> void:
	if _running:
		push_error("[Cutscene] already running")
		return
	_scene_root = scene_root
	_tree = scene_root.get_tree()
	_running = true
	for i in range(steps.size()):
		var step = steps[i]
		step_started.emit(i, step)
		await _run_step(step)
	_running = false
	cutscene_finished.emit()

func _run_step(step: Dictionary) -> void:
	var t: String = step.get("type", "")
	match t:
		"dialogue":
			Dialogue.play(step["line_id"])
			while Dialogue.is_playing():
				await Dialogue.dialogue_finished
		"wait":
			await _tree.create_timer(float(step.get("seconds", 0.0))).timeout
		"walk_to":
			var node: Node2D = _resolve_node(step["node_path"])
			if node == null:
				push_error("[Cutscene] walk_to: node not found %s" % step["node_path"])
				return
			var pos: Vector2 = step.get("to", Vector2.ZERO)
			var tol: float = step.get("tolerance", 4.0)
			if node.has_method("walk_to"):
				await node.walk_to(pos, tol)
			else:
				node.global_position = pos
		"walk_to_node":
			var node: Node2D = _resolve_node(step["node_path"])
			var target: Node2D = _resolve_node(step["target_node_path"])
			if node == null or target == null:
				push_error("[Cutscene] walk_to_node: missing node(s)")
				return
			var tol: float = step.get("tolerance", 4.0)
			if node.has_method("walk_to"):
				await node.walk_to(target.global_position, tol)
			else:
				node.global_position = target.global_position
		"set_facing":
			var node: Node = _resolve_node(step["node_path"])
			if node and node.has_method("set_facing"):
				node.set_facing(step["facing"])
		"spawn_npc":
			var packed: PackedScene = load(step["scene_path"])
			if packed == null:
				push_error("[Cutscene] spawn_npc: cannot load %s" % step["scene_path"])
				return
			var inst := packed.instantiate()
			inst.name = step.get("name", "NPC")
			if step.has("character_id"):
				inst.character_id = step["character_id"]
			var parent: Node = _resolve_node(step.get("parent_path", "."))
			if parent == null:
				parent = _scene_root
			parent.add_child(inst)
			if inst is Node2D and step.has("position"):
				(inst as Node2D).global_position = step["position"]
		"free_node":
			var node: Node = _resolve_node(step["node_path"])
			if node:
				node.queue_free()
		"trigger_event":
			GlobalState.mark_triggered(step["event_id"])
		"set_chapter":
			GlobalState.set_chapter(step["chapter_id"])
		"change_scene":
			await SceneRouter.change_scene(step["scene_id"], step.get("spawn_point", "default"))
			# 老 _scene_root 已被 change_scene_to_file 释放；用 SceneTree 拿新的 current_scene。
			_scene_root = _tree.current_scene
		"callable":
			var cb: Callable = step["callable"]
			var ret = cb.call()
			if ret is Signal:
				await ret
		_:
			push_error("[Cutscene] unknown step type: %s" % t)

func _resolve_node(path: String) -> Node:
	if path == "." or path == "":
		return _scene_root
	if _scene_root == null:
		return null
	return _scene_root.get_node_or_null(path)
