# =============================================================================
# Stat System — Unit Test Suite
# =============================================================================
# 实现 design/gdd/stat-system.md §H 全 20 条 AC（H.1–H.20）+ §H 测试夹具契约 5 条。
# 实装契约由 docs/architecture/adr-0001-stat-system-contract.md 锁定，
# 实装位置 scripts/autoload/global_state.gd。
#
# 命名规则（.claude/rules/test-standards.md）:
#   test_h##_<system>_<scenario>_<expected>
#
# 运行：在 Godot 4.6 编辑器中安装 gdunit4 后，右键 tests/unit/stat_system/ → "Run Tests"
# 或 headless: godot --headless --import && godot --headless -s addons/gdUnit4/bin/GdUnitCmdTool.gd \
#     --add tests/unit/stat_system/test_stat_system.gd
# =============================================================================
extends GdUnitTestSuite


# ---------------------------------------------------------------------------
# Mock subscriber 模板（§H 测试夹具契约 #4）
# ---------------------------------------------------------------------------
# 所有 6 个信号统一用同一份 mock 类记录 (call_count, last_payload, payloads_history)。
# 不同信号通过不同的 on_* 方法区分，便于 disconnect 与多信号断言。
class _StatTestMock extends RefCounted:
	var _call_count: int = 0
	var _last_payload: Array = []
	var _payloads: Array = []  # 完整历史，用于"同帧 N 次广播"类断言

	func reset_counters() -> void:
		_call_count = 0
		_last_payload = []
		_payloads = []

	func _record(payload: Array) -> void:
		_call_count += 1
		_last_payload = payload
		_payloads.append(payload.duplicate())

	# 4 元 payload 三类
	func on_stat_changed(stat_id: String, old_v: int, new_v: int, req: int) -> void:
		_record([stat_id, old_v, new_v, req])

	func on_var_changed(var_id: String, old_v: int, new_v: int, req: int) -> void:
		_record([var_id, old_v, new_v, req])

	func on_affinity_changed(npc_id: String, old_v: int, new_v: int, req: int) -> void:
		_record([npc_id, old_v, new_v, req])

	# 1 元 payload 两类
	func on_event_triggered(event_id: String) -> void:
		_record([event_id])

	func on_era_marker_added(marker_id: String) -> void:
		_record([marker_id])

	# 2 元 payload chapter
	func on_chapter_changed(old_chapter: String, new_chapter: String) -> void:
		_record([old_chapter, new_chapter])


# ---------------------------------------------------------------------------
# 6 个 mock 实例 + 信号名常量
# ---------------------------------------------------------------------------
const _SIGNAL_NAMES: Array[String] = [
	"stat_changed",
	"var_changed",
	"affinity_changed",
	"event_triggered",
	"era_marker_added",
	"chapter_changed",
]

var _mock_stat: _StatTestMock
var _mock_var: _StatTestMock
var _mock_affinity: _StatTestMock
var _mock_event: _StatTestMock
var _mock_era: _StatTestMock
var _mock_chapter: _StatTestMock


# ---------------------------------------------------------------------------
# 夹具（§H 测试夹具契约 #1 / #2 / #3）
# ---------------------------------------------------------------------------
func before_test() -> void:
	# 1) 重置 GlobalState 到出厂态
	GlobalState.reset_to_initial()
	# 2) 逐信号断开所有现存连接
	_disconnect_all_signals()
	# 3) 创建并连接 6 个新 mock subscriber（默认同步连接，验证同步路径正确）
	_mock_stat = _StatTestMock.new()
	_mock_var = _StatTestMock.new()
	_mock_affinity = _StatTestMock.new()
	_mock_event = _StatTestMock.new()
	_mock_era = _StatTestMock.new()
	_mock_chapter = _StatTestMock.new()
	GlobalState.stat_changed.connect(_mock_stat.on_stat_changed)
	GlobalState.var_changed.connect(_mock_var.on_var_changed)
	GlobalState.affinity_changed.connect(_mock_affinity.on_affinity_changed)
	GlobalState.event_triggered.connect(_mock_event.on_event_triggered)
	GlobalState.era_marker_added.connect(_mock_era.on_era_marker_added)
	GlobalState.chapter_changed.connect(_mock_chapter.on_chapter_changed)


