## 主角控制器。读 InputMap 驱动基类的 _move_input。
## 加 F1（切 collision 调试可视）/ F2（打印当前坐标）调试键。
extends BaseCharacterController

var _debug_collision_visible: bool = false

func _ready() -> void:
	character_id = AssetIds.Char.YUANSHENG
	add_to_group("player")
	super()
	print("[yuansheng] controller ready, animations: ", sprite.sprite_frames.get_animation_names())

func _physics_process(delta: float) -> void:
	_move_input = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	_is_running = Input.is_action_pressed("run")
	super(delta)

func _unhandled_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	if event.keycode == KEY_F1:
		_toggle_collision_debug()
		get_viewport().set_input_as_handled()
	elif event.keycode == KEY_F2:
		print("[pos] %s @ (%d, %d) facing=%s" % [
			SceneRouter.current_scene_id,
			int(global_position.x), int(global_position.y),
			get_facing(),
		])
		get_viewport().set_input_as_handled()

func _toggle_collision_debug() -> void:
	_debug_collision_visible = not _debug_collision_visible
	for node in get_tree().get_nodes_in_group("debug_collision"):
		node.visible = _debug_collision_visible
	print("[debug] collision visible = %s" % _debug_collision_visible)
