## 时代切片标记 toast：屏幕右上角短暂显示"+ <切片名>"。
extends CanvasLayer

const MARKER_NAMES := {
	"kaixue": "时代切片 · 开学",
	"shenzhou7": "时代切片 · 神舟七号",
	"sanlu": "时代切片 · 三鹿",
}

@onready var label: Label = $Box/Margin/Label

func _ready() -> void:
	layer = 60
	visible = false

func show_marker(marker_id: String) -> void:
	var t: String = MARKER_NAMES.get(marker_id, marker_id)
	label.text = t
	visible = true
	$Box.modulate.a = 0.0
	$Box.position.x = 60
	var tween := create_tween()
	tween.tween_property($Box, "modulate:a", 1.0, 0.4)
	tween.parallel().tween_property($Box, "position:x", 0.0, 0.4)
	tween.tween_interval(2.0)
	tween.tween_property($Box, "modulate:a", 0.0, 0.4)
	tween.tween_callback(func(): visible = false)