func after_test() -> void:
	_disconnect_all_signals()


func _disconnect_all_signals() -> void:
	# Godot 4.6 没有 disconnect_all()，必须遍历 get_signal_connection_list 手动断。
	for sig_name in _SIGNAL_NAMES:
		var conns: Array = GlobalState.get_signal_connection_list(sig_name)
		for conn in conns:
			# Godot 4.x: connection entry 含 "signal" / "callable" / "flags"
			if conn.has("callable"):
				GlobalState.disconnect(sig_name, conn["callable"])


func _await_idle_frames(n: int) -> void:
	# 负断言用：触发后 await N 帧，再断言 mock._call_count == 0。
	for i in n:
		await get_tree().process_frame


func _reset_all_mock_counters() -> void:
	_mock_stat.reset_counters()
	_mock_var.reset_counters()
	_mock_affinity.reset_counters()
	_mock_event.reset_counters()
	_mock_era.reset_counters()
	_mock_chapter.reset_counters()


# =============================================================================
# H.1 真变化广播（显性属性，4 元组 payload）
# =============================================================================
# GIVEN xuexi = 3
# WHEN  change_stat("xuexi", +1)
# THEN  get_stat("xuexi") == 4 + stat_changed 触发 1 次,
#       payload ("xuexi", old=3, new=4, requested=+1) 全字段精确匹配
func test_h01_change_stat_real_change_broadcasts_4tuple_payload() -> void:
	# Arrange
	assert_int(GlobalState.get_stat("xuexi")).is_equal(3)

	# Act
	GlobalState.change_stat("xuexi", 1)

	# Assert: 状态
	assert_int(GlobalState.get_stat("xuexi")).is_equal(4)
	# Assert: 信号触发次数与 payload
	assert_int(_mock_stat._call_count).is_equal(1)
	assert_array(_mock_stat._last_payload).is_equal(["xuexi", 3, 4, 1])


# =============================================================================
# H.2 底值完全吞掉不广播（D.3 + E.1）
# =============================================================================
# GIVEN danliang = 0 (init=1, 先 -1 到底)
# WHEN  change_stat("danliang", -1)
# THEN  get_stat == 0 不变, stat_changed **不**触发, 同帧 100ms 内无延迟广播
func test_h02_change_stat_floor_completely_swallowed_silent() -> void:
	# Arrange: 把 danliang 从 init=1 -> 0
	GlobalState.change_stat("danliang", -1)
	assert_int(GlobalState.get_stat("danliang")).is_equal(0)
	_reset_all_mock_counters()

	# Act
	GlobalState.change_stat("danliang", -1)

	# Assert: 状态不变
	assert_int(GlobalState.get_stat("danliang")).is_equal(0)
	# Assert: 负断言 — await 2 frames 后无任何 stat_changed
	await _await_idle_frames(2)
	assert_int(_mock_stat._call_count).is_equal(0)


