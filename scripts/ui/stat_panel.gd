## 属性面板：Tab 键切换显示。订阅 GlobalState.stat_changed 实时刷新 + 飘字。
extends CanvasLayer

const STAT_NAMES := {
	"xuexi": "学习",
	"danliang": "胆量",
	"koucai": "口才",
	"tili": "体力",
}

@onready var panel: Control = $Panel
@onready var stats_box: VBoxContainer = $Panel/Margin/VBox/StatsBox
@onready var float_layer: Control = $FloatLayer

var _label_map: Dictionary = {}
var _is_showing: bool = false

func _ready() -> void:
	layer = 50
	panel.visible = false
	GlobalState.stat_changed.connect(_on_stat_changed)
	_build_rows()
	_refresh_all()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_TAB:
		toggle()
		get_viewport().set_input_as_handled()

func toggle() -> void:
	_is_showing = not _is_showing
	panel.visible = _is_showing
	if _is_showing:
		_refresh_all()

func _build_rows() -> void:
	for c in stats_box.get_children():
		c.queue_free()
	_label_map.clear()
	for sid in STAT_NAMES:
		var hb := HBoxContainer.new()
		var name_lbl := Label.new()
		name_lbl.text = STAT_NAMES[sid]
		name_lbl.custom_minimum_size = Vector2(80, 0)
		hb.add_child(name_lbl)
		var val_lbl := Label.new()
		val_lbl.name = "Value"
		val_lbl.text = "0"
		val_lbl.custom_minimum_size = Vector2(40, 0)
		hb.add_child(val_lbl)
		var bar := ProgressBar.new()
		bar.name = "Bar"
		bar.min_value = 0
		bar.max_value = 10
		bar.value = 0
		bar.custom_minimum_size = Vector2(160, 0)
		bar.show_percentage = false
		hb.add_child(bar)
		stats_box.add_child(hb)
		_label_map[sid] = {"value": val_lbl, "bar": bar}

func _refresh_all() -> void:
	for sid in STAT_NAMES:
		_refresh_stat(sid)

func _refresh_stat(sid: String) -> void:
	var v := GlobalState.get_stat(sid)
	var entry: Dictionary = _label_map.get(sid, {})
	if entry.is_empty():
		return
	(entry["value"] as Label).text = str(v)
	(entry["bar"] as ProgressBar).value = v

func _on_stat_changed(sid: String, delta: int, _new_value: int) -> void:
	_refresh_stat(sid)
	_spawn_float_text(sid, delta)

func _spawn_float_text(sid: String, delta: int) -> void:
	var prefix := "+" if delta >= 0 else ""
	var name_text: String = STAT_NAMES.get(sid, sid)
	var lbl := Label.new()
	lbl.text = "%s%d %s" % [prefix, delta, name_text]
	lbl.modulate = Color(1.0, 0.9, 0.4, 1.0) if delta >= 0 else Color(1.0, 0.5, 0.5, 1.0)
	lbl.position = Vector2(get_viewport().get_visible_rect().size.x * 0.5, 80)
	lbl.add_theme_font_size_override("font_size", 22)
	float_layer.add_child(lbl)
	var tween := lbl.create_tween()
	tween.tween_property(lbl, "position:y", lbl.position.y - 60.0, 1.2)
	tween.parallel().tween_property(lbl, "modulate:a", 0.0, 1.2)
	tween.tween_callback(lbl.queue_free)
