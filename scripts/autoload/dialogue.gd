## 对话系统 autoload。
## 加载 data/dialogue/<chapter_id>.json，按 line_id 推进。
## 条件检查走 GlobalState；UI 由 DialogueBox 节点订阅信号呈现。
extends Node

signal line_entered(line: Dictionary)
signal choices_offered(line: Dictionary, available_indices: Array)
signal dialogue_finished(start_line_id: String)

const DATA_DIR := "res://data/dialogue"

var _scripts: Dictionary = {}  ## chapter_id -> {lines: ...}
var _current_chapter: String = ""
var _current_line_id: String = ""
var _start_line_id: String = ""
var _is_playing: bool = false
var _awaiting_choice: bool = false
var _last_available_indices: Array = []

func play(start_line_id: String) -> void:
	if _is_playing:
		push_error("[Dialogue] already playing %s, ignoring %s" % [_current_line_id, start_line_id])
		return
	var chapter_id := _chapter_from_line_id(start_line_id)
	if chapter_id == "":
		push_error("[Dialogue] cannot determine chapter from line id: %s" % start_line_id)
		return
	if not _scripts.has(chapter_id):
		_load_script(chapter_id)
	if not _scripts.has(chapter_id):
		return
	if not _scripts[chapter_id]["lines"].has(start_line_id):
		push_error("[Dialogue] line not found: %s" % start_line_id)
		return
	_current_chapter = chapter_id
	_start_line_id = start_line_id
	_is_playing = true
	_enter_line(start_line_id)

func advance() -> void:
	if not _is_playing or _awaiting_choice:
		return
	var line: Dictionary = _scripts[_current_chapter]["lines"][_current_line_id]
	var next_id = line.get("next", null)
	if next_id == null:
		_finish()
		return
	_enter_line(next_id)

func choose(index: int) -> void:
	if not _awaiting_choice:
		return
	if index < 0 or index >= _last_available_indices.size():
		push_error("[Dialogue] choice index %d out of available %s" % [index, str(_last_available_indices)])
		return
	var line: Dictionary = _scripts[_current_chapter]["lines"][_current_line_id]
	var actual_index: int = _last_available_indices[index]
	var choice: Dictionary = line["choices"][actual_index]
	_apply_postconditions(choice.get("postconditions", {}))
	_awaiting_choice = false
	_last_available_indices = []
	var next_id: String = choice.get("next", "")
	if next_id == "":
		_finish()
		return
	_enter_line(next_id)

func is_playing() -> bool:
	return _is_playing

func _enter_line(line_id: String) -> void:
	if not _scripts[_current_chapter]["lines"].has(line_id):
		push_error("[Dialogue] missing line: %s" % line_id)
		_finish()
		return
	_current_line_id = line_id
	var line: Dictionary = _scripts[_current_chapter]["lines"][line_id]
	if not _check_preconditions(line.get("preconditions", {})):
		push_error("[Dialogue] preconditions failed at line %s" % line_id)
		_finish()
		return
	_apply_postconditions(line.get("postconditions", {}))
	line_entered.emit(line)
	if line.has("choices") and line["choices"] is Array:
		var available: Array = []
		for i in range(line["choices"].size()):
			var ch: Dictionary = line["choices"][i]
			if _check_preconditions(ch.get("preconditions", {})):
				available.append(i)
		_last_available_indices = available
		_awaiting_choice = true
		choices_offered.emit(line, available)

func _finish() -> void:
	var s := _start_line_id
	_is_playing = false
	_awaiting_choice = false
	_current_line_id = ""
	_start_line_id = ""
	_last_available_indices = []
	dialogue_finished.emit(s)

func _check_preconditions(pre: Dictionary) -> bool:
	if pre == null or pre.is_empty():
		return true
	for sid in pre.get("stat", {}):
		var range_dict: Dictionary = pre["stat"][sid]
		var v := GlobalState.get_stat(sid)
		if range_dict.has("min") and v < int(range_dict["min"]):
			return false
		if range_dict.has("max") and v > int(range_dict["max"]):
			return false
	for vid in pre.get("var", {}):
		var range_dict: Dictionary = pre["var"][vid]
		var v := GlobalState.get_var(vid)
		if range_dict.has("min") and v < int(range_dict["min"]):
			return false
		if range_dict.has("max") and v > int(range_dict["max"]):
			return false
	for nid in pre.get("affinity", {}):
		var range_dict: Dictionary = pre["affinity"][nid]
		var v := GlobalState.get_affinity(nid)
		if range_dict.has("min") and v < int(range_dict["min"]):
			return false
		if range_dict.has("max") and v > int(range_dict["max"]):
			return false
	for ev in pre.get("triggered", []):
		if not GlobalState.has_triggered(ev):
			return false
	for ev in pre.get("not_triggered", []):
		if GlobalState.has_triggered(ev):
			return false
	for mk in pre.get("era_marker", []):
		if not GlobalState.has_era_marker(mk):
			return false
	if pre.has("chapter"):
		var allowed: Array = pre["chapter"]
		if GlobalState.get_chapter() not in allowed:
			return false
	return true

func _apply_postconditions(post: Dictionary) -> void:
	if post == null or post.is_empty():
		return
	for sid in post.get("stat", {}):
		GlobalState.change_stat(sid, int(post["stat"][sid]))
	for vid in post.get("var", {}):
		GlobalState.change_var(vid, int(post["var"][vid]))
	for nid in post.get("affinity", {}):
		GlobalState.change_affinity(nid, int(post["affinity"][nid]))
	for ev in post.get("trigger", []):
		GlobalState.mark_triggered(ev)
	for mk in post.get("era_marker", []):
		GlobalState.mark_era_marker(mk)
	if post.has("set_chapter"):
		GlobalState.set_chapter(post["set_chapter"])
	for item_id in post.get("give_item", []):
		print("[Dialogue] give_item %s (demo: log only)" % item_id)

func _load_script(chapter_id: String) -> void:
	var path := "%s/%s.json" % [DATA_DIR, chapter_id]
	if not FileAccess.file_exists(path):
		push_error("[Dialogue] script file not found: %s" % path)
		return
	var text := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("[Dialogue] root not a dict: %s" % path)
		return
	if not parsed.has("lines") or typeof(parsed["lines"]) != TYPE_DICTIONARY:
		push_error("[Dialogue] no 'lines' dict: %s" % path)
		return
	_scripts[chapter_id] = parsed
	print("[Dialogue] loaded %s (%d lines)" % [chapter_id, parsed["lines"].size()])

func _chapter_from_line_id(line_id: String) -> String:
	var slash := line_id.find("/")
	if slash <= 0:
		return ""
	return line_id.substr(0, slash)
