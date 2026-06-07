# AI RPG 资产生成系统需求文档

更新时间：2026-06-05

## 1. 项目定位

`asset_general_system` 作为一套系统级 AI 游戏资产生成工具的根目录。系统目标是根据用户的自然语言描述，生成可进入游戏制作流程的 RPG 风格资产，而不是只生成一张不可编辑的图片。

系统第一阶段聚焦 2D top-down RPG 地图生成，后续扩展到地图元素、角色、特效和动画帧。

核心价值：

- 可编辑：输出 tilemap、对象层、碰撞层、事件层等结构化数据。
- 可导入：优先支持 Tiled JSON，后续支持 Godot、Unity、Phaser。
- 可验证：地图需要满足可走、可达、入口无遮挡、关键对象可交互等游戏逻辑约束。
- 可迭代：支持局部重生成、锁定区域、seed 复现和版本历史。
- 风格一致：地图、角色、特效需要保持统一的视觉风格和资产规格。

## 2. 目标用户

- 独立游戏开发者：快速生成 RPG 场景、角色和特效素材。
- 关卡设计师：通过自然语言生成初版地图，再进行编辑和调整。
- 美术/技术美术：批量生成符合规格的 sprite、tileset、VFX 帧。
- 教学/原型团队：快速构建可运行的 RPG demo 场景。

## 3. 需求范围

### 3.1 第一阶段范围

第一阶段只做地图最小闭环：

```text
用户描述 -> RPGMapSpec JSON -> 地图生成 -> 规则校验 -> 预览图 -> Tiled JSON 导出
```

第一阶段约束：

- 地图类型：2D top-down RPG。
- 地图模式：orthogonal tilemap。
- 默认 tile 尺寸：32x32。
- 默认地图尺寸：64x64，可配置。
- 视觉风格：先以像素风为主。
- 素材来源：先使用固定 tileset，不在第一阶段生成新素材。
- 主导出格式：Tiled JSON。

### 3.2 后续阶段范围

后续扩展：

- 局部重生成和编辑器工作流。
- 地图元素生成，例如树、摊位、神庙、宝箱、石碑。
- 角色 sprite sheet 生成，例如 NPC、怪物、主角。
- 特效动画帧生成，例如火球、治疗、斩击、传送、爆炸。
- Godot、Unity、Phaser 导出和运行时适配。

### 3.3 暂不纳入范围

第一阶段暂不处理：

- 3D 地图。
- 斜 45 度等距地图。
- 完整剧情/任务系统自动生成。
- 完整战斗系统自动生成。
- 商业级美术一致性训练。
- 直接生成不可编辑的大图作为最终地图。

## 4. 核心功能需求

### 4.1 自然语言解析

系统需要把用户描述解析为结构化地图规格 `RPGMapSpec`。

示例输入：

```text
生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙，村民可以在道路上行走。
```

示例输出：

```json
{
  "theme": "autumn_forest_village",
  "map_size": [64, 64],
  "tile_size": [32, 32],
  "regions": [
    {"id": "river_01", "type": "river", "position": "left", "size": "medium"},
    {"id": "market_01", "type": "market", "position": "center", "size": "medium"},
    {"id": "temple_01", "type": "temple", "position": "top_right", "size": "small"}
  ],
  "paths": [
    {"from": "market_01", "to": "temple_01"},
    {"from": "market_01", "to": "spawn_01"}
  ],
  "entities": [
    {"type": "villager", "count": 6},
    {"type": "merchant", "count": 2}
  ],
  "constraints": {
    "walkable_spawn": true,
    "connect_key_regions": true,
    "no_blocked_doors": true
  }
}
```

能力要求：

- 支持中文和英文描述。
- 支持从描述中提取主题、地形、区域、建筑、道路、对象、NPC、事件点。
- 支持默认值补全，例如缺少地图大小时使用 64x64。
- 支持冲突检测，例如“全水域地图但要求大量房屋和道路”。
- 支持 seed，保证同一输入和 seed 可复现。

### 4.2 地图生成

地图生成器根据 `RPGMapSpec` 生成分层 tilemap。

基础层级：

- `terrain`：草地、泥地、雪地、沙地、石地、水域等。
- `path`：道路、小径、桥梁。
- `building`：房屋、神庙、地牢入口、墙体。
- `decoration`：树、花、石头、路牌、摊位。
- `collision`：不可行走区域。
- `object`：宝箱、门、传送点、采集点等可交互对象。
- `entity`：NPC、怪物、出生点。
- `event`：触发区、任务点、区域切换点。

生成算法可组合使用：

- Cellular Automata：森林、洞穴、水域、自然斑块。
- WFC：tile 连接规则、边缘过渡、墙体和地形拼接。
- BSP / room graph：地牢、室内、建筑结构。
- A* / road planner：道路、桥梁、关键区域连通。
- Rule engine：放置规则、碰撞规则、可达性约束。

### 4.3 地图验证

每次生成后必须执行校验。

最低校验项：

- 出生点必须可行走。
- 关键区域之间必须可达。
- 建筑入口不能被阻挡。
- NPC 不能生成在不可行走区域。
- 宝箱、门、传送点等交互对象必须有可达邻接格。
- 水、墙、悬崖、树、建筑默认生成碰撞。
- 地图边界处理正确，不出现越界对象。
- 导出的 Tiled JSON 能被 Tiled 打开。

失败处理：

- 自动重试局部生成。
- 自动移动违规对象到最近合法位置。
- 返回明确的错误报告，标记问题 tile 坐标。

### 4.4 预览和编辑

系统需要提供地图预览能力。

第一阶段最低能力：

