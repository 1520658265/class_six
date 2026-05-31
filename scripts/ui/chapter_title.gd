## 章节标题卡：淡入 → 停留 → 淡出。
extends CanvasLayer

@onready var label: Label = $Center/Label

func _ready() -> void:
	layer = 70
	visible = false

func show_title(text: String) -> void:
	label.text = text
	visible = true
	label.modulate.a = 0.0
	var tween := create_tween()
	tween.tween_property(label, "modulate:a", 1.0, 0.6)
	tween.tween_interval(1.6)
	tween.tween_property(label, "modulate:a", 0.0, 0.6)
	tween.tween_callback(func(): visible = false)
