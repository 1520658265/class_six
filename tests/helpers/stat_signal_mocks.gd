## Stat System 测试用 mock subscriber helpers
##
## 实现 stat-system GDD §H 测试夹具契约 #4 的 mock subscriber 模板：
## 每个 helper 暴露 _call_count / _last_payload，供 AC 直接断言。
##
## Usage:
##   var mock := StatSignalMocks.StatChangedMock.new()
##   GlobalState.stat_changed.connect(mock.on_stat_changed)
##   ...
##   assert_int(mock._call_count).is_equal(1)
##   assert_array(mock._last_payload).is_equal(["xuexi", 3, 4, 1])
class_name StatSignalMocks


class StatChangedMock extends RefCounted:
	var _call_count: int = 0
	var _last_payload: Array = []
	var _all_payloads: Array[Array] = []

	func on_stat_changed(stat_id: String, old_v: int, new_v: int, req: int) -> void:
		_call_count += 1
		_last_payload = [stat_id, old_v, new_v, req]
		_all_payloads.append([stat_id, old_v, new_v, req])


class VarChangedMock extends RefCounted:
	var _call_count: int = 0
	var _last_payload: Array = []
	var _all_payloads: Array[Array] = []

	func on_var_changed(var_id: String, old_v: int, new_v: int, req: int) -> void:
		_call_count += 1
		_last_payload = [var_id, old_v, new_v, req]
		_all_payloads.append([var_id, old_v, new_v, req])


class AffinityChangedMock extends RefCounted:
	var _call_count: int = 0
	var _last_payload: Array = []
	var _all_payloads: Array[Array] = []

	func on_affinity_changed(npc_id: String, old_v: int, new_v: int, req: int) -> void:
		_call_count += 1
		_last_payload = [npc_id, old_v, new_v, req]
		_all_payloads.append([npc_id, old_v, new_v, req])


class EventTriggeredMock extends RefCounted:
	var _call_count: int = 0
	var _last_payload: Array = []

	func on_event_triggered(event_id: String) -> void:
		_call_count += 1
		_last_payload = [event_id]


class EraMarkerAddedMock extends RefCounted:
	var _call_count: int = 0
	var _last_payload: Array = []

	func on_era_marker_added(marker_id: String) -> void:
		_call_count += 1
		_last_payload = [marker_id]


class ChapterChangedMock extends RefCounted:
	var _call_count: int = 0
	var _last_payload: Array = []

	func on_chapter_changed(old_ch: String, new_ch: String) -> void:
		_call_count += 1
		_last_payload = [old_ch, new_ch]


## 一次性把 6 个 mock 全部连接到 GlobalState 的 6 个信号，方便 H.3 等
## "全集合校验" 场景。返回一个 Dictionary 让 caller 按 key 断言。
##
## Caller 在 after_test 里调用 disconnect_all_from_globalstate(globalstate, mocks)
## 把 mocks 全部断开。
static func connect_all(globalstate: Node) -> Dictionary:
	var mocks := {
		"stat":     StatChangedMock.new(),
		"var":      VarChangedMock.new(),
		"affinity": AffinityChangedMock.new(),
		"event":    EventTriggeredMock.new(),
		"era":      EraMarkerAddedMock.new(),
		"chapter":  ChapterChangedMock.new(),
	}
	globalstate.stat_changed.connect(mocks["stat"].on_stat_changed)
	globalstate.var_changed.connect(mocks["var"].on_var_changed)
	globalstate.affinity_changed.connect(mocks["affinity"].on_affinity_changed)
	globalstate.event_triggered.connect(mocks["event"].on_event_triggered)
	globalstate.era_marker_added.connect(mocks["era"].on_era_marker_added)
	globalstate.chapter_changed.connect(mocks["chapter"].on_chapter_changed)
	return mocks


## 断开所有 6 个 mock 的连接（after_test 用）。
static func disconnect_all(globalstate: Node, mocks: Dictionary) -> void:
	if mocks.has("stat"):
		globalstate.stat_changed.disconnect(mocks["stat"].on_stat_changed)
	if mocks.has("var"):
		globalstate.var_changed.disconnect(mocks["var"].on_var_changed)
	if mocks.has("affinity"):
		globalstate.affinity_changed.disconnect(mocks["affinity"].on_affinity_changed)
	if mocks.has("event"):
		globalstate.event_triggered.disconnect(mocks["event"].on_event_triggered)
	if mocks.has("era"):
		globalstate.era_marker_added.disconnect(mocks["era"].on_era_marker_added)
	if mocks.has("chapter"):
		globalstate.chapter_changed.disconnect(mocks["chapter"].on_chapter_changed)


## §H 测试夹具契约 #1 第二步：手工断开某个 signal 上现存的所有连接。
## Godot 4.6 的 Signal 没有 disconnect_all()，必须遍历 get_connections。
static func disconnect_all_handlers(target: Object, signal_name: String) -> void:
	var sig: Signal = Signal(target, signal_name)
	var conns: Array = sig.get_connections()
	for entry in conns:
		var callable: Callable = entry["callable"]
		if sig.is_connected(callable):
			sig.disconnect(callable)
