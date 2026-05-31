class_name GlobalState
extends Node
##
## GlobalState autoload — Stat System v1 contract per ADR-0001.
##
## Owns 4 visible stats (xuexi / danliang / koucai / tili), 3 hidden vars
## (xinjie / kaguodu_xinli / qianbao_xiuchi), 12 NPC affinities, the
## current chapter, the triggered-events set, and the era-marker set.
## Broadcasts every accepted change via 6 typed signals. Foundation layer,
## zero external dependencies.
##
## Contract sources:
## - design/gdd/stat-system.md (§C–§H)
## - docs/architecture/adr-0001-stat-system-contract.md (§Implementation Guidelines)
##
## Subscribers MUST connect with Object.CONNECT_DEFERRED (§F.5 invariant).
## Reentrant change_* calls from inside a *_changed handler are blocked at
## runtime by the _emit_depth guard.

# ── Constants ─────────────────────────────────────────────────────────────

## Visible stat configs. Each entry: {init, min, max} with min ≤ init ≤ max
## enforced at startup by _validate_configs (§F.5 R-S6).
const STATS_CONFIG: Dictionary[String, Dictionary] = {
	"xuexi":    {"init": 3, "min": 0, "max": 10},
	"danliang": {"init": 1, "min": 0, "max": 10},
	"koucai":   {"init": 1, "min": 0, "max": 10},
	"tili":     {"init": 3, "min": 0, "max": 10},
}

## Hidden var configs. xinjie / qianbao_xiuchi max=20 are PROVISIONAL
## (终章 scenarios will reconfirm; downstream MUST NOT hardcode the bound,
## see §F.5 invariant).
const VARS_CONFIG: Dictionary[String, Dictionary] = {
	"xinjie":         {"init": 0, "min": 0, "max": 20},
	"kaguodu_xinli":  {"init": 0, "min": 0, "max": 10},
	"qianbao_xiuchi": {"init": 0, "min": 0, "max": 20},
}

## Per-NPC affinity configs. caozhengdong.min=-15 (宿敌 head room) and
## jiejie.max=+15 (被托住 head room) are pillar-bearing overrides; everyone
## else uses default ±10. New NPCs MUST be declared here before any
## change_affinity call (§E.2 strict semantics: unknown id → push_error).
const AFFINITY_CONFIG: Dictionary[String, Dictionary] = {
	"baoxianjin":   {"init": 0,  "min": -10, "max": 10},
	"baosimu":      {"init": 1,  "min": -10, "max": 10},
	"wangyan":      {"init": 1,  "min": -10, "max": 10},
	"zengjianming": {"init": 1,  "min": -10, "max": 10},
	"caozhengdong": {"init": -3, "min": -15, "max": 10},
	"huxiaodong":   {"init": 0,  "min": -10, "max": 10},
	"zhanglei":     {"init": 0,  "min": -10, "max": 10},
	"lijing":       {"init": 0,  "min": -10, "max": 10},
	"menwei_daye":  {"init": 0,  "min": -10, "max": 10},
	"fuqin":        {"init": 5,  "min": -10, "max": 10},
	"muqin":        {"init": 5,  "min": -10, "max": 10},
	"jiejie":       {"init": 8,  "min": -10, "max": 15},
}

## Fallback bounds. Only consulted if a future code path looks up an NPC
## that is not in AFFINITY_CONFIG; current contract (§E.2 修订) is to
## push_error and return, so these are effectively unused at runtime.
const AFFINITY_DEFAULT_MIN: int = -10
const AFFINITY_DEFAULT_MAX: int = 10

## |delta| > TYPO_WARN_DELTA triggers a push_warning after a successful
## change_* (§E.10). Threshold 5 leaves room for legitimate ±3..±5 story
## bumps; symbol comparison (delta > T or delta < -T) avoids the
## abs(INT64_MIN) overflow trap.
const TYPO_WARN_DELTA: int = 5

const _LEGAL_CHAPTERS: Array[String] = ["prologue", "ch1", "ch1_done"]

# ── Signals (v1 frozen) ───────────────────────────────────────────────────

## stat_changed broadcasts only when effective_delta ≠ 0 (i.e. clamped
## new_value differs from old_value). requested_delta carries the *raw*
## delta the caller passed in — UI may compare effective vs requested
## to detect "half-clamped" boundary cases.
signal stat_changed(stat_id: String, old_value: int, new_value: int, requested_delta: int)
signal var_changed(var_id: String, old_value: int, new_value: int, requested_delta: int)
signal affinity_changed(npc_id: String, old_value: int, new_value: int, requested_delta: int)
signal event_triggered(event_id: String)
signal era_marker_added(marker_id: String)
signal chapter_changed(old_chapter: String, new_chapter: String)

# ── Private state ─────────────────────────────────────────────────────────

