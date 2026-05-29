# RPG Tileset Assets

下载日期：2026-05-25
总计：23 个资源包，~13,000+ 个文件，约 29 MB

## 目录结构

```
assets/tilesets/
├── kenney/          ← 12 个 Kenney 官方包（CC0，免署名）
├── opengameart/     ← 11 个 OpenGameArt 资源（CC0/CC-BY/CC-BY-SA）
├── itch/            ← itch.io 手动下载的资源
└── ITCH_MANUAL.md   ← itch.io 手动下载清单（脚本无法直下）
```

## Kenney 包（CC0）

| 包名 | 文件数 | 用途 |
|------|--------|------|
| `roguelike-rpg-pack` | 11 sheet | 俯视 RPG 主力，1700+ 块 16x16 |
| `rpg-urban-pack` | 495 | 城市素材，含 6 个四方向角色 |
| `medieval-rts` | 270 | 中世纪建筑/单位 |
| `tiny-battle` | 208 | 战棋俯视 |
| `tiny-town` | 141 | 小镇 |
| `tiny-dungeon` | 142 | 地牢，16x16 |
| `tiny-ski` | 142 | 雪地/滑雪 |
| `1-bit-pack` | 24 | 极简单色风 |
| `pixel-platformer` | 252 | 横版平台 |
| `pixel-platformer-blocks` | 338 | 横版平台扩展 |
| `monochrome-rpg` | 434 | 单色 RPG |
| `fantasy-town-kit` | 847 | 幻想城镇大包 |

## OpenGameArt 包

| 包名 | 文件数 | 授权 | 用途 |
|------|--------|------|------|
| `dungeon-crawl-stone-soup-full` | 6031 | CC0 | 海量地牢素材，已分散为单文件 |
| `dungeon-crawl-tiles` | 3047 | CC0 | 同上，旧版 |
| `DungeonCrawl_ProjectUtumno.png` | 1 | CC0 | 全图 sheet |
| `KenneyRPGpack` | 236 | CC0 | Kenney RPG 基础包（OGA 镜像） |
| `kenney_RPGurbanPack` | 495 | CC0 | 城市包（OGA 镜像，与 Kenney 站重复） |
| `mapPack` | 198 | CC0 | 世界地图 180+ 资源 |
| `NessTilesPack` | 34 | CC0 | 16x16 RPG 基础 |
| `seamless-64px-rpg-tiles` | 114 | CC-BY-SA 4.0 | 高清 64px |
| `16x16-rpg-tileset` | 29 | CC-BY-SA 3.0 / GPL 3.0 | 综合 |
| `RPGCharacterSprites32x32.png` | 1 | - | 20 个 32x32 角色 |
| `RPGSoldier32x32.png` | 1 | - | 战士角色 |

## Godot 4 导入要点

1. 把素材文件夹拖进 Godot，PNG 自动 import
2. 在 Import 面板把 **Filter** 设为 **Off**（保留像素锐利）
3. 新建 `TileSet` 资源 → 添加 atlas → 设置 tile size（通常 16 或 32）
4. 用 **Terrains**（autotile）画地面/墙壁，比手摆方便
5. 动画 tile（火把/水）：在 atlas 里配置 animation columns/frames

## 授权汇总

- **CC0**：Kenney 全部、大部分 OGA 包 → 商用/魔改/不署名都可
- **CC-BY-SA 4.0**：`seamless-64px-rpg-tiles` → 必须署名 + 衍生品同协议开源
- **CC-BY-SA 3.0 / GPL 3.0**：`16x16-rpg-tileset` → 同上

商用前再确认一遍每个包内附的 LICENSE/README.txt。