- 生成 PNG 预览图。
- 显示地图尺寸、seed、主题、导出路径。
- 可查看主要层级是否存在。

后续编辑能力：

- 框选区域重生成。
- 锁定区域不变。
- 撤销和重做。
- 导入已有 Tiled JSON 后继续编辑。
- 对局部区域输入描述，例如“把这里改成集市”。
- 显示碰撞层、事件层、导航连通性。

### 4.5 素材库和素材匹配

第一阶段使用固定 tileset。

素材库需要维护 metadata：

```json
{
  "asset_id": "tree_oak_01",
  "kind": "tile_object",
  "tags": ["tree", "forest", "blocking"],
  "theme": ["forest", "village"],
  "tile_size": [32, 32],
  "footprint": [1, 2],
  "collision": [[0, 1]],
  "anchor": "bottom_center"
}
```

后续需要支持：

- 根据语义标签匹配 tile 或 object。
- 根据主题过滤素材，例如森林、雪地、沙漠、地牢。
- 支持同义词映射，例如 `temple`、`shrine`、`sanctuary`。
- 支持用户上传 tileset 并自动标注。
- 缺失素材时触发图像生成。

### 4.6 地图元素生成

地图元素包括建筑、装饰物、道具、交互对象。

输出要求：

- PNG 透明背景。
- 尺寸符合 tile 网格，例如 32x32、64x64、96x96。
- metadata 包含 footprint、anchor、collision、semantic tags。
- 可放入 object library。
- 可被地图生成器自动放置。

示例对象：

- 树、石头、花丛、灌木。
- 房屋、神庙、桥、门、路牌。
- 宝箱、采集点、传送阵、任务标记。
- 摊位、灯笼、雕像、井。

### 4.7 角色 sprite sheet

角色生成后需要是游戏可用的动画表，而不是单张图。

第一版角色规格：

- 方向：down、left、right、up。
- 动作：idle、walk。
- 帧数：每动作 4 帧或 6 帧。
- 尺寸：32x48 或 48x64，可配置。
- 背景：透明。
- 输出：PNG sprite sheet + JSON metadata。

后续扩展：

- run、attack、cast、hurt、death。
- 武器挂点。
- hitbox。
- shadow。
- portrait。
- 角色风格一致性检查。

metadata 示例：

```json
{
  "asset_id": "villager_merchant_01",
  "frame_size": [32, 48],
  "directions": ["down", "left", "right", "up"],
  "animations": {
    "walk_down": {"row": 0, "frames": 4, "fps": 8, "loop": true},
    "idle_down": {"row": 4, "frames": 4, "fps": 4, "loop": true}
  },
  "anchor": "feet_center",
  "hitbox": [8, 28, 16, 16]
}
```

### 4.8 特效动画帧

特效需要输出可直接挂到技能或事件上的 sprite sheet。

基础类型：

- 火球。
- 斩击。
- 治疗光环。
- 爆炸。
- 传送。
- 闪光。
- 雨、雪、落叶等环境特效。

metadata 示例：

```json
{
  "asset_id": "fireball_small_01",
  "frame_size": [64, 64],
  "frames": 8,
  "fps": 12,
  "loop": false,
  "blend": "additive",
  "anchor": "center"
}
```

### 4.9 导出

第一优先级：

- Tiled JSON。
- PNG 预览图。
- assets metadata JSON。

第二优先级：

- Godot TileMap / TileSet 适配。
- Unity Tilemap 适配。
- Phaser tilemap 适配。

导出要求：

- 地图层级清晰。
- tile id 映射稳定。
- 对象层包含坐标、类型、属性。
- 碰撞层和事件层可被引擎读取。
- 资源路径使用相对路径，便于项目迁移。

## 5. 非功能需求

### 5.1 可复现

- 每次生成任务记录 prompt、spec、seed、tileset 版本、生成器版本。
- 同一输入和 seed 应尽可能复现同一地图。

### 5.2 可扩展

- 地图生成算法、素材生成器、导出器需要插件化。
- 新主题、新 tileset、新对象类型不应要求重写核心流程。

### 5.3 可测试

- `RPGMapSpec` 需要 schema 校验。
- 地图生成结果需要自动运行规则校验。
- 导出器需要样例回归测试。

### 5.4 性能

第一阶段目标：

- 64x64 地图生成在 10 秒内完成，不含远程图像生成。
- PNG 预览在 3 秒内完成。
- 失败重试次数可配置。

### 5.5 版权和素材来源

- 所有内置素材需要记录来源和许可。
- 用户上传素材需要记录归属。
- AI 生成素材需要记录模型、prompt、seed 和生成时间。

## 6. 项目目录建议

建议后续按以下结构演进：

```text
asset_general_system/
  REQUIREMENTS.md
  ROADMAP.md
  README.md
  specs/
    rpg_map_spec.schema.json
    asset_metadata.schema.json
    sprite_sheet.schema.json
  docs/
    architecture.md
    export_formats.md
    validation_rules.md
  generator/
    map/
    assets/
    characters/
    vfx/
  exporters/
    tiled/
    godot/
    unity/
    phaser/
  editor/
  examples/
    prompts/
    maps/
    previews/
  tests/
```

## 7. 关键开放问题

- 第一版固定 tileset 使用哪一套，是否允许商用。
- 第一版是否只支持像素风，还是同时支持手绘风。
- 第一版面向 Godot 还是 Unity 做深度适配。
- 是否优先做本地生成，还是云端任务队列。
- 是否需要多人协作和资产版本管理。
- 角色和特效是否依赖已有图像生成模型，还是先只做规格和导出。