var _stats: Dictionary[String, int] = {}
var _vars: Dictionary[String, int] = {}
var _affinity: Dictionary[String, int] = {}
## Set-as-Dict: value is always true; only keys carry meaning.
var _triggered: Dictionary[String, bool] = {}
## Set-as-Dict: value is always true; only keys carry meaning.
var _era_markers: Dictionary[String, bool] = {}
var _chapter: String = "prologue"

## Reentrancy depth counter. Incremented before each *_changed emit and
## decremented after; change_* entry checks > 0 to refuse reentrant calls
## from inside signal handlers (§E.3 / §C.6 Round-2).
var _emit_depth: int = 0

# ── Built-in virtuals ─────────────────────────────────────────────────────

func _ready() -> void:
	# Validate configs before any container is populated. assert(false)
	# inside _validate_configs blocks startup if any min/init/max invariant
	# is violated (§F.5 R-S6).
	_validate_configs(STATS_CONFIG, VARS_CONFIG, AFFINITY_CONFIG)
	reset_to_initial()

# ── Public API: stats (visible) ───────────────────────────────────────────

## Returns the current value of a visible stat. Unknown id returns 0
## without raising (read-path tolerance, §E.2).
func get_stat(id: String) -> int:
	return _stats.get(id, 0)

## Adds delta to the named stat with clamp + signal semantics:
## 1. Refuses reentrant calls from inside any *_changed handler (push_error).
## 2. Unknown id → push_error and return (§E.2).
## 3. Pre-clamps delta to [min-max, max-min] for INT64 overflow safety (D.1).
## 4. Emits stat_changed only when effective_delta ≠ 0 (D.3).
## 5. requested_delta in payload is the *original* delta, not safe_delta.
## 6. After a real broadcast, emits push_warning if |delta| > TYPO_WARN_DELTA.
func change_stat(id: String, delta: int) -> void:
	if _emit_depth > 0:
		push_error("[GlobalState] re-entrant change_stat during signal handler — use call_deferred")
		return
	if not STATS_CONFIG.has(id):
		push_error("[GlobalState] unknown stat: %s" % id)
		return
	var cfg: Dictionary = STATS_CONFIG[id]
	var cfg_min: int = cfg["min"]
	var cfg_max: int = cfg["max"]
	var old_value: int = _stats[id]
	var safe_delta: int = clampi(delta, cfg_min - cfg_max, cfg_max - cfg_min)
	var new_value: int = clampi(old_value + safe_delta, cfg_min, cfg_max)
	if new_value == old_value:
		return
	_stats[id] = new_value
	_emit_depth += 1
	stat_changed.emit(id, old_value, new_value, delta)
	_emit_depth -= 1
	if delta > TYPO_WARN_DELTA or delta < -TYPO_WARN_DELTA:
		push_warning("[GlobalState] large delta on %s: %d (typical range [-%d, +%d])"
			% [id, delta, TYPO_WARN_DELTA, TYPO_WARN_DELTA])

# ── Public API: vars (hidden) ─────────────────────────────────────────────

## Returns the current value of a hidden var. Unknown id returns 0
## without raising (read-path tolerance, §E.2).
func get_var(id: String) -> int:
	return _vars.get(id, 0)

## Adds delta to the named hidden var. Same semantics as change_stat
## (D.1 overflow safety, D.3 broadcast predicate, E.10 typo warning).
func change_var(id: String, delta: int) -> void:
	if _emit_depth > 0:
		push_error("[GlobalState] re-entrant change_var during signal handler — use call_deferred")
		return
	if not VARS_CONFIG.has(id):
		push_error("[GlobalState] unknown var: %s" % id)
		return
	var cfg: Dictionary = VARS_CONFIG[id]
	var cfg_min: int = cfg["min"]
	var cfg_max: int = cfg["max"]
	var old_value: int = _vars[id]
	var safe_delta: int = clampi(delta, cfg_min - cfg_max, cfg_max - cfg_min)
	var new_value: int = clampi(old_value + safe_delta, cfg_min, cfg_max)
	if new_value == old_value:
		return
	_vars[id] = new_value
	_emit_depth += 1
	var_changed.emit(id, old_value, new_value, delta)
	_emit_depth -= 1
	if delta > TYPO_WARN_DELTA or delta < -TYPO_WARN_DELTA:
		push_warning("[GlobalState] large delta on %s: %d (typical range [-%d, +%d])"
			% [id, delta, TYPO_WARN_DELTA, TYPO_WARN_DELTA])

# ── Public API: affinity (hidden, per-NPC) ────────────────────────────────

## Returns the current affinity for an NPC. Unknown npc returns 0
## without raising (read-path tolerance, §E.2). Use AFFINITY_CONFIG to
## look up bounds when displaying.
func get_affinity(npc_id: String) -> int:
	return _affinity.get(npc_id, 0)