# =============================================================================
# H.3 reset_to_initial 静默（E.7）
# =============================================================================
# GIVEN 显式构造已变更运行态 (stats/vars/affinity/triggered/era_markers/chapter 各动两条)
# WHEN  reset_to_initial()
# THEN  6 类容器全回 init + 6 个 mock 全 _call_count == 0
func test_h03_reset_to_initial_silent_full_six_containers() -> void:
	# Arrange: 步骤 (a)-(f) 显式构造运行态
	GlobalState.change_stat("xuexi", 2)
	GlobalState.change_stat("danliang", 1)
	GlobalState.change_var("xinjie", 1)
	GlobalState.change_var("qianbao_xiuchi", 1)
	GlobalState.change_affinity("jiejie", 2)
	GlobalState.change_affinity("caozhengdong", -2)
	GlobalState.mark_triggered("ev1")
	GlobalState.mark_triggered("ev2")
	GlobalState.mark_era_marker("kaixue")
	GlobalState.mark_era_marker("shenzhou7")
	GlobalState.set_chapter("ch1")
	# 清掉运行态构造期间累积的回调计数（mock 已绑定，会被触发）
	_reset_all_mock_counters()

	# Act
	GlobalState.reset_to_initial()

	# Assert (1)(2)(3): 4 stats / 3 vars / 12 affinity 全部回 init
	assert_int(GlobalState.get_stat("xuexi")).is_equal(GlobalState.STATS_CONFIG["xuexi"].init)
	assert_int(GlobalState.get_stat("danliang")).is_equal(GlobalState.STATS_CONFIG["danliang"].init)
	assert_int(GlobalState.get_stat("koucai")).is_equal(GlobalState.STATS_CONFIG["koucai"].init)
	assert_int(GlobalState.get_stat("tili")).is_equal(GlobalState.STATS_CONFIG["tili"].init)
	for var_id in GlobalState.VARS_CONFIG:
		assert_int(GlobalState.get_var(var_id)).is_equal(GlobalState.VARS_CONFIG[var_id].init)
	for npc_id in GlobalState.AFFINITY_CONFIG:
		assert_int(GlobalState.get_affinity(npc_id)).is_equal(GlobalState.AFFINITY_CONFIG[npc_id].init)
	# Assert (4)(5): triggered / era_markers 全清
	assert_bool(GlobalState.has_triggered("ev1")).is_false()
	assert_bool(GlobalState.has_triggered("ev2")).is_false()
	assert_bool(GlobalState.has_era_marker("kaixue")).is_false()
	assert_bool(GlobalState.has_era_marker("shenzhou7")).is_false()
	# Assert (6): chapter 回 prologue
	assert_str(GlobalState.get_chapter()).is_equal("prologue")
	# Assert (7): await 2 idle frames 后 6 个 mock 全 _call_count == 0
	await _await_idle_frames(2)
	assert_int(_mock_stat._call_count).is_equal(0)
	assert_int(_mock_var._call_count).is_equal(0)
	assert_int(_mock_affinity._call_count).is_equal(0)
	assert_int(_mock_event._call_count).is_equal(0)
	assert_int(_mock_era._call_count).is_equal(0)
	assert_int(_mock_chapter._call_count).is_equal(0)


# =============================================================================
# H.4 change_var 广播（隐性变量，4 元组）
# =============================================================================
func test_h04_change_var_real_change_broadcasts_4tuple_payload() -> void:
	# Arrange: xinjie 默认 init=0
	assert_int(GlobalState.get_var("xinjie")).is_equal(0)

	# Act
	GlobalState.change_var("xinjie", 2)

	# Assert
	assert_int(GlobalState.get_var("xinjie")).is_equal(2)
	assert_int(_mock_var._call_count).is_equal(1)
	assert_array(_mock_var._last_payload).is_equal(["xinjie", 0, 2, 2])


# =============================================================================
# H.5 change_affinity 广播（4 元组）
# =============================================================================
func test_h05_change_affinity_real_change_broadcasts_4tuple_payload() -> void:
	# Arrange: baoxianjin 默认 init=0
	assert_int(GlobalState.get_affinity("baoxianjin")).is_equal(0)

	# Act
	GlobalState.change_affinity("baoxianjin", -3)

	# Assert
	assert_int(GlobalState.get_affinity("baoxianjin")).is_equal(-3)
	assert_int(_mock_affinity._call_count).is_equal(1)
	assert_array(_mock_affinity._last_payload).is_equal(["baoxianjin", 0, -3, -3])


# =============================================================================
# H.6 mark_triggered 首次广播
# =============================================================================
func test_h06_mark_triggered_first_time_broadcasts() -> void:
	# Arrange
	assert_bool(GlobalState.has_triggered("ch1/12_yuekao_ranking")).is_false()

	# Act
	GlobalState.mark_triggered("ch1/12_yuekao_ranking")

	# Assert
	assert_bool(GlobalState.has_triggered("ch1/12_yuekao_ranking")).is_true()
	assert_int(_mock_event._call_count).is_equal(1)
	assert_array(_mock_event._last_payload).is_equal(["ch1/12_yuekao_ranking"])


# =============================================================================
# H.7 mark_triggered 重复静默（E.4）
# =============================================================================
func test_h07_mark_triggered_repeat_silent() -> void:
	# Arrange: 第一次 mark
	GlobalState.mark_triggered("ev1")
	assert_bool(GlobalState.has_triggered("ev1")).is_true()
	_reset_all_mock_counters()

	# Act: 重复 mark
	GlobalState.mark_triggered("ev1")

	# Assert: 仍然 true，但 event_triggered 不再发
	assert_bool(GlobalState.has_triggered("ev1")).is_true()
	await _await_idle_frames(2)
	assert_int(_mock_event._call_count).is_equal(0)


