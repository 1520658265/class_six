class_name PortraitSet
extends Resource

@export var character_id: String = ""
## key 是表情名（"neutral"/"smile"/...），value 是 Texture2D（通常是 AtlasTexture）
@export var expressions: Dictionary = {}
