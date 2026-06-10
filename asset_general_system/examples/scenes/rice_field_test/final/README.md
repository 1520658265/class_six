# Godot 4.x 导入说明

## 文件清单

- `tileset.tres`: TileSet 资源
- `scene.tscn`: 主场景，包含所有 tile layer 和对象层
- `objects.json`: 对象、事件、区域数据（运行时加载）

## 导入步骤

1. 把整个目录复制到 Godot 项目下，例如 `res://maps/`
2. 确保 tileset 引用的 PNG 文件路径正确（相对 res://）
3. 在 Godot 中打开 `scene.tscn` 即可看到地图

## 运行时使用对象数据

```gdscript
extends Node2D

var objects_data: Dictionary

func _ready() -> void:
    var file := FileAccess.open("res://maps/objects.json", FileAccess.READ)
    objects_data = JSON.parse_string(file.get_as_text())
    _spawn_objects()

func _spawn_objects() -> void:
    for obj in objects_data["objects"]:
        if obj.has("sprite_path"):
            var sprite := Sprite2D.new()
            sprite.texture = load("res://" + obj["sprite_path"])
            sprite.position = Vector2(
                obj["x"] * objects_data["map"]["tile_width"],
                obj["y"] * objects_data["map"]["tile_height"]
            )
            $Objects.add_child(sprite)
```

## 注意事项

- collision 层默认 visible=false，运行时用作物理碰撞参考
- objects/events 层在场景中是 Node2D 占位符，附带 metadata 属性
- 完整对象逻辑请通过 `objects.json` 加载