## Adds delta to an NPC's affinity using per-NPC bounds from AFFINITY_CONFIG
## (§C.4 / D.2). Unknown npc_id → push_error and return (§E.2 修订: write
## path is strict so save round-trips do not pollute state with typos).
func change_affinity(npc_id: String, delta: int) -> void:
	if _emit_depth > 0:
		push_error("[GlobalState] re-entrant change_affinity during signal handler — use call_deferred")
		return
	if not AFFINITY_CONFIG.has(npc_id):
		push_error("[GlobalState] unknown npc: %s" % npc_id)
		return
	var cfg: Dictionary = AFFINITY_CONFIG[npc_id]
	var cfg_min: int = cfg["min"]
	var cfg_max: int = cfg["max"]
	var old_value: int = _affinity[npc_id]
	var safe_delta: int = clampi(delta, cfg_min - cfg_max, cfg_max - cfg_min)
	var new_value: int = clampi(old_value + safe_delta, cfg_min, cfg_max)
	if new_value == old_value:
		return
	_affinity[npc_id] = new_value
	_emit_depth += 1
	affinity_changed.emit(npc_id, old_value, new_value, delta)
	_emit_depth -= 1
	if delta > TYPO_WARN_DELTA or delta < -TYPO_WARN_DELTA:
		push_warning("[GlobalState] large delta on %s: %d (typical range [-%d, +%d])"
			% [npc_id, delta, TYPO_WARN_DELTA, TYPO_WARN_DELTA])

# ── Public API: triggered events (Set-as-Dict) ────────────────────────────

## Has the named event been triggered before? Idempotent read.
func has_triggered(event_id: String) -> bool:
	return _triggered.has(event_id)

## Marks an event as triggered. Repeat calls are silently ignored
## (§E.4): only the first call broadcasts event_triggered.
func mark_triggered(event_id: String) -> void:
	if _triggered.has(event_id):
		return
	_triggered[event_id] = true
	_emit_depth += 1
	event_triggered.emit(event_id)
	_emit_depth -= 1

# ── Public API: era markers (Set-as-Dict) ─────────────────────────────────

## Has the named era marker been lit before? Idempotent read.
func has_era_marker(marker_id: String) -> bool:
	return _era_markers.has(marker_id)

## Marks an era marker as lit. Repeat calls are silently ignored
## (§E.4): only the first call broadcasts era_marker_added.
func mark_era_marker(marker_id: String) -> void:
	if _era_markers.has(marker_id):
		return
	_era_markers[marker_id] = true
	_emit_depth += 1
	era_marker_added.emit(marker_id)
	_emit_depth -= 1

# ── Public API: chapter ───────────────────────────────────────────────────

## Returns the current chapter id. Default is "prologue".
func get_chapter() -> String:
	return _chapter

## Switches the current chapter and broadcasts chapter_changed with both
## the old and new id (§C.6 Round-2: 2-arg payload). Same-id calls are
## silently ignored. Note: write path does NOT validate the value
## (§C.5 / §E.5: business-rule, code-review-enforced); from_dict is the
## only legal way to set arbitrary values, see §F.5.
func set_chapter(chapter_id: String) -> void:
	if _chapter == chapter_id:
		return
	var old_chapter: String = _chapter
	_chapter = chapter_id
	_emit_depth += 1
	chapter_changed.emit(old_chapter, chapter_id)
	_emit_depth -= 1

# ── Public API: serialization ─────────────────────────────────────────────

## Snapshots all 6 collections into a flat Dictionary suitable for JSON.
## Triggered / era_marker keys are sorted to give byte-stable output for
## the same logical state (§E.8): round-trip diffs and git diffs stay
## meaningful even when insertion order varied.
func to_dict() -> Dictionary:
	var trig_keys: Array = _triggered.keys()
	trig_keys.sort()
	var era_keys: Array = _era_markers.keys()
	era_keys.sort()
	return {
		"stats":       _stats.duplicate(true),
		"vars":        _vars.duplicate(true),
		"affinity":    _affinity.duplicate(true),
		"triggered":   trig_keys,
		"era_markers": era_keys,
		"chapter":     _chapter,
	}

