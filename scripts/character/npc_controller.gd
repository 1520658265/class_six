## NPC 控制器。无输入；默认站桩 idle，由 cutscene runner 通过 walk_to 接管移动。
## 通过 character_id 指定使用哪套 walk SpriteFrames。
class_name NpcController
extends BaseCharacterController

## 此 NPC 是否在 demo 内开放主角主动 interact 触发对话
@export var interactable: bool = true
## 主角靠近时（互动半径内）按 Z 触发的对话起始 line_id；空字符串则不触发对话
@export var dialogue_line_id: String = ""
## 是否随主角朝向（站桩 NPC 转身看向主角）
@export var face_player_on_interact: bool = true

func _ready() -> void:
	if character_id == "":
		push_error("[%s] NpcController.character_id 未配置" % name)
	super()
	var iz: InteractZone = get_node_or_null("InteractZone")
	if iz != null:
		iz.interacted.connect(_on_interacted)
		iz.enabled = interactable and dialogue_line_id != ""

func _on_interacted(by_player: Node2D) -> void:
	if dialogue_line_id == "":
		return
	if Dialogue.is_playing():
		return
	if face_player_on_interact and by_player is Node2D:
		var dx := by_player.global_position.x - global_position.x
		var dy := by_player.global_position.y - global_position.y
		if abs(dx) > abs(dy):
			set_facing("right" if dx > 0 else "left")
		else:
			set_facing("down" if dy > 0 else "up")
	Dialogue.play(dialogue_line_id)
