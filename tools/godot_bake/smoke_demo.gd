extends SceneTree

## 自动化端到端测试：模拟新游戏 → 跑完序章+第一章全部对白事件，
## 验证 Dialogue/GlobalState/CutsceneRunner 链路完整。
## 不模拟实际 UI 交互，所有 choice 默认走 0（即第一选项）。

const PROLOGUE_EVENTS := [
	"prologue/01_father_send_off",
	"prologue/03_corridor_overhear",
	"prologue/02_classroom_arrival",
	"prologue/04_xiaomaibu_first_pass",
	"prologue/05_dorm_assigned",
]
const CH1_EVENTS := [
	"ch1/11_zhengfanhe_help",
	"ch1/12_yuekao_ranking",
	"ch1/13_xiaomaibu_first_buy",
	"ch1/14_caozhengdong_robbery",
	"ch1/15_shenzhou7_evening",
	"ch1/16_sanlu_classmeeting",
	"ch1/_demo_end",
]

var _failures: Array[String] = []
var _gs: Node
var _dlg: Node
var _sm: Node

func _init() -> void:
	root.set_disable_3d(true)
	auto_accept_quit = true
	## 等 autoloads 准备好
	process_frame.connect(_on_first_frame, CONNECT_ONE_SHOT)

func _on_first_frame() -> void:
	_gs = root.get_node("GlobalState")
	_dlg = root.get_node("Dialogue")
	_sm = root.get_node("SaveManager")
	if _gs == null or _dlg == null or _sm == null:
		print("autoloads missing: GlobalState=%s Dialogue=%s SaveManager=%s" % [_gs, _dlg, _sm])
		quit(2)
		return
	_run_test()

func _run_test() -> void:
	_gs.reset_to_initial()
	print("=== smoke test: new game ===")
	print("init: chapter=%s xuexi=%d danliang=%d koucai=%d" % [
		_gs.get_chapter(), _gs.get_stat("xuexi"),
		_gs.get_stat("danliang"), _gs.get_stat("koucai"),
	])

	for ev in PROLOGUE_EVENTS:
		await _play_event(ev)
	for ev in CH1_EVENTS:
		await _play_event(ev)

	print("=== final state ===")
	print("chapter=%s" % _gs.get_chapter())
	print("stats: xuexi=%d danliang=%d koucai=%d tili=%d" % [
		_gs.get_stat("xuexi"), _gs.get_stat("danliang"),
		_gs.get_stat("koucai"), _gs.get_stat("tili"),
	])
	print("vars: xinjie=%d kaguodu=%d qianbao=%d" % [
		_gs.get_var("xinjie"), _gs.get_var("kaguodu_xinli"),
		_gs.get_var("qianbao_xiuchi"),
	])
	print("affinity: wangyan=%d zengjianming=%d baosimu=%d caozhengdong=%d" % [
		_gs.get_affinity("wangyan"), _gs.get_affinity("zengjianming"),
		_gs.get_affinity("baosimu"), _gs.get_affinity("caozhengdong"),
	])
	print("era_markers: %s" % str(_gs._era_markers.keys()))

	print("=== save/load round-trip ===")
	var saved_ok: bool = _sm.save(0, "classroom_2b", Vector2(1080, 400), "down")
	if not saved_ok:
		_failures.append("save failed")
	_gs.reset_to_initial()
	if _gs.get_chapter() != "prologue":
		_failures.append("reset_to_initial did not reset chapter")
	var data: Dictionary = _sm.load_slot(0)
	if data.is_empty():
		_failures.append("load_slot returned empty")
	if _gs.get_chapter() != "ch1_done":
		_failures.append("load_slot did not restore chapter (got %s)" % _gs.get_chapter())

	for ev in PROLOGUE_EVENTS + CH1_EVENTS:
		if not _gs.has_triggered(ev):
			_failures.append("event not triggered after load: %s" % ev)

	if _failures.is_empty():
		print("=== ALL OK ===")
		quit(0)
	else:
		print("=== FAILURES ===")
		for f in _failures:
			print("  ! " + f)
		quit(1)

func _play_event(event_id: String) -> void:
	var line_id := event_id + "/01"
	_dlg.play(line_id)
	if not _dlg.is_playing():
		_failures.append("dialogue did not start: %s" % line_id)
		return
	while _dlg.is_playing():
		await process_frame
		if _dlg._awaiting_choice:
			_dlg.choose(0)
		else:
			_dlg.advance()
		await process_frame
	print("[ok] event done: %s" % event_id)
