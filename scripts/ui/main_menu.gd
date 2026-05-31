## 主菜单：开始新游戏 / 继续游戏 / 退出。
## 继续游戏会读 slot 0，没存档时按钮变灰。
extends Control

@onready var btn_new: Button = $Center/VBox/BtnNew
@onready var btn_continue: Button = $Center/VBox/BtnContinue
@onready var btn_quit: Button = $Center/VBox/BtnQuit

func _ready() -> void:
	btn_new.pressed.connect(_on_new_game)
	btn_continue.pressed.connect(_on_continue)
	btn_quit.pressed.connect(_on_quit)
	btn_continue.disabled = not SaveManager.has_save(0)
	btn_new.grab_focus()

func _on_new_game() -> void:
	GlobalState.reset_to_initial()
	## 释放按钮焦点，避免 Enter 残留触发对话推进
	for b in [btn_new, btn_continue, btn_quit]:
		b.release_focus()
		b.disabled = true
	## 直接切场；章节标题改由 LevelBase 在新场景里弹出，
	## 避免半透明背景压在还没释放的菜单文字上
	await SceneRouter.change_scene("home", "default")

func _on_continue() -> void:
	for b in [btn_new, btn_continue, btn_quit]:
		b.release_focus()
		b.disabled = true
	var data: Dictionary = SaveManager.load_slot(0)
	if data.is_empty():
		return
	SceneRouter.resume_from_save(data)

func _on_quit() -> void:
	get_tree().quit()