## Self-healing load (§E.6 修订). Behaviour:
## - Resets all collections first.
## - For each known stat / var / affinity entry: cast to int (defends against
##   JSON 999.0 floats), clamp to that id's [min, max], push_warning if the
##   raw value differed from the clamped value, then write.
## - Unknown stat / var / npc ids → skip + push_warning.
## - triggered / era_markers accept Array (canonical) OR Dictionary
##   (legacy), or any other type (skip + push_warning). Falsy values
##   inside a Dict are still treated as "marked" with a push_warning,
##   for forward-compatibility with old saves.
## - Out-of-range chapter is written verbatim with a push_warning
##   (§E.5: white-list expands as chapters ship).
## - Emits NO *_changed signals — load is a silent path (§F.5 / §E.7).
##   UI subscribers are expected to re-read state on load_finished.
func from_dict(data: Dictionary) -> void:
	reset_to_initial()
	_load_int_dict(data.get("stats", {}), STATS_CONFIG, _stats, "stat")
	_load_int_dict(data.get("vars", {}), VARS_CONFIG, _vars, "var")
	_load_int_dict(data.get("affinity", {}), AFFINITY_CONFIG, _affinity, "npc")
	_load_set(data.get("triggered", []), _triggered, "triggered")
	_load_set(data.get("era_markers", []), _era_markers, "era_markers")
	var ch_raw: Variant = data.get("chapter", "prologue")
	if typeof(ch_raw) != TYPE_STRING:
		push_warning("[GlobalState] from_dict: chapter field has unexpected type, defaulting to prologue")
		_chapter = "prologue"
	else:
		var ch: String = ch_raw
		if not _LEGAL_CHAPTERS.has(ch):
			push_warning("[GlobalState] from_dict: out-of-range chapter %s" % ch)
		_chapter = ch

## Resets all 6 collections to their config-declared init values.
## Emits NO signals — used by _ready and from_dict (§E.7).
func reset_to_initial() -> void:
	_stats.clear()
	for id in STATS_CONFIG:
		_stats[id] = STATS_CONFIG[id]["init"]
	_vars.clear()
	for id in VARS_CONFIG:
		_vars[id] = VARS_CONFIG[id]["init"]
	_affinity.clear()
	for npc_id in AFFINITY_CONFIG:
		_affinity[npc_id] = AFFINITY_CONFIG[npc_id]["init"]
	_triggered.clear()
	_era_markers.clear()
	_chapter = "prologue"

# ── Private helpers ───────────────────────────────────────────────────────

## Self-healing loader for stats / vars / affinity. cfg is the matching
## *_CONFIG dict; target is the live store; label is "stat" / "var" / "npc"
## for diagnostic messages. Caller guarantees source is whatever
## from_dict received (may be Dict-typed or any Variant from JSON).
func _load_int_dict(source: Variant, cfg: Dictionary, target: Dictionary, label: String) -> void:
	if not (source is Dictionary):
		if source != null:
			push_warning("[GlobalState] from_dict: %s field has unexpected type, ignored" % label)
		return
	var src: Dictionary = source
	for id in src:
		if not cfg.has(id):
			push_warning("[GlobalState] from_dict: unknown %s %s — skipped" % [label, id])
			continue
		var entry: Dictionary = cfg[id]
		var entry_min: int = entry["min"]
		var entry_max: int = entry["max"]
		var raw: Variant = src[id]
		var v: int = int(raw)
		var clamped: int = clampi(v, entry_min, entry_max)
		if clamped != v:
			push_warning("[GlobalState] from_dict: %s out-of-range %s, clamped to %d"
				% [id, str(raw), clamped])
		target[id] = clamped

## Set-as-Dict loader. Accepts Array (canonical) or Dictionary (legacy);
## anything else is dropped with a push_warning (§E.8).
func _load_set(source: Variant, target: Dictionary, label: String) -> void:
	if source is Array:
		var arr: Array = source
		for k in arr:
			target[k] = true
		return
	if source is Dictionary:
		var dict: Dictionary = source
		for k in dict.keys():
			if not dict[k]:
				push_warning("[GlobalState] from_dict: %s key with non-true value, treating as triggered: %s"
					% [label, k])
			target[k] = true
		return
	push_warning("[GlobalState] from_dict: %s field has unexpected type, ignored" % label)

## Verifies that every entry in the three configs satisfies
## min ≤ init ≤ max and min ≤ max. Returns true on success. On any
## failure, push_error is emitted for each offender and assert(false)
## blocks startup (§F.5 R-S6, §H.19). Exposed as a method (not inlined
## in _ready) so unit tests can inject synthetic configs to verify
## each failure mode in isolation.
func _validate_configs(stats_cfg: Dictionary, vars_cfg: Dictionary, aff_cfg: Dictionary) -> bool:
	var ok: bool = true
	var groups: Array[Dictionary] = [stats_cfg, vars_cfg, aff_cfg]
	for ds: Dictionary in groups:
		for id in ds:
			var entry: Dictionary = ds[id]
			var entry_min: int = entry["min"]
			var entry_init: int = entry["init"]
			var entry_max: int = entry["max"]
			if not (entry_min <= entry_init and entry_init <= entry_max and entry_min <= entry_max):
				push_error("[GlobalState] config invariant violated: %s min=%d init=%d max=%d"
					% [id, entry_min, entry_init, entry_max])
				ok = false
	assert(ok, "[GlobalState] config validation failed — see push_error above")
	return ok
