## 第一章 cutscene 编排（数据驱动）。
##
## 把 docs/design/event-flow-prologue-ch1.md §二 的 6 个事件转译成 CutsceneRunner step 数组。
## 沿用 PrologueCutscenes 的模式：dialogue 内部跑完整链（含选项分流 / postcondition 标 trigger），
## cutscene 末尾追加保险性 trigger_event（mark_triggered 是 idempotent，不会重复加变量）。
##
## 事件清单：
##   1. ch1/11_zhengfanhe_help        — cafeteria_steam 蒸饭间认饭盒
##   2. ch1/12_yuekao_ranking         — corridor_stairs 月考排名
##   3. ch1/13_xiaomaibu_first_buy    — xiaomaibu 第一次买零食（三选一）
##   4. ch1/14_caozhengdong_robbery   — corridor_stairs 楼梯口拦截（三选一，C 需 danliang≥3）
##   5. ch1/15_shenzhou7_evening      — classroom_2b 神七出舱晚自习（era_marker: shenzhou7）
##   6. ch1/16_sanlu_classmeeting     — classroom_2b 班会 + 校门口听话（era_marker: sanlu）
##
## 关于 ch1/16 的跨场景叙事：
##   dialogue 链从 /01 教室班会 → /04 narration "班会散了。晚自习后元生路过校门" → /05 校门门卫，
##   是用旁白文本完成跨场景切换，不显式 change_scene。和 prologue/01 父亲送行（home → 山路 → 校门）
##   不同——序章那个事件 dialogue 链在 home 内闭合后再视觉切场；ch1/16 的 dialogue 自带"回宿舍"收尾，
##   player 实际仍在 classroom_2b，无需 change_scene。
##
## 调用方式：CutsceneRunner.new().run(level_root, Ch1Cutscenes.get_cutscene(event_id, level_root))
class_name Ch1Cutscenes
extends RefCounted


## 按 event_id 返回对应 step 数组；未编排的 event 返回空数组。
## scene_root 暂未使用，预留给将来涉及具体 NPC 节点位移 / spawn 的 cutscene。
static func get_cutscene(event_id: String, _scene_root: Node) -> Array:
	match event_id:
		"ch1/11_zhengfanhe_help":
			return _zhengfanhe_help()
		"ch1/12_yuekao_ranking":
			return _yuekao_ranking()
		"ch1/13_xiaomaibu_first_buy":
			return _xiaomaibu_first_buy()
		"ch1/14_caozhengdong_robbery":
			return _caozhengdong_robbery()
		"ch1/15_shenzhou7_evening":
			return _shenzhou7_evening()
		"ch1/16_sanlu_classmeeting":
			return _sanlu_classmeeting()
		_:
			return []


# ============================================================================
# 1.1 蒸饭间认饭盒 — cafeteria_steam
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/07：
#   /01-/04 narration + 王炎对白 → /05 王炎递饭盒（choice 谢谢/沉默）
#     → /06_thanks 或 /06_silent → /07 narration（postcondition: trigger）
# 选项 A "谢谢" 加 stat.koucai +1 / affinity.wangyan +1。
# ============================================================================
static func _zhengfanhe_help() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "ch1/11_zhengfanhe_help/01"},
		{"type": "trigger_event", "event_id": "ch1/11_zhengfanhe_help"},
	]


# ============================================================================
# 1.2 月考排名 — corridor_stairs
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/13 线性无选项：
#   /01-/05 教室念分数（/05 postcondition stat.xuexi +1）
#   /06-/12 走廊围排名表 + 曾建明上二楼借数学报
#   /13 元生内心独白（postcondition: var.xinjie +1, trigger）
# ============================================================================
static func _yuekao_ranking() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "ch1/12_yuekao_ranking/01"},
		{"type": "trigger_event", "event_id": "ch1/12_yuekao_ranking"},
	]


# ============================================================================
# 1.3 小卖部第一次买 — xiaomaibu
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/end：
#   /01-/02 王炎拉进店 → /03 鲍师母（choice A/B/C）
#     → /04_a 摇头不要（var.qianbao_xiuchi +1）
#     → /04_b 赊辣条（var.xinjie +1）
#     → /04_c 跳跳糖（stat.koucai +1, affinity.baosimu +1）
#     → /end（postcondition: trigger）
# ============================================================================
static func _xiaomaibu_first_buy() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "ch1/13_xiaomaibu_first_buy/01"},
		{"type": "trigger_event", "event_id": "ch1/13_xiaomaibu_first_buy"},
	]


# ============================================================================
# 1.4 曹正东抢钱 — corridor_stairs
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/end：
#   /01-/02 narration + 曹正东 → /03 元生内心（choice A/B/C）
#     → /04_a 不吭声（stat.danliang -1, affinity.caozhengdong -1, var.xinjie+2/qianbao_xiuchi+2）
#     → /04_b 喊老师（stat.danliang +1, affinity.baoxianjin +1, affinity.caozhengdong -2, var.xinjie +1）
#     → /04_c 推回去（precondition: stat.danliang.min=3；postcondition stat.danliang +2,
#                    affinity.caozhengdong -3, trigger ch1/14_caozhengdong_robbery/hardline）
#     → /end（postcondition: trigger ch1/14_caozhengdong_robbery）
# 注：选项 C 的 precondition 由 dialogue 系统自动过滤，cutscene 不需要额外处理。
# ============================================================================
static func _caozhengdong_robbery() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "ch1/14_caozhengdong_robbery/01"},
		{"type": "trigger_event", "event_id": "ch1/14_caozhengdong_robbery"},
	]


# ============================================================================
# 1.5 神七晚自习 — classroom_2b（首次时代切片：shenzhou7）
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/end：
#   /01-/05 看翟志刚出舱 + 王炎"以后想干啥" + 曾建明转头一句
#   /06 元生内心（choice 嗯/沉默）
#     A "嗯" 加 affinity.zengjianming +1
#     B 沉默 无变化
#   /end（postcondition: trigger + era_marker shenzhou7）
# 注：era_marker 由 dialogue postcondition 自动加，cutscene 不重复 era_marker。
# ============================================================================
static func _shenzhou7_evening() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "ch1/15_shenzhou7_evening/01"},
		{"type": "trigger_event", "event_id": "ch1/15_shenzhou7_evening"},
	]


# ============================================================================
# 1.6 三鹿班会 — classroom_2b → 校门口（叙事跨场景）（首次时代切片：sanlu）
# ----------------------------------------------------------------------------
# Dialogue 链 /01-/end：
#   /01-/03 班会 鲍先进讲奶粉 + 王炎小声
#   /04 narration "班会散了。晚自习后元生路过校门" — 用旁白完成跨场景切换
#   /05 门卫大爷讲"城里出大事了"（choice 听完/直接走）
#     → /06_listen 加 affinity.menwei_daye +1
#     → /06_pass 元生内心一句
#   /end（postcondition: trigger + era_marker sanlu）"元生回宿舍"
# 注：dialogue 自带跨场景旁白，player 实际仍在 classroom_2b。无需 change_scene。
# era_marker 由 dialogue postcondition 自动加。
# ============================================================================
static func _sanlu_classmeeting() -> Array:
	return [
		{"type": "wait", "seconds": 0.4},
		{"type": "dialogue", "line_id": "ch1/16_sanlu_classmeeting/01"},
		{"type": "trigger_event", "event_id": "ch1/16_sanlu_classmeeting"},
	]
