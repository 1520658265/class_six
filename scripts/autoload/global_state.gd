extends Node

signal stat_changed(stat_id: String, delta: int, new_value: int)
signal var_changed(var_id: String, delta: int, new_value: int)
signal affinity_changed(npc_id: String, delta: int, new_value: int)
signal event_triggered(event_id: String)
signal era_marker_added(marker_id: String)
signal chapter_changed(new_chapter: String)

const STATS_CONFIG := {
	"xuexi":    {"init": 3, "min": 0, "max": 10},
	"danliang": {"init": 1, "min": 0, "max": 10},
	"koucai":   {"init": 1, "min": 0, "max": 10},
	"tili":     {"init": 3, "min": 0, "max": 10},
}

const VARS_CONFIG := {
	"xinjie":          {"init": 0, "min": 0, "max": 20},
	"kaguodu_xinli":   {"init": 0, "min": 0, "max": 10},
	"qianbao_xiuchi":  {"init": 0, "min": 0, "max": 20},
}

const AFFINITY_INIT := {
	"baoxianjin": 0, "baosimu": 1, "wangyan": 1, "zengjianming": 1,
	"caozhengdong": -3, "huxiaodong": 0, "zhanglei": 0, "lijing": 0,
	"menwei_daye": 0, "fuqin": 5, "muqin": 5, "jiejie": 8,
}

const AFFINITY_MIN := -10
const AFFINITY_MAX := 10

var _stats: Dictionary = {}
var _vars: Dictionary = {}
var _affinity: Dictionary = {}
var _triggered: Dictionary = {}
var _era_markers: Dictionary = {}
var _chapter: String = "prologue"

func _ready() -> void:
	reset_to_initial()

func reset_to_initial() -> void:
	_stats.clear()
	for id in STATS_CONFIG:
		_stats[id] = STATS_CONFIG[id].init
	_vars.clear()
	for id in VARS_CONFIG:
		_vars[id] = VARS_CONFIG[id].init
	_affinity.clear()
	for id in AFFINITY_INIT:
		_affinity[id] = AFFINITY_INIT[id]
	_triggered.clear()
	_era_markers.clear()
	_chapter = "prologue"

func get_stat(id: String) -> int:
	return _stats.get(id, 0)

func change_stat(id: String, delta: int) -> void:
	if not STATS_CONFIG.has(id):
		push_error("[GlobalState] unknown stat: %s" % id)
		return
	var cfg: Dictionary = STATS_CONFIG[id]
	var new_value: int = clamp(_stats[id] + delta, cfg.min, cfg.max)
	if new_value == _stats[id]:
		return
	_stats[id] = new_value
	stat_changed.emit(id, delta, new_value)

func get_var(id: String) -> int:
	return _vars.get(id, 0)

func change_var(id: String, delta: int) -> void:
	if not VARS_CONFIG.has(id):
		push_error("[GlobalState] unknown var: %s" % id)
		return
	var cfg: Dictionary = VARS_CONFIG[id]
	var new_value: int = clamp(_vars[id] + delta, cfg.min, cfg.max)
	if new_value == _vars[id]:
		return
	_vars[id] = new_value
	var_changed.emit(id, delta, new_value)

func get_affinity(npc_id: String) -> int:
	return _affinity.get(npc_id, 0)

func change_affinity(npc_id: String, delta: int) -> void:
	var cur: int = _affinity.get(npc_id, 0)
	var new_value: int = clamp(cur + delta, AFFINITY_MIN, AFFINITY_MAX)
	if new_value == cur:
		return
	_affinity[npc_id] = new_value
	affinity_changed.emit(npc_id, delta, new_value)

func has_triggered(event_id: String) -> bool:
	return _triggered.has(event_id)

func mark_triggered(event_id: String) -> void:
	if _triggered.has(event_id):
		return
	_triggered[event_id] = true
	event_triggered.emit(event_id)

func has_era_marker(marker_id: String) -> bool:
	return _era_markers.has(marker_id)

func mark_era_marker(marker_id: String) -> void:
	if _era_markers.has(marker_id):
		return
	_era_markers[marker_id] = true
	era_marker_added.emit(marker_id)

func get_chapter() -> String:
	return _chapter

func set_chapter(chapter_id: String) -> void:
	if _chapter == chapter_id:
		return
	_chapter = chapter_id
	chapter_changed.emit(chapter_id)

func to_dict() -> Dictionary:
	return {
		"stats": _stats.duplicate(true),
		"vars": _vars.duplicate(true),
		"affinity": _affinity.duplicate(true),
		"triggered": _triggered.keys(),
		"era_markers": _era_markers.keys(),
		"chapter": _chapter,
	}

func from_dict(data: Dictionary) -> void:
	reset_to_initial()
	for id in data.get("stats", {}):
		if STATS_CONFIG.has(id):
			_stats[id] = data["stats"][id]
	for id in data.get("vars", {}):
		if VARS_CONFIG.has(id):
			_vars[id] = data["vars"][id]
	for id in data.get("affinity", {}):
		_affinity[id] = data["affinity"][id]
	for ev in data.get("triggered", []):
		_triggered[ev] = true
	for mk in data.get("era_markers", []):
		_era_markers[mk] = true
	_chapter = data.get("chapter", "prologue")