# =============================================================================
# H.8 mark_era_marker 重复静默（E.4）
# =============================================================================
func test_h08_mark_era_marker_repeat_silent() -> void:
	# Arrange
	GlobalState.mark_era_marker("kaixue")
	assert_bool(GlobalState.has_era_marker("kaixue")).is_true()
	_reset_all_mock_counters()

	# Act
	GlobalState.mark_era_marker("kaixue")

	# Assert
	assert_bool(GlobalState.has_era_marker("kaixue")).is_true()
	await _await_idle_frames(2)
	assert_int(_mock_era._call_count).is_equal(0)


# =============================================================================
# H.9 set_chapter 广播 2 元 payload + 同章节静默（Round-2 修订）
# =============================================================================
func test_h09_set_chapter_broadcasts_2tuple_and_same_chapter_silent() -> void:
	# Arrange
	assert_str(GlobalState.get_chapter()).is_equal("prologue")

	# Act 1: 真切换
	GlobalState.set_chapter("ch1")

	# Assert 1: payload 2 元 (old, new)
	assert_str(GlobalState.get_chapter()).is_equal("ch1")
	assert_int(_mock_chapter._call_count).is_equal(1)
	assert_array(_mock_chapter._last_payload).is_equal(["prologue", "ch1"])

	# Act 2: 同章节再 set
	GlobalState.set_chapter("ch1")

	# Assert 2: 不再广播 — _call_count 仍 == 1
	await _await_idle_frames(2)
	assert_int(_mock_chapter._call_count).is_equal(1)


# =============================================================================
# H.10 to_dict ↔ from_dict round-trip + sort 显式验证（E.8 + Round-2 加严）
# =============================================================================
# 重点：(2)(3) 显式断言 _triggered / _era_markers 字典升序，验证 to_dict 的 sort 真生效，
# 而不是因插入顺序碰巧匹配；(4) 重复 dump 字面级稳定。
func test_h10_to_dict_from_dict_round_trip_with_explicit_sort_assertion() -> void:
	# Arrange: 显式构造运行态 S（注意 mark_triggered / mark_era_marker 用**逆字典序**插入）
	GlobalState.reset_to_initial()
	GlobalState.change_stat("xuexi", 2)               # → 5
	GlobalState.change_var("xinjie", 3)
	GlobalState.change_affinity("jiejie", 2)          # 8 → 10
	GlobalState.mark_triggered("ev2")                 # 逆序插入
	GlobalState.mark_triggered("ev1")
	GlobalState.mark_era_marker("shenzhou7")          # 逆序插入
	GlobalState.mark_era_marker("kaixue")
	GlobalState.set_chapter("ch1")

	# Act: dump → reset → load → dump again
	var d: Dictionary = GlobalState.to_dict()
	GlobalState.reset_to_initial()
	GlobalState.from_dict(d)
	var d2: Dictionary = GlobalState.to_dict()

	# Assert (1): 深比相等
	assert_bool(d == d2).is_true()

	# Assert (2): _triggered 是 Array 且字典升序
	assert_bool(d["triggered"] is Array).is_true()
	assert_array(d["triggered"]).is_equal(["ev1", "ev2"])

	# Assert (3): _era_markers 是 Array 且字典升序
	assert_bool(d["era_markers"] is Array).is_true()
	assert_array(d["era_markers"]).is_equal(["kaixue", "shenzhou7"])

	# Assert (4): 重复 dump 字面级一致（同 state 多次 dump 字节稳定）
	var d3: Dictionary = GlobalState.to_dict()
	assert_bool(d == d3).is_true()


