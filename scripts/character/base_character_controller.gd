## 公共角色控制器基类。
## 提供 4 方向 walk/idle 动画切换、面向跟踪、SpriteFrames 加载。
## 不处理输入；子类决定如何驱动 _move_input。
##
## 注意：左右共用同一行的 sprite，靠 sprite.flip_h 实现镜像，
## 这样不依赖 walksheet 里 left/right 行实际怎么排，对所有 NPC 都安全。
class_name BaseCharacterController
extends CharacterBody2D

const SPEED_WALK := 120.0
const SPEED_RUN := 220.0

@onready var sprite: AnimatedSprite2D = $AnimatedSprite2D

var character_id: String = ""
var _facing: String = "down"
var _move_input: Vector2 = Vector2.ZERO
var _is_running: bool = false

func _ready() -> void:
	if character_id != "":
		_load_sprite_frames(character_id)
	_apply_idle_pose()

func _load_sprite_frames(id: String) -> void:
	var sf := Sprites.walk_frames(id)
	if sf == null:
		push_error("[%s] failed to load SpriteFrames for %s" % [name, id])
		return
	sprite.sprite_frames = sf
	_apply_idle_pose()

func _apply_idle_pose() -> void:
	if sprite.sprite_frames == null:
		return
	sprite.animation = _anim_for_facing(_facing)
	sprite.flip_h = (_facing == "left")
	sprite.frame = 0
	sprite.pause()

func set_facing(dir: String) -> void:
	if dir not in ["up", "down", "left", "right"]:
		return
	_facing = dir
	_apply_idle_pose()

func get_facing() -> String:
	return _facing

func _physics_process(_delta: float) -> void:
	## 对话播放时不允许移动
	if Dialogue.is_playing():
		velocity = Vector2.ZERO
		_move_input = Vector2.ZERO
		sprite.pause()
		return
	var speed := SPEED_RUN if _is_running else SPEED_WALK
	velocity = _move_input * speed
	move_and_slide()
	_update_animation(_move_input)

func _update_animation(input: Vector2) -> void:
	if input == Vector2.ZERO:
		sprite.pause()
		return
	var dir := _pick_direction(input)
	var anim := _anim_for_facing(dir)
	sprite.flip_h = (dir == "left")
	if sprite.animation != anim:
		sprite.play(anim)
	elif not sprite.is_playing():
		sprite.play()
	_facing = dir

func _pick_direction(input: Vector2) -> String:
	if abs(input.x) >= abs(input.y):
		return "right" if input.x > 0 else "left"
	return "down" if input.y > 0 else "up"

## 左右共用 walk_right 行 + 翻转。这样不依赖 sheet 行实际是 left 还是 right。
func _anim_for_facing(dir: String) -> String:
	match dir:
		"left", "right":
			return "walk_right"
		"up":
			return "walk_up"
		_:
			return "walk_down"

## 由 cutscene runner 调用：阻塞式走到一个全局坐标。
func walk_to(target: Vector2, tolerance: float = 4.0) -> void:
	while global_position.distance_to(target) > tolerance:
		_move_input = (target - global_position).normalized()
		await get_tree().physics_frame
	_move_input = Vector2.ZERO
