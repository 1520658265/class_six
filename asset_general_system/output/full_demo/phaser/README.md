# Phaser 3 Tilemap 集成说明

## 文件清单

- `tilemap.json`: Phaser 兼容的 tilemap（Tiled 格式）
- `DemoScene.js`: 场景脚本示例
- `index.html`: HTML 入口（可直接浏览器打开）

## 快速开始

1. 把整个目录放到 Web 服务器（或用 `python -m http.server`）
2. 把 tileset PNG 文件复制到对应的 `tilesets/` 路径
3. 浏览器打开 `index.html` 即可看到地图

## 集成到现有 Phaser 项目

```javascript
this.load.image('default_rpg_32', 'assets/tilesets/default_rpg_32.png');
this.load.tilemapTiledJSON('map', 'assets/maps/tilemap.json');

const map = this.make.tilemap({ key: 'map' });
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