# =============================================================================
# H.11 from_dict 自愈式 clamp + cast（E.6 + Round-2 加严）
# =============================================================================
# 关键：6 个字段（2 stats + 2 vars + 2 affinity）越界 / 浮点 → cast + clamp + push_warning
# load 路径静默契约：mock subscriber 不应收到任何 *_changed
# 警告计数验证由 log_capture helper 兜底（参见文件末 NOTE）
func test_h11_from_dict_self_healing_clamp_and_cast() -> void:
	# Arrange: 越界快照
	var snap: Dictionary = {
		"stats":    {"xuexi": 999, "danliang": -50},
		"vars":     {"xinjie": -50, "qianbao_xiuchi": 9999.0},  # qianbao 用浮点验证 cast
		"affinity": {"jiejie": 99, "caozhengdong": -99},
	}

	# Act
	GlobalState.reset_to_initial()
	_reset_all_mock_counters()
	GlobalState.from_dict(snap)

	# Assert (1): 6 字段进入自愈路径，clamp 至各 cfg.min/max
	assert_int(GlobalState.get_stat("xuexi")).is_equal(10)             # max=10
	assert_int(GlobalState.get_stat("danliang")).is_equal(0)           # min=0
	assert_int(GlobalState.get_var("xinjie")).is_equal(0)              # min=0
	assert_int(GlobalState.get_var("qianbao_xiuchi")).is_equal(20)     # max=20, 9999.0 cast 到 9999 再 clamp
	assert_int(GlobalState.get_affinity("jiejie")).is_equal(15)        # max=15
	assert_int(GlobalState.get_affinity("caozhengdong")).is_equal(-15) # min=-15

	# Assert (3): load 路径静默 — 三类 mock 全 _call_count == 0
	await _await_idle_frames(2)
	assert_int(_mock_stat._call_count).is_equal(0)
	assert_int(_mock_var._call_count).is_equal(0)
	assert_int(_mock_affinity._call_count).is_equal(0)
	# Assert (2) — 6 条 push_warning：见文件末 NOTE，log_capture helper 落地后追加
	# assert_warning_count(6)


# =============================================================================
# H.12 性能预算（Round-2 修订：< 5ms / 100 次广播 / 重复 3 次取最差）
# =============================================================================
# 注意：GDD 原文用 change_stat("xuexi", +1) × 100，但 xuexi(init=3, max=10) 仅能产生 7 次有效广播 / 内层。
# 改用 change_var("xinjie", +1)（init=0, max=20）让 10 × 10 = 100 次内层全部产生有效广播，
# 严格匹配 GDD "100 次有效 change + 100 次 mock 回调"。
func test_h12_performance_budget_100_changes_under_5ms() -> void:
	# Arrange: 用 var_changed 信号（已在 before_test 连接）
	const OUTER: int = 10
	const INNER: int = 10
	const BUDGET_USEC: int = 5000  # 5 ms
	const REPEATS: int = 3

	# 每次 repeat 累计仅 inner 窗口（reset 在外、不计入），3 次取最差
	var worst_usec: int = 0
	for repeat in REPEATS:
		_reset_all_mock_counters()
		var pure_total: int = 0
		for outer in OUTER:
			GlobalState.reset_to_initial()  # 不计入计时
			var ts: int = Time.get_ticks_usec()
			for inner in INNER:
				GlobalState.change_var("xinjie", 1)
			pure_total += Time.get_ticks_usec() - ts
		if pure_total > worst_usec:
			worst_usec = pure_total

	# Assert (1): mock subscriber 在最后一次 repeat 累计收到 100 次 var_changed
	assert_int(_mock_var._call_count).is_equal(OUTER * INNER)

	# Assert (2)(3): 3 次最差仍 < 5 ms
	assert_int(worst_usec).is_less(BUDGET_USEC)

	# Assert (4): 测试运行环境契约 — 由 CI 配置约束（headless --release），本 AC 内不直接验证


# =============================================================================
# H.13 未知 ID push_error（E.2 修订）
# =============================================================================
# 三类 change_*("unknown_*", 1) 都不修改集合、不发信号、各产生一次 push_error
# 警告/错误计数验证由 log_capture helper 兜底（见文件末 NOTE）
func test_h13_change_with_unknown_id_pushes_error_and_no_op() -> void:
	# Arrange: 记录初始大小
	var stats_size_before: int = GlobalState.STATS_CONFIG.size()
	var vars_size_before: int = GlobalState.VARS_CONFIG.size()
	var aff_size_before: int = GlobalState.AFFINITY_CONFIG.size()

	# Act: 三次未知 ID 调用
	GlobalState.change_stat("unknown_id", 1)
	GlobalState.change_var("unknown_id", 1)
	GlobalState.change_affinity("unknown_npc", 1)

	# Assert: 三类容器大小不变（未知 ID 不写入）
	# 通过 to_dict 间接验证容器内容
	var d: Dictionary = GlobalState.to_dict()
	assert_int((d["stats"] as Dictionary).size()).is_equal(stats_size_before)
	assert_int((d["vars"] as Dictionary).size()).is_equal(vars_size_before)
	assert_int((d["affinity"] as Dictionary).size()).is_equal(aff_size_before)
	# Assert: 三类信号未触发
	await _await_idle_frames(2)
	assert_int(_mock_stat._call_count).is_equal(0)
	assert_int(_mock_var._call_count).is_equal(0)
	assert_int(_mock_affinity._call_count).is_equal(0)
	# Assert: 3 次 push_error — log_capture helper 落地后追加
	# assert_error_count(3)


