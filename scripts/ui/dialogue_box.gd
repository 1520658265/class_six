## DialogueBox：订阅 Dialogue autoload 信号，呈现立绘+姓名条+正文+选项。
## 打字机效果：完整文本前按 interact 立刻补全；补全后再按 interact 推进。
##
## 输入用 _process + Input.is_action_just_pressed，不用 _unhandled_input：
##  1) 焦点 Control 不会吃掉
##  2) 跟选项按钮的 pressed 信号互不干扰
extends CanvasLayer

const TYPE_INTERVAL := 0.025

@onready var portrait_rect: TextureRect = $Root/Frame/HBox/Portrait
@onready var name_label: Label = $Root/Frame/HBox/RightCol/NameBar/NameLabel
@onready var text_label: RichTextLabel = $Root/Frame/HBox/RightCol/TextPanel/TextLabel
@onready var choices_box: VBoxContainer = $Root/Frame/HBox/RightCol/Choices
@onready var typing_timer: Timer = $TypingTimer

var _full_text: String = ""
var _typed_chars: int = 0
var _line_finished_typing: bool = false

func _ready() -> void:
	visible = false
	set_process(true)
	Dialogue.line_entered.connect(_on_line_entered)
	Dialogue.choices_offered.connect(_on_choices_offered)
	Dialogue.dialogue_finished.connect(_on_dialogue_finished)
	typing_timer.timeout.connect(_on_typing_tick)

func _process(_delta: float) -> void:
	if not visible:
		return
	if not Dialogue.is_playing():
		return
	if not Input.is_action_just_pressed("interact"):
		return
	if not _line_finished_typing:
		_complete_typing()
		return
	if choices_box.get_child_count() > 0:
		## 选项框可见时让按钮自己接 Enter，不在这里推进
		return
	Dialogue.advance()

func _on_line_entered(line: Dictionary) -> void:
	visible = true
	_clear_choices()
	_set_portrait(line.get("speaker_id", ""), line.get("expression", "neutral"))
	var speaker: String = line.get("speaker", "")
	name_label.text = speaker
	name_label.visible = speaker != ""
	_full_text = line.get("text", "")
	_typed_chars = 0
	_line_finished_typing = false
	text_label.text = ""
	if _full_text.is_empty():
		_line_finished_typing = true
	else:
		typing_timer.start(TYPE_INTERVAL)

func _on_typing_tick() -> void:
	_typed_chars += 1
	if _typed_chars >= _full_text.length():
		_complete_typing()
		return
	text_label.text = _full_text.substr(0, _typed_chars)

func _complete_typing() -> void:
	typing_timer.stop()
	text_label.text = _full_text
	_typed_chars = _full_text.length()
	_line_finished_typing = true

func _on_choices_offered(line: Dictionary, available_indices: Array) -> void:
	await _wait_until_typed()
	_clear_choices()
	choices_box.visible = true
	for visible_index in range(available_indices.size()):
		var actual_index: int = available_indices[visible_index]
		var ch: Dictionary = line["choices"][actual_index]
		var btn := Button.new()
		btn.text = "%d. %s" % [visible_index + 1, ch.get("label", "...")]
		btn.focus_mode = Control.FOCUS_ALL
		btn.pressed.connect(_on_choice_pressed.bind(visible_index))
		choices_box.add_child(btn)
	if choices_box.get_child_count() > 0:
		choices_box.get_child(0).grab_focus()

func _wait_until_typed() -> void:
	while not _line_finished_typing:
		await get_tree().process_frame

func _on_choice_pressed(index: int) -> void:
	_clear_choices()
	Dialogue.choose(index)

func _clear_choices() -> void:
	for c in choices_box.get_children():
		c.queue_free()
	choices_box.visible = false

func _on_dialogue_finished(_start_line_id: String) -> void:
	visible = false
	_clear_choices()

func _set_portrait(speaker_id: String, expression: String) -> void:
	if speaker_id == "":
		portrait_rect.visible = false
		portrait_rect.texture = null
		return
	var tex := Portraits.get_expression(speaker_id, expression)
	if tex == null:
		tex = Portraits.get_expression(speaker_id, "neutral")
	portrait_rect.visible = tex != null
	portrait_rect.texture = tex
