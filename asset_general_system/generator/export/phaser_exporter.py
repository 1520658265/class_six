"""
Phaser 3 引擎导出器。

输出 Phaser 兼容的 tilemap JSON（Tiled 格式的子集）。
Phaser 原生支持 Tiled JSON，所以可以直接复用 map.tiled.json，
本导出器额外生成 Phaser 项目骨架和加载示例。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models import TilemapData


class PhaserExporter:
    """
    Phaser 3 引擎导出器。

    输出文件：
    - tilemap.json: Phaser 兼容的 tilemap（基于 Tiled 格式）
    - phaser_scene.js: 加载和显示场景的 JS 代码
    - README.md: 集成说明
    """

    def export(
        self,
        tilemap: TilemapData,
        output_dir: Path,
        scene_key: str = "MainScene",
    ) -> dict[str, Any]:
        """
        导出 Phaser 项目骨架。

        Args:
            tilemap: 地图数据
            output_dir: 输出目录
            scene_key: 场景 key 名

        Returns:
            导出报告
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        files = []

        # 1. Phaser tilemap JSON
        map_path = output_dir / "tilemap.json"
        self._export_phaser_map(tilemap, map_path)
        files.append("tilemap.json")

        # 2. 场景脚本
        scene_path = output_dir / f"{scene_key}.js"
        self._write_scene_script(scene_path, scene_key, tilemap)
        files.append(f"{scene_key}.js")

        # 3. 配套 HTML 入口
        index_path = output_dir / "index.html"
        self._write_html(index_path, scene_key)
        files.append("index.html")

        # 4. README
        readme_path = output_dir / "README.md"
        self._write_readme(readme_path, scene_key)
        files.append("README.md")

        return {
            "engine": "phaser",
            "output_dir": str(output_dir),
            "scene": scene_key,
            "files": files,
            "layers": list(tilemap.layers.keys()),
            "object_count": len(tilemap.objects),
        }

    def _export_phaser_map(self, tilemap: TilemapData, path: Path) -> None:
        """导出 Phaser 兼容的 tilemap JSON（Tiled 格式）。"""
        width = tilemap.map.width
        height = tilemap.map.height
        tile_w = tilemap.map.tile_width
        tile_h = tilemap.map.tile_height

        # Phaser 直接吃 Tiled JSON 格式
        tilesets = [
            {
                "name": tilemap.tileset.id,
                "image": tilemap.tileset.image,
                "imagewidth": tilemap.tileset.columns * tile_w,
                "imageheight": ((tilemap.tileset.tile_count + tilemap.tileset.columns - 1) // tilemap.tileset.columns) * tile_h,
                "tilewidth": tile_w,
                "tileheight": tile_h,
                "columns": tilemap.tileset.columns,
                "tilecount": tilemap.tileset.tile_count,
                "firstgid": 1,
                "margin": 0,
                "spacing": 0,
            }
        ]

        layers: list[dict[str, Any]] = []
        layer_id = 1

        # tile layers
        for name, data in tilemap.layers.items():
            layers.append({
                "id": layer_id,
                "name": name,
                "type": "tilelayer",
                "width": width,
                "height": height,
                "x": 0,
                "y": 0,
                "data": data,
                "visible": name != "collision",
                "opacity": 1.0,
            })
            layer_id += 1

        # objects layer
        objects = []
        for i, obj in enumerate(tilemap.objects, start=1):
            entry = {
                "id": i,
                "name": obj.id,
                "type": obj.type,
                "x": obj.x * tile_w,
                "y": obj.y * tile_h,
                "width": obj.width * tile_w,
                "height": obj.height * tile_h,
                "visible": True,
                "properties": [
                    {"name": k, "value": v, "type": "string"}
                    for k, v in (obj.properties or {}).items()
                ],
            }
            if obj.sprite_ref:
                entry["properties"].append({"name": "sprite_ref", "value": obj.sprite_ref, "type": "string"})
            if obj.sprite_path:
                entry["properties"].append({"name": "sprite_path", "value": obj.sprite_path, "type": "string"})
            objects.append(entry)

        if objects:
            layers.append({
                "id": layer_id,
                "name": "objects",
                "type": "objectgroup",
                "objects": objects,
                "visible": True,
                "opacity": 1.0,
            })
            layer_id += 1

        # events layer
        events = []
        for i, ev in enumerate(tilemap.events, start=1):
            events.append({
                "id": i,
                "name": ev.id,
                "type": ev.type,
                "x": ev.x * tile_w,
                "y": ev.y * tile_h,
                "width": tile_w,
                "height": tile_h,
                "visible": True,
                "point": True,
                "properties": [
                    {"name": k, "value": v, "type": "string"}
                    for k, v in (ev.properties or {}).items()
                ],
            })

        if events:
            layers.append({
                "id": layer_id,
                "name": "events",
                "type": "objectgroup",
                "objects": events,
                "visible": True,
                "opacity": 1.0,
            })

        data = {
            "type": "map",
            "version": "1.10",
            "tiledversion": "asset_general_system_phaser",
            "orientation": tilemap.map.orientation,
            "renderorder": "right-down",
            "width": width,
            "height": height,
            "tilewidth": tile_w,
            "tileheight": tile_h,
            "infinite": False,
            "nextlayerid": layer_id + 1,
            "nextobjectid": len(tilemap.objects) + len(tilemap.events) + 1,
            "tilesets": tilesets,
            "layers": layers,
        }

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_scene_script(
        self,
        path: Path,
        scene_key: str,
        tilemap: TilemapData,
    ) -> None:
        """写入 Phaser 场景脚本。"""
        tile_layers = list(tilemap.layers.keys())
        tileset_image_basename = Path(tilemap.tileset.image).stem

        content = f"""// {scene_key}.js - Phaser 3 场景示例

class {scene_key} extends Phaser.Scene {{
    constructor() {{
        super({{ key: '{scene_key}' }});
    }}

    preload() {{
        this.load.image('{tileset_image_basename}', '{tilemap.tileset.image}');
        this.load.tilemapTiledJSON('map', 'tilemap.json');
    }}

    create() {{
        const map = this.make.tilemap({{ key: 'map' }});
        const tileset = map.addTilesetImage('{tilemap.tileset.id}', '{tileset_image_basename}');

        // 创建所有 tile layer
"""
        for layer_name in tile_layers:
            visible = "false" if layer_name == "collision" else "true"
            content += f"        const {layer_name}Layer = map.createLayer('{layer_name}', tileset, 0, 0);\n"
            if layer_name == "collision":
                content += f"        if ({layer_name}Layer) {layer_name}Layer.setVisible(false);\n"

        content += """
        // 加载对象层
        const objectLayer = map.getObjectLayer('objects');
        if (objectLayer) {
            objectLayer.objects.forEach(obj => {
                const props = {};
                (obj.properties || []).forEach(p => { props[p.name] = p.value; });

                if (props.sprite_path) {
                    // 异步加载对象 sprite
                    const key = `obj_${obj.name}`;
                    this.load.image(key, props.sprite_path);
                    this.load.once('complete', () => {
                        this.add.image(obj.x + obj.width / 2, obj.y + obj.height / 2, key);
                    });
                    this.load.start();
                }
            });
        }

        // 加载事件层
        const eventLayer = map.getObjectLayer('events');
        if (eventLayer) {
            eventLayer.objects.forEach(event => {
                console.log('Event:', event.type, 'at', event.x, event.y);
            });
        }
    }

    update() {
        // 游戏逻辑
    }
}

// 导出全局
if (typeof window !== 'undefined') {
    window.""" + scene_key + """ = """ + scene_key + """;
}
"""
        path.write_text(content, encoding="utf-8")

    def _write_html(self, path: Path, scene_key: str) -> None:
        """写入 HTML 入口文件。"""
        content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Phaser Tilemap Demo</title>
    <script src="https://cdn.jsdelivr.net/npm/phaser@3/dist/phaser.min.js"></script>
    <script src="{scene_key}.js"></script>
</head>
<body>
    <div id="game"></div>
    <script>
        const config = {{
            type: Phaser.AUTO,
            parent: 'game',
            width: 1024,
            height: 768,
            scene: [{scene_key}],
            pixelArt: true,
        }};
        new Phaser.Game(config);
    </script>
</body>
</html>
"""
        path.write_text(content, encoding="utf-8")

    def _write_readme(self, path: Path, scene_key: str) -> None:
        """Phaser 集成说明。"""
        content = f"""# Phaser 3 Tilemap 集成说明

## 文件清单

- `tilemap.json`: Phaser 兼容的 tilemap（Tiled 格式）
- `{scene_key}.js`: 场景脚本示例
- `index.html`: HTML 入口（可直接浏览器打开）

## 快速开始

1. 把整个目录放到 Web 服务器（或用 `python -m http.server`）
2. 把 tileset PNG 文件复制到对应的 `tilesets/` 路径
3. 浏览器打开 `index.html` 即可看到地图

## 集成到现有 Phaser 项目

```javascript
this.load.image('default_rpg_32', 'assets/tilesets/default_rpg_32.png');
this.load.tilemapTiledJSON('map', 'assets/maps/tilemap.json');

const map = this.make.tilemap({{ key: 'map' }});
const tileset = map.addTilesetImage('default_rpg_32', 'default_rpg_32');
const terrain = map.createLayer('terrain', tileset, 0, 0);
const buildings = map.createLayer('building', tileset, 0, 0);
// ...
```

## 注意事项

- 我们的 Tiled JSON 与 Phaser 完全兼容（Phaser 原生读 Tiled 格式）
- collision 层默认 visible=false，运行时建议作为物理碰撞层
- 对象 sprite 通过 properties 中的 sprite_path 字段引用
- 想要简化集成？直接用本系统输出的 `map.tiled.json` 即可，无需本目录文件
"""
        path.write_text(content, encoding="utf-8")