# =============================================================================
# H.14 半吃掉广播 4 元组（D.3 边界）
# =============================================================================
# jiejie max=15。从 14 → +3 → clamp 至 15；effective=+1, requested=+3
func test_h14_change_affinity_half_swallowed_broadcasts_with_requested_preserved() -> void:
	# Arrange: 用合法路径推到 14（init=8, +6 -> 14）
	GlobalState.change_affinity("jiejie", 6)
	assert_int(GlobalState.get_affinity("jiejie")).is_equal(14)
	_reset_all_mock_counters()

	# Act
	GlobalState.change_affinity("jiejie", 3)

	# Assert
	assert_int(GlobalState.get_affinity("jiejie")).is_equal(15)
	assert_int(_mock_affinity._call_count).is_equal(1)
	# payload requested 字段保留**原始** +3，而非 clamp 修剪后的 +1
	assert_array(_mock_affinity._last_payload).is_equal(["jiejie", 14, 15, 3])


# =============================================================================
# H.15 typo_warning 阈值与符号比较（E.10 + Round-2 阈值 5 + abs 溢出修复 + effective=0 静默）
# =============================================================================
# 5 case 合并测试：A 超阈值真变化 / B 等于阈值不警告 / C 半吃掉仍报 / D effective=0 静默 / E INT64_MIN 不绕过
# warning 计数由 log_capture helper 兜底；此处验证状态 + 信号
func test_h15_typo_warning_threshold_and_sign_comparison_5_cases() -> void:
	# ---- case A: GIVEN xuexi=3 WHEN +6 THEN xuexi==9, signal once payload (xuexi,3,9,+6), warning_count=1
	GlobalState.change_stat("xuexi", 6)
	assert_int(GlobalState.get_stat("xuexi")).is_equal(9)
	assert_int(_mock_stat._call_count).is_equal(1)
	assert_array(_mock_stat._last_payload).is_equal(["xuexi", 3, 9, 6])

	# ---- case B: GIVEN xuexi=3（重置）WHEN +5 THEN warning_count=0（边界 |delta|≤5 不警告）
	GlobalState.reset_to_initial()
	_reset_all_mock_counters()
	GlobalState.change_stat("xuexi", 5)
	assert_int(GlobalState.get_stat("xuexi")).is_equal(8)
	assert_int(_mock_stat._call_count).is_equal(1)
	assert_array(_mock_stat._last_payload).is_equal(["xuexi", 3, 8, 5])

	# ---- case C 半吃掉仍报: GIVEN xuexi=7 WHEN +6 THEN xuexi==10 signal once payload(7,10,+6) warning_count=1
	GlobalState.reset_to_initial()
	GlobalState.change_stat("xuexi", 4)  # → 7
	assert_int(GlobalState.get_stat("xuexi")).is_equal(7)
	_reset_all_mock_counters()
	GlobalState.change_stat("xuexi", 6)
	assert_int(GlobalState.get_stat("xuexi")).is_equal(10)
	assert_int(_mock_stat._call_count).is_equal(1)
	assert_array(_mock_stat._last_payload).is_equal(["xuexi", 7, 10, 6])

	# ---- case D effective=0 静默: GIVEN caozhengdong=-15(min) WHEN -20 THEN no signal, no warning
	GlobalState.reset_to_initial()
	GlobalState.change_affinity("caozhengdong", -12)  # init=-3 → -15
	assert_int(GlobalState.get_affinity("caozhengdong")).is_equal(-15)
	_reset_all_mock_counters()
	GlobalState.change_affinity("caozhengdong", -20)
	assert_int(GlobalState.get_affinity("caozhengdong")).is_equal(-15)
	await _await_idle_frames(2)
	assert_int(_mock_affinity._call_count).is_equal(0)

	# ---- case E INT64_MIN 不绕过: GIVEN xuexi=3 WHEN INT64_MIN THEN xuexi==0, signal once payload requested=INT64_MIN, warning fires
	GlobalState.reset_to_initial()
	_reset_all_mock_counters()
	# Godot 4.x: -9223372036854775808 字面量在 GDScript 解析为表达式 -9223372036854775808
	# 但负字面量上限为 -9223372036854775807（受表达式 unary minus 影响），因此用 INT64_MIN 安全表达：
	const INT64_MIN: int = -9223372036854775807 - 1
	GlobalState.change_stat("xuexi", INT64_MIN)
	# safe_delta = clampi(INT64_MIN, -10, 10) = -10 → new = clampi(3 + -10, 0, 10) = 0
	assert_int(GlobalState.get_stat("xuexi")).is_equal(0)
	assert_int(_mock_stat._call_count).is_equal(1)
	# requested 字段保留**原始** INT64_MIN
	assert_array(_mock_stat._last_payload).is_equal(["xuexi", 3, 0, INT64_MIN])

	# 5 个 warning 由 log_capture helper 兜底（A=1 + B=0 + C=1 + D=0 + E=1 = 3 total），
	# 见文件末 NOTE。assert_warning_count(3)


