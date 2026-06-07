## 序章 cutscene 编排（数据驱动）。
##
## 把 docs/design/event-flow-prologue-ch1.md §一 的 8 个事件转译成 CutsceneRunner step 数组。
## 因 step 含 Vector2 / Callable 等 JSON 不可表达类型，故用 GDScript 而非 JSON。
##
## 事件清单（含 event_id 的才有 cutscene 条目；其余由 level_base 章节标题/场景门处理）：
##   2. prologue/01_father_send_off       — home → mountain_road_autumn → school_gate
##   4. prologue/03_corridor_overhear     — corridor_stairs 走廊路过老师议论
##   5. prologue/02_classroom_arrival     — classroom_2b 班会 + 自我介绍
##   6. prologue/04_xiaomaibu_first_pass  — xiaomaibu 元生路过
##   7. prologue/05_dorm_assigned         — dorm 分铺 + set_chapter ch1
##
## 跳过的事件（在 level_base / SceneRouter / UIRoot 流程里已隐式处理）：
##   1. 章节开始：`_intro/prologue_title` 章节标题 + 道具 log（见 level_base._after_ready）
##   3. 走过校门：scene_door 自动路由 school_gate → corridor_stairs
##   8. 走到第三排：classroom_2b 已挂 SavePoint；set_chapter ch1 由 #7 dialogue postcondition 完成
##
## 调用方式：CutsceneRunner.new().run(level_root, PrologueCutscenes.get_cutscene(event_id))
class_name PrologueCutscenes
extends RefCounted


## 按 event_id 返回对应 step 数组；未编排的 event 返回空数组。
static func get_cutscene(event_id: String) -> Array:
	match event_id:
		"prologue/01_father_send_off":
			return _father_send_off()
		"prologue/03_corridor_overhear":
			return _corridor_overhear()
		"prologue/02_classroom_arrival":
			return _classroom_arrival()
		"prologue/04_xiaomaibu_first_pass":
			return _xiaomaibu_first_pass()
		"prologue/05_dorm_assigned":
			return _dorm_assigned()
		_:
			return []


# ============================================================================
# 事件 #2 父亲送行 — home → mountain_road_autumn → school_gate
# ----------------------------------------------------------------------------
# Dialogue 链 /01..../11 已自洽（postcondition 在 /07 标记 trigger）：
#   /01 旁白 → /02-/05 母亲嘱咐（含选项 affinity_muqin±）→ /06_* → /07 旁白(trigger)
#   → /08 山路旁白 → /09 父亲 → /10 元生选项（含 affinity_fuqin±）→ /11 收尾
# 因 dialogue 链不可中途切换 line，故全段在 home 播放完毕后再走视觉切场。
# ============================================================================
static func _father_send_off() -> Array:
	return [
		{"type": "wait", "seconds": 0.3},
		{"type": "dialogue", "line_id": "prologue/01_father_send_off/01"},
		{"type": "wait", "seconds": 0.4},
		{"type": "change_scene", "scene_id": "mountain_road_autumn", "spawn_point": "from_home"},
		{"type": "wait", "seconds": 1.2},
		{"type": "change_scene", "scene_id": "school_gate", "spawn_point": "from_mountain"},
		# 防御性 trigger（dialogue 链 /07 postcondition 已 mark，重复 mark 是 idempotent）
		{"type": "trigger_event", "event_id": "prologue/01_father_send_off"},
	]


# ============================================================================
# 事件 #4 走廊偷听 — corridor_stairs
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/04 在 /04 postcondition 完成 var.kaguodu_xinli +1 与 trigger。
# Demo 简化：玩家从 school_gate 走过门进入即触发，无需走位 step。
# ============================================================================
static func _corridor_overhear() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "prologue/03_corridor_overhear/01"},
		{"type": "trigger_event", "event_id": "prologue/03_corridor_overhear"},
	]


# ============================================================================
# 事件 #5 班会自我介绍 — classroom_2b
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/10：/08 含选项（"主动报全名"→ stat.koucai +1 / affinity.baoxianjin +1），
# /10 postcondition 标记 trigger 与 era_marker.kaixue。
# 教室内 Baoxianjin / Zengjianming / Wangyan NPC 节点已在场景里站桩。
# ============================================================================
static func _classroom_arrival() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "prologue/02_classroom_arrival/01"},
		{"type": "trigger_event", "event_id": "prologue/02_classroom_arrival"},
	]


# ============================================================================
# 事件 #6 小卖部路过 — xiaomaibu
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/08 在 /07 postcondition 完成 var.qianbao_xiuchi +1 与 trigger。
# Baosimu NPC 已在场景里。王炎在对白里走位（非视觉 npc），demo 简化为纯文本。
# ============================================================================
static func _xiaomaibu_first_pass() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "prologue/04_xiaomaibu_first_pass/01"},
		{"type": "trigger_event", "event_id": "prologue/04_xiaomaibu_first_pass"},
	]


# ============================================================================
# 事件 #7 宿舍分铺 — dorm（序章终点，转章 ch1）
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/06：/03 含选项（"主动跟王炎打招呼"→ stat.koucai +1 / affinity.wangyan +1），
# /06 postcondition 标记 trigger 与 set_chapter "ch1"。
# 章节切到 ch1 后 UIRoot._on_chapter_changed 自动弹"第一章 · 蒸饭盒里的秋天"标题卡。
# Wangyan_Dorm NPC 节点已在场景中（dialogue_line_id 是 ch1 支线，prologue 期间不冲突）。
# ============================================================================
static func _dorm_assigned() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "prologue/05_dorm_assigned/01"},
		{"type": "trigger_event", "event_id": "prologue/05_dorm_assigned"},
	]
