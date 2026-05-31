## 全局 UI 根节点（autoload）。
## 持有 DialogueBox、StatPanel、ChapterTitle、EraMarker 等 CanvasLayer 子场景，
## 这样切场景时 UI 不会被销毁，并且任何地方都可以通过 UIRoot.show_chapter_title() 调用。
extends Node

const DIALOGUE_BOX_SCENE := preload("res://scenes/ui/dialogue_box.tscn")
const STAT_PANEL_SCENE := preload("res://scenes/ui/stat_panel.tscn")
const CHAPTER_TITLE_SCENE := preload("res://scenes/ui/chapter_title.tscn")
const ERA_MARKER_SCENE := preload("res://scenes/ui/era_marker_toast.tscn")

var dialogue_box: CanvasLayer
var stat_panel: CanvasLayer
var chapter_title: CanvasLayer
var era_marker_toast: CanvasLayer

func _ready() -> void:
	dialogue_box = DIALOGUE_BOX_SCENE.instantiate()
	add_child(dialogue_box)
	stat_panel = STAT_PANEL_SCENE.instantiate()
	add_child(stat_panel)
	chapter_title = CHAPTER_TITLE_SCENE.instantiate()
	add_child(chapter_title)
	era_marker_toast = ERA_MARKER_SCENE.instantiate()
	add_child(era_marker_toast)
	GlobalState.chapter_changed.connect(_on_chapter_changed)
	GlobalState.era_marker_added.connect(_on_era_marker)

func show_chapter_title(text: String) -> void:
	if chapter_title.has_method("show_title"):
		chapter_title.show_title(text)

func _on_chapter_changed(chapter_id: String) -> void:
	var titles := {
		"prologue": "序章 · 二楼的窗",
		"ch1": "第一章 · 蒸饭盒里的秋天",
		"ch1_done": "Demo · 序章 + 第一章 完结",
	}
	if titles.has(chapter_id):
		show_chapter_title(titles[chapter_id])

func _on_era_marker(marker_id: String) -> void:
	if era_marker_toast.has_method("show_marker"):
		era_marker_toast.show_marker(marker_id)