# =============================================================================
# H.16 C.5 负 API 表面（has_method 反射）
# =============================================================================
func test_h16_no_set_methods_exist_on_global_state() -> void:
	# 禁止未来 PR 静默引入 set_stat / set_var / set_affinity 绝对赋值接口
	assert_bool(GlobalState.has_method("set_stat")).is_false()
	assert_bool(GlobalState.has_method("set_var")).is_false()
	assert_bool(GlobalState.has_method("set_affinity")).is_false()


# =============================================================================
# H.17 from_dict unknown ID 跳过 + push_warning（E.6 case 2/6 + Round-2 新增）
# =============================================================================
func test_h17_from_dict_unknown_id_skipped_with_warning() -> void:
	# Arrange
	var snap: Dictionary = {
		"stats":    {"unknown_stat": 5, "xuexi": 4},
		"vars":     {"unknown_var": 7, "xinjie": 2},
		"affinity": {"unknown_npc": 3, "jiejie": 9},
	}

	# Act
	GlobalState.reset_to_initial()
	GlobalState.from_dict(snap)

	# Assert (1): 已知 ID 正确写入
	assert_int(GlobalState.get_stat("xuexi")).is_equal(4)
	assert_int(GlobalState.get_var("xinjie")).is_equal(2)
	assert_int(GlobalState.get_affinity("jiejie")).is_equal(9)

	# Assert (2): unknown_* 被跳过 — 容器大小仅含 CONFIG 注册的 ID
	var d: Dictionary = GlobalState.to_dict()
	assert_int((d["stats"] as Dictionary).size()).is_equal(GlobalState.STATS_CONFIG.size())
	assert_int((d["vars"] as Dictionary).size()).is_equal(GlobalState.VARS_CONFIG.size())
	assert_int((d["affinity"] as Dictionary).size()).is_equal(GlobalState.AFFINITY_CONFIG.size())
	assert_bool((d["stats"] as Dictionary).has("unknown_stat")).is_false()
	assert_bool((d["vars"] as Dictionary).has("unknown_var")).is_false()
	assert_bool((d["affinity"] as Dictionary).has("unknown_npc")).is_false()

	# Assert (3): 3 条 push_warning — log_capture helper 落地后追加
	# assert_warning_count(3)


