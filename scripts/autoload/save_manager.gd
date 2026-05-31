## 存档系统。3 个槽位写到 user://saves/slot_<n>.json。
## 序列化：GlobalState 全部状态 + 当前场景 + 主角坐标/朝向 + 时间戳。
## SceneRouter 负责把存档里的 scene_id 转成实际 .tscn 路径。
extends Node

signal saved(slot: int)
signal loaded(slot: int)

const SAVE_DIR := "user://saves"
const SLOT_COUNT := 3
const VERSION := 1

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute(SAVE_DIR)

func has_save(slot: int) -> bool:
	return FileAccess.file_exists(_slot_path(slot))

func get_save_summary(slot: int) -> Dictionary:
	if not has_save(slot):
		return {}
	var data := _read(slot)
	if data == null:
		return {}
	return {
		"chapter": data.get("global_state", {}).get("chapter", "?"),
		"scene_id": data.get("scene_id", "?"),
		"timestamp": data.get("timestamp", ""),
	}

func save(slot: int, scene_id: String, player_pos: Vector2, player_facing: String) -> bool:
	if slot < 0 or slot >= SLOT_COUNT:
		push_error("[SaveManager] invalid slot %d" % slot)
		return false
	var data := {
		"version": VERSION,
		"timestamp": Time.get_datetime_string_from_system(),
		"scene_id": scene_id,
		"player": {
			"x": player_pos.x,
			"y": player_pos.y,
			"facing": player_facing,
		},
		"global_state": GlobalState.to_dict(),
	}
	var f := FileAccess.open(_slot_path(slot), FileAccess.WRITE)
	if f == null:
		push_error("[SaveManager] cannot write %s" % _slot_path(slot))
		return false
	f.store_string(JSON.stringify(data, "  "))
	f.close()
	saved.emit(slot)
	print("[SaveManager] saved slot %d: %s @ (%d, %d)" % [slot, scene_id, int(player_pos.x), int(player_pos.y)])
	return true

func load_slot(slot: int) -> Dictionary:
	if not has_save(slot):
		return {}
	var data := _read(slot)
	if data == null:
		return {}
	GlobalState.from_dict(data.get("global_state", {}))
	loaded.emit(slot)
	print("[SaveManager] loaded slot %d: %s" % [slot, data.get("scene_id", "?")])
	return data

func delete_slot(slot: int) -> void:
	if has_save(slot):
		DirAccess.remove_absolute(_slot_path(slot))

func _read(slot: int) -> Dictionary:
	var path := _slot_path(slot)
	if not FileAccess.file_exists(path):
		return {}
	var text := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("[SaveManager] corrupt save: %s" % path)
		return {}
	return parsed

func _slot_path(slot: int) -> String:
	return "%s/slot_%d.json" % [SAVE_DIR, slot]