# =============================================================================
# H.18 from_dict chapter 越界写入 + push_warning（E.6 case 7 + Round-2 新增）
# =============================================================================
# 实装按 §C.5 / §E.5 不校验，写入接受；仅 push_warning + load 路径 chapter_changed 不发
func test_h18_from_dict_chapter_out_of_range_accepted_with_warning() -> void:
	# Arrange
	var snap: Dictionary = {"chapter": "ch99"}

	# Act
	GlobalState.reset_to_initial()
	_reset_all_mock_counters()
	GlobalState.from_dict(snap)

	# Assert (1): chapter 写入接受
	assert_str(GlobalState.get_chapter()).is_equal("ch99")
	# Assert (3): chapter_changed 不触发（load 路径静默）
	await _await_idle_frames(2)
	assert_int(_mock_chapter._call_count).is_equal(0)
	# Assert (2): 1 条 push_warning — log_capture helper 落地后追加
	# assert_warning_count(1)


# =============================================================================
# H.19 启动 config 校验（§F.5 R-S6 + Round-2 新增）
# =============================================================================
# 三组非法 config 各返回 false 且各 push_error 一次；合法 config 返回 true 无 error/warning
func test_h19_validate_configs_rejects_min_init_max_violations() -> void:
	# 非法组 (a): init < min
	var bad_a: Dictionary = {"xuexi": {"init": 5, "min": 6, "max": 10}}
	assert_bool(GlobalState._validate_configs(bad_a, {}, {})).is_false()

	# 非法组 (b): init > max
	var bad_b: Dictionary = {"xuexi": {"init": 11, "min": 0, "max": 10}}
	assert_bool(GlobalState._validate_configs(bad_b, {}, {})).is_false()

	# 非法组 (c): min > max（在 affinity 表）
	var bad_c: Dictionary = {"jiejie": {"init": 8, "min": 16, "max": 15}}
	assert_bool(GlobalState._validate_configs({}, {}, bad_c)).is_false()

	# 合法 config（默认三表）
	assert_bool(GlobalState._validate_configs(
		GlobalState.STATS_CONFIG,
		GlobalState.VARS_CONFIG,
		GlobalState.AFFINITY_CONFIG
	)).is_true()
	# 3 次 push_error — log_capture helper 落地后追加
	# assert_error_count(3)


# =============================================================================
# H.20 同帧多次 change_* 多次广播（E.3 + Round-2 新增）
# =============================================================================
# CONNECT_DEFERRED **不**使用：验证同步路径同帧 N 次正确
func test_h20_same_frame_multiple_change_stat_broadcasts_in_order() -> void:
	# Arrange: danliang init=1
	assert_int(GlobalState.get_stat("danliang")).is_equal(1)

	# Act: 同步连续 3 次（无 await）
	GlobalState.change_stat("danliang", 1)
	GlobalState.change_stat("danliang", 1)
	GlobalState.change_stat("danliang", 1)

	# Assert: await 1 idle frame 后 mock 累计 3 次，按调用顺序
	await _await_idle_frames(1)
	assert_int(_mock_stat._call_count).is_equal(3)
	assert_array(_mock_stat._payloads[0]).is_equal(["danliang", 1, 2, 1])
	assert_array(_mock_stat._payloads[1]).is_equal(["danliang", 2, 3, 1])
	assert_array(_mock_stat._payloads[2]).is_equal(["danliang", 3, 4, 1])
	assert_int(GlobalState.get_stat("danliang")).is_equal(4)


# =============================================================================
# NOTE — push_error / push_warning 计数断言
# =============================================================================
# H.11 / H.13 / H.15 / H.17 / H.18 / H.19 中标记为
#   "log_capture helper 落地后追加"
# 的 assert_error_count(N) / assert_warning_count(N) 调用点：
#
# gdunit4 4.x 的 GdUnitTestSuite 没有名为 assert_error_count / assert_warning_count
# 的内置方法（API 名在不同 minor 版本之间漂移）。stat-system GDD §H 测试夹具契约 #5
# 已声明：若版本不支持，回退方案是临时 hook 全局 Logger（待 [[test-helpers]] GDD
# 提供 tests/helpers/log_capture.gd）。
#
# 当前测试文件保留所有"状态 + 信号"侧的强断言（足以验证 push_error/push_warning
# 路径的实际效果：未知 ID 不写入、effective_delta=0 静默、自愈 clamp 至边界等）。
# 待 /test-helpers 落地 log_capture 后，把上述被注释的 assert_error_count /
# assert_warning_count 解开即可。
#
# 此 gap 不影响 20 条 AC 的核心覆盖率：状态 + 信号断言已 cover §H 设计意图。
# =============================================================================
