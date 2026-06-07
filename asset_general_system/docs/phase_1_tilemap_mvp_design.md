# 第一阶段设计文档：文本生成 RPG Tilemap MVP

更新时间：2026-06-05

## 1. 阶段目标

第一阶段目标是跑通从用户自然语言描述到可视化 RPG tilemap 资产包的最小闭环。

核心链路：

```text
用户描述
  -> Prompt Parser
  -> RPGMapSpec JSON
  -> Map Generator
  -> Validator
  -> Preview Renderer
  -> Tiled JSON Exporter
  -> 输出资产包
```

第一阶段产物不是一张普通图片，而是一套可以继续进入游戏制作流程的结构化地图资产。

必须输出：

- `map_spec.json`：结构化地图需求。
- `map_data.json`：系统内部 tilemap 数据。
- `map.tiled.json`：Tiled JSON 导出文件。
- `preview.png`：地图预览图。
- `validation_report.json`：地图校验报告。
- `generation_report.json`：生成过程报告。

## 2. 技术路线

第一阶段采用独立生成工具路线，不把生成逻辑绑定在 Godot、Unity 或 Phaser 中。

推荐框架：

```text
语言：Python
CLI：Typer 或 argparse
数据模型：Pydantic
Schema 导出：JSON Schema
预览渲染：Pillow
地图导出：Tiled JSON
测试：pytest
可选依赖：numpy、networkx
```

### 2.1 为什么第一阶段用 Python

Python 更适合第一阶段的生成流水线：

- 适合做 LLM 接入和 prompt 解析。
- 适合做 schema 校验、规则校验、批量测试。
- 适合做 PNG 预览、素材切图、metadata 处理。
- 后续可以包装成 CLI、API 服务或任务队列。

### 2.2 为什么用 Tiled JSON

Tiled JSON 作为第一阶段标准导出格式，原因是：

- 表达 tile layer、object layer、tileset、地图尺寸、tile 尺寸比较直接。
- 可以被 Tiled 编辑器打开并继续编辑。
- 适合作为 Godot、Unity、Phaser 的中间交换格式。
- 支持自定义属性，可以承载 collision、event、spawn 等游戏逻辑信息。

### 2.3 第一阶段不做什么

第一阶段暂不做：

- Web 编辑器。
- Godot 插件。
- Unity 插件。
- Phaser 运行 demo。
- 角色 sprite sheet 生成。
- 特效动画帧生成。
- 新 tileset 或 object sprite 自动生成。
- 局部重生成。

这些能力放到后续阶段。

## 3. 用户体验目标

第一阶段以 CLI 形式提供能力。

示例命令：

```bash
python -m asset_general_system.generate_map \
  --prompt "生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙" \
  --theme autumn_forest_village \
  --size 64x64 \
  --seed 20260605 \
  --output outputs/demo_autumn_village
```

生成后输出：

```text
outputs/demo_autumn_village/
  map_spec.json
  map_data.json
  map.tiled.json
  preview.png
  validation_report.json
  generation_report.json
```

第一阶段验收时，用户应该能做到：

1. 输入一段地图描述。
2. 得到一张可查看的 `preview.png`。
3. 得到一个可被 Tiled 打开的 `map.tiled.json`。
4. 看到地图是否通过可达性、碰撞和对象放置校验。

## 4. 输入输出定义

### 4.1 输入

基础输入：

```json
{
  "prompt": "生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙",
  "theme": "autumn_forest_village",
  "map_size": [64, 64],
  "tile_size": [32, 32],
  "seed": 20260605
}
```

必填字段：

- `prompt`：用户自然语言描述。

可选字段：

- `theme`：主题，不填时由 prompt parser 推断。
- `map_size`：地图尺寸，不填默认 `[64, 64]`。
- `tile_size`：tile 尺寸，不填默认 `[32, 32]`。
- `seed`：随机种子，不填时自动生成。
- `tileset_id`：指定 tileset，不填时根据主题选择默认 tileset。

### 4.2 输出资产包

每次生成任务输出一个独立目录：

```text
outputs/{task_id}/
  map_spec.json
  map_data.json
  map.tiled.json
  preview.png
  validation_report.json
  generation_report.json
```

文件说明：

- `map_spec.json`：LLM 或规则解析后的结构化需求。
- `map_data.json`：内部地图数据，便于调试和后续导出。
- `map.tiled.json`：Tiled 标准导出。
- `preview.png`：合成预览图。
- `validation_report.json`：规则校验结果。
- `generation_report.json`：prompt、seed、版本、耗时、重试记录。

## 5. 系统架构

### 5.1 模块划分

```text
PromptParser
  将用户描述解析为 RPGMapSpec

SpecNormalizer
  补全默认值，处理同义词，规整主题和区域配置

MapGenerator
  根据 RPGMapSpec 生成内部 TilemapData

LayerComposer
  生成 terrain、path、building、decoration、collision、object、event 等层

Validator
  校验可达性、碰撞、入口、对象放置等规则

PreviewRenderer
  根据 TilemapData 和 tileset 渲染 PNG 预览

TiledExporter
  将 TilemapData 导出为 Tiled JSON

ReportWriter
  输出校验报告和生成报告
```

### 5.2 数据流

```text
GenerateRequest
  -> PromptParser.parse()
  -> RPGMapSpec
  -> SpecNormalizer.normalize()
  -> NormalizedRPGMapSpec
  -> MapGenerator.generate()
  -> TilemapData
  -> Validator.validate()
  -> ValidationReport
  -> PreviewRenderer.render()
  -> preview.png
  -> TiledExporter.export()
  -> map.tiled.json
  -> ReportWriter.write()
```

### 5.3 失败处理

生成失败分三类：

- `SPEC_ERROR`：prompt 无法解析或 spec 冲突。
- `GENERATION_ERROR`：地图生成失败，例如关键区域无法放置。
- `VALIDATION_ERROR`：地图生成成功但校验不通过。

处理策略：

- `SPEC_ERROR`：返回明确错误和可修复建议。
- `GENERATION_ERROR`：允许按 seed 派生最多重试 3 次。
- `VALIDATION_ERROR`：优先自动修复，修复失败后输出失败报告。

## 6. 核心数据模型

### 6.1 RPGMapSpec

`RPGMapSpec` 是第一阶段最关键的协议。它连接 prompt parser、地图生成器、校验器和导出器。

示例：

```json
{
  "version": "0.1.0",
  "id": "autumn_village_001",
  "title": "秋季森林村庄",
  "theme": "autumn_forest_village",
  "map": {
    "width": 64,
    "height": 64,
    "tile_width": 32,
    "tile_height": 32,
    "orientation": "orthogonal"
  },
  "regions": [
    {
      "id": "river_01",
      "type": "river",
      "position": "left",
      "size": "medium",
      "priority": 90
    },
    {
      "id": "market_01",
      "type": "market",
      "position": "center",
      "size": "medium",
      "priority": 80
    },
    {
      "id": "temple_01",
      "type": "temple",
      "position": "top_right",
      "size": "small",
      "priority": 80
    }
  ],
  "paths": [
    {
      "from": "market_01",
      "to": "temple_01",
      "kind": "dirt_road"
    },
    {
      "from": "spawn_01",
      "to": "market_01",
      "kind": "dirt_road"
    }
  ],
  "objects": [
    {
      "type": "tree",
      "count": 80,
      "placement": "forest_edges"
    },
    {
      "type": "market_stall",
      "count": 6,
      "placement": "near:market_01"
    }
  ],
  "entities": [
    {
      "id": "spawn_01",
      "type": "player_spawn",
      "position": "bottom_center"
    },
    {
      "type": "villager",
      "count": 6,
      "placement": "near:market_01"
    }
  ],
  "constraints": {
    "walkable_spawn": true,
    "connect_key_regions": true,
    "no_blocked_doors": true,
    "objects_require_walkable_neighbor": true
  }
}
```

### 6.2 TilemapData

内部地图数据用于生成、校验、预览和导出。

结构示例：

```json
{
  "version": "0.1.0",
  "map": {
    "width": 64,
    "height": 64,
    "tile_width": 32,
    "tile_height": 32
  },
  "tileset": {
    "id": "default_rpg_32",
    "image": "tilesets/default_rpg_32.png",
    "tile_width": 32,
    "tile_height": 32,
    "columns": 16
  },
  "layers": {
    "terrain": [],
    "path": [],
    "building": [],
    "decoration": [],
    "collision": []
  },
  "objects": [],
  "events": [],
  "regions": []
}
```

层级说明：

- tile layer 使用一维数组保存，长度为 `width * height`。
- 空 tile 使用 `0`。
- tile id 与 Tiled gid 映射需要稳定。
- object 和 event 使用坐标加属性，不强行塞进 tile layer。

### 6.3 AssetCatalog

第一阶段不生成新素材，但需要有 tileset metadata。

示例：

```json
{
  "tileset_id": "default_rpg_32",
  "image": "tilesets/default_rpg_32.png",
  "tile_width": 32,
  "tile_height": 32,
  "columns": 16,
  "tiles": [
    {
      "tile_id": 1,
      "name": "grass",
      "tags": ["terrain", "grass", "walkable"],
      "walkable": true
    },
    {
      "tile_id": 2,
      "name": "water",
      "tags": ["terrain", "water", "blocking"],
      "walkable": false
    }
  ]
}
```

## 7. 地图生成设计

### 7.1 生成顺序

推荐生成顺序：

```text
1. 初始化基础地形
2. 放置大区域，例如河流、森林、村庄、地牢房间
3. 放置关键建筑和关键地点
4. 规划道路和桥梁
5. 放置装饰物
6. 放置交互对象
7. 放置实体和出生点
8. 生成碰撞层
9. 生成事件层
10. 执行校验和自动修复
```

这个顺序可以避免装饰物提前占位，导致道路和关键建筑无法放置。

### 7.2 区域放置

`position` 先支持枚举和相对位置：

- `top`
- `bottom`
- `left`
- `right`
- `center`
- `top_left`
- `top_right`
- `bottom_left`
- `bottom_right`
- `random`

区域大小：

- `small`
- `medium`
- `large`

生成器将位置和大小转换成候选矩形区域，再按优先级放置。

### 7.3 地形生成

第一阶段地形类型：

- `grass`
- `dirt`
- `forest_floor`
- `water`
- `snow`
- `sand`
- `stone_floor`
- `wall`

不同主题的默认地形：

| 主题 | 默认地形 | 主要装饰 | 关键区域 |
| --- | --- | --- | --- |
| forest_village | grass | tree、flower、rock | house、market、river |
| autumn_forest_village | grass/autumn_grass | autumn_tree、leaf、rock | market、temple、river |
| dungeon | stone_floor | torch、crate、bones | room、corridor、boss_room |
| snow_camp | snow | pine、snow_rock | cabin、campfire |
| desert_ruins | sand | cactus、ruin_wall | altar、ruins |

### 7.4 道路生成

道路负责连接关键区域。

第一阶段使用 A* 或简化路径规划：

- 节点：spawn、market、temple、house、boss_room 等关键区域中心点。
- 权重：优先走可行走地形，避开水、墙、建筑。
- 输出：`path` layer。
- 遇到水域时可以生成桥梁。

道路生成后必须更新碰撞层，确保道路可行走。

### 7.5 建筑生成

第一阶段建筑可以先用模板化布局，不生成复杂建筑外观。

建筑模板示例：

```text
house_small:
  size: 4x4
  door: bottom_center
  footprint: blocking
  entrance_neighbor: walkable

temple_small:
  size: 6x5
  door: bottom_center
  footprint: blocking
  entrance_neighbor: walkable
```

建筑生成规则：

- 建筑 footprint 内默认不可行走。
- 门口 tile 或门口相邻 tile 必须可行走。
- 建筑不能覆盖道路和水域，除非模板允许。
- 建筑之间保持至少 1 tile 间距。

### 7.6 装饰物生成

装饰物包括树、石头、花、摊位、路牌等。

放置规则：

- blocking object 不能放在道路上。
- blocking object 不能围死关键区域。
- decorative object 可以按概率分布放置。
- market stall 等语义对象必须靠近指定区域。
- 树和石头可以形成自然边界，但需要保留通行空间。

### 7.7 碰撞层生成

碰撞层由地形、建筑、对象共同决定。

默认不可行走：

- water
- wall
- cliff
- building footprint
- tree trunk
- large rock

默认可行走：

- grass
- dirt road
- bridge
- stone floor
- snow path
- sand path

碰撞层输出为 tile layer，也可以在 Tiled 中作为隐藏层。

### 7.8 对象层和事件层

对象层用于可交互对象：

- chest
- door
- sign
- portal
- harvest_node
- quest_marker

事件层用于逻辑触发：

- player_spawn
- area_transition
- cutscene_trigger
- battle_trigger
- npc_spawn_area

第一阶段至少支持：

- `player_spawn`
- `door`
- `chest`
- `npc_spawn`
- `area_marker`

## 8. Prompt Parser 设计

### 8.1 第一阶段方案

第一阶段 Prompt Parser 可以分两种实现：

1. 规则解析器：用于本地稳定测试。
2. LLM 解析器：用于真实自然语言输入。

建议接口统一：

```python
class PromptParser:
    def parse(self, request: GenerateRequest) -> RPGMapSpec:
        ...
```

这样可以在没有 LLM 的情况下先跑通工程闭环。

### 8.2 规则解析器

规则解析器用于 MVP 和自动化测试。

能力：

- 识别主题关键词。
- 识别区域关键词。
- 识别位置关键词。
- 识别对象数量。
- 补全默认 constraints。

示例关键词：

| 中文 | 英文/内部类型 |
| --- | --- |
| 森林 | forest |
| 村庄 | village |
| 河流 | river |
| 集市 | market |
| 神庙 | temple |
| 地牢 | dungeon |
| Boss 房 | boss_room |
| 雪地 | snow |
| 营地 | camp |

### 8.3 LLM 解析器

LLM 解析器只负责输出 `RPGMapSpec`，不直接输出 tile grid。

要求：

- 输出必须符合 JSON schema。
- 不允许自由生成未知字段。
- 缺少信息时使用默认值。
- 明显冲突时返回 `SPEC_ERROR`。

后续可以增加：

- 多轮澄清。
- spec 修复。
- prompt 模板版本管理。

## 9. 校验设计

### 9.1 ValidationReport

示例：

```json
{
  "passed": false,
  "errors": [
    {
      "code": "BLOCKED_DOOR",
      "severity": "error",
      "message": "temple_01 的入口被树阻挡",
      "position": [52, 12],
      "target": "temple_01"
    }
  ],
  "warnings": [
    {
      "code": "LOW_DECORATION_DENSITY",
      "severity": "warning",
      "message": "森林区域装饰密度偏低"
    }
  ],
  "metrics": {
    "walkable_ratio": 0.62,
    "reachable_key_regions": 3,
    "total_key_regions": 3
  }
}
```

### 9.2 必须校验项

必须通过：

- `SPAWN_WALKABLE`：出生点可行走。
- `KEY_REGIONS_REACHABLE`：关键区域可达。
- `NO_BLOCKED_DOORS`：门口无遮挡。
- `OBJECTS_PLACEABLE`：对象没有越界或重叠非法区域。
- `INTERACTABLE_REACHABLE`：交互对象相邻至少有一个可行走 tile。
- `TILED_EXPORT_VALID`：导出结构符合 Tiled JSON 基础要求。

### 9.3 建议校验项

建议检查但不强制失败：

- `WALKABLE_RATIO`：可行走区域比例合理。
- `DECORATION_DENSITY`：装饰密度合理。
- `REGION_BALANCE`：区域面积不过小或过大。
- `PATH_LENGTH`：关键路径不过度绕行。
- `EDGE_NATURALNESS`：地形边界不过于碎裂。

### 9.4 自动修复策略

可自动修复：

- 把 NPC 移动到最近可行走 tile。
- 删除堵门装饰物。
- 为水域路径补桥。
- 为不可达区域补道路。
- 降低装饰物密度。

不建议自动修复：

- 用户描述本身冲突。
- 地图尺寸过小导致关键区域无法放置。
- tileset 缺少必要 tile。

## 10. Tiled JSON 导出设计

### 10.1 图层映射

内部层到 Tiled 层映射：

| 内部层 | Tiled 类型 | 说明 |
| --- | --- | --- |
| terrain | tilelayer | 基础地形 |
| path | tilelayer | 道路、桥梁 |
| building | tilelayer | 建筑 tile |
| decoration | tilelayer | 装饰 tile |
| collision | tilelayer | 碰撞层，默认隐藏 |
| objects | objectgroup | 可交互对象 |
| events | objectgroup | 出生点、触发区、区域标记 |

### 10.2 坐标规则

- tile 坐标使用 `[x, y]`，左上角为 `[0, 0]`。
- Tiled object 坐标使用像素坐标。
- object 的像素坐标为 `tile_x * tile_width` 和 `tile_y * tile_height`。
- 对于角色出生点，锚点默认使用脚底中心。

### 10.3 自定义属性

Tiled object properties 示例：

```json
{
  "name": "spawn_01",
  "type": "player_spawn",
  "x": 1024,
  "y": 1888,
  "properties": [
    {"name": "direction", "type": "string", "value": "up"},
    {"name": "region", "type": "string", "value": "village"}
  ]
}
```

碰撞层属性：

```json
{
  "name": "collision",
  "type": "tilelayer",
  "visible": false,
  "properties": [
    {"name": "semantic", "type": "string", "value": "collision"}
  ]
}
```

## 11. 预览渲染设计

第一阶段使用 Pillow 渲染静态 PNG。

渲染顺序：

```text
terrain
path
building
decoration
objects
entities debug marker
events debug marker
```

调试渲染模式：

- 默认模式：只显示最终视觉层。
- Debug 模式：叠加碰撞、出生点、区域边界、路径连通线。

输出建议：

- `preview.png`：默认预览。
- `preview_debug.png`：可选调试预览。

第一阶段如果 tileset 未准备完整，可以先使用颜色块和文字标记作为 debug tileset，但验收版本需要替换为真实 tileset。

## 12. 建议目录结构

第一阶段建议目录：

```text
asset_general_system/
  docs/
    phase_1_tilemap_mvp_design.md
  specs/
    rpg_map_spec.schema.json
    tilemap_data.schema.json
    asset_catalog.schema.json
  generator/
    __init__.py
    cli.py
    config.py
    models/
      request.py
      rpg_map_spec.py
      tilemap_data.py
      reports.py
    parser/
      base.py
      rule_parser.py
      llm_parser.py
    map/
      generator.py
      terrain.py
      regions.py
      roads.py
      buildings.py
      decorations.py
      collisions.py
    validation/
      validator.py
      pathfinding.py
      rules.py
    render/
      preview_renderer.py
    export/
      tiled_exporter.py
    assets/
      catalog_loader.py
      default_rpg_32.json
      tilesets/
        default_rpg_32.png
  examples/
    prompts/
    specs/
    outputs/
  tests/
    test_rule_parser.py
    test_map_generator.py
    test_validator.py
    test_tiled_exporter.py
```

## 13. CLI 设计

### 13.1 generate 命令

```bash
python -m asset_general_system.generator.cli generate \
  --prompt "生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙" \
  --size 64x64 \
  --seed 20260605 \
  --output asset_general_system/examples/outputs/autumn_village
```

参数：

- `--prompt`：用户描述。
- `--prompt-file`：从文件读取描述。
- `--theme`：手动指定主题。
- `--size`：地图尺寸，例如 `64x64`。
- `--seed`：随机种子。
- `--tileset`：指定 tileset id。
- `--output`：输出目录。
- `--debug-preview`：是否输出 debug 预览图。

### 13.2 validate 命令

```bash
python -m asset_general_system.generator.cli validate \
  --map-data asset_general_system/examples/outputs/autumn_village/map_data.json
```

### 13.3 export-tiled 命令

```bash
python -m asset_general_system.generator.cli export-tiled \
  --map-data asset_general_system/examples/outputs/autumn_village/map_data.json \
  --output asset_general_system/examples/outputs/autumn_village/map.tiled.json
```

## 14. 测试设计

### 14.1 单元测试

覆盖：

- `RPGMapSpec` schema 校验。
- 中文 prompt 到 spec 的规则解析。
- 地形层生成。
- 区域放置。
- 道路连通。
- 碰撞层生成。
- Tiled JSON 结构导出。

### 14.2 集成测试

准备 5 个固定 demo prompt：

1. 秋季森林村庄。
2. 小型地下城。
3. 雪地营地。
4. 沙漠遗迹。
5. 海边渔村。

每个 demo 都需要检查：

- 生成不抛异常。
- 输出文件完整。
- `validation_report.passed == true`。
- `preview.png` 存在且尺寸正确。
- `map.tiled.json` 包含必要 layers 和 tilesets。

### 14.3 回归测试

对固定 seed 的 demo 保存快照：

- `map_spec.json`
- `map_data.json`
- `validation_report.json`

回归测试允许少量非关键随机差异，但关键指标必须稳定：

- 地图尺寸。
- 图层数量。
- 关键区域数量。
- 可达性。
- 出生点合法性。

## 15. 第一阶段里程碑

### 15.1 M1：协议和 CLI 骨架

交付：

- Pydantic 数据模型。
- CLI `generate` 命令。
- 示例 prompt。
- 空白地图输出。

验收：

- 命令可以运行。
- 可以生成基础输出目录。
- `map_spec.json` 和 `generation_report.json` 存在。

### 15.2 M2：规则 Parser 和基础地图生成

交付：

- 规则 parser。
- 主题识别。
- 基础地形生成。
- 区域放置。

验收：

- 森林村庄、地牢、雪地营地 3 类 prompt 能生成不同地图结构。

### 15.3 M3：道路、建筑、对象和碰撞

交付：

- 道路生成。
- 简单建筑模板。
- 装饰物放置。
- 碰撞层。

验收：

- 出生点和关键区域之间可达。
- 建筑入口无遮挡。
- 碰撞层正确标记水、墙、建筑、树。

### 15.4 M4：预览和 Tiled JSON 导出

交付：

- PNG 预览。
- debug 预览。
- Tiled JSON 导出。

验收：

- `preview.png` 可以正常查看。
- `map.tiled.json` 可以被 Tiled 打开。
- 图层结构符合设计。

### 15.5 M5：批量 demo 和验收

交付：

- 5 个 demo prompt。
- 5 套输出资产包。
- 自动化测试。
- 第一阶段总结文档。

验收：

- 5 个 demo 全部生成成功。
- 校验全部通过。
- 输出目录结构统一。

## 16. 验收标准

第一阶段完成时，必须满足：

- 支持至少 5 条中文 prompt 生成地图。
- 支持至少 3 类主题：森林村庄、地牢、雪地营地。
- 每次生成输出完整资产包。
- 地图尺寸支持默认 64x64。
- 预览 PNG 正常生成。
- Tiled JSON 能被 Tiled 打开。
- 出生点可行走。
- 关键区域可达。
- 建筑入口无遮挡。
- 碰撞层存在且有效。
- 生成报告记录 prompt、spec、seed、耗时和版本。

## 17. 主要风险和应对

### 17.1 Prompt 解析不稳定

应对：

- 第一阶段保留规则 parser。
- LLM parser 只作为可替换实现。
- 所有 parser 输出都必须过 schema 校验。

### 17.2 地图可玩性不足

应对：

- 可达性和碰撞校验作为硬门槛。
- 先保证结构合法，再逐步优化美观。
- 对关键区域使用模板和约束，而不是纯随机。

### 17.3 Tileset 不完整

应对：

- 第一阶段选择覆盖森林、村庄、地牢、雪地的固定 tileset。
- 缺失 tile 先用 debug tile 标记。
- 后续阶段再做素材生成和自动补全。

### 17.4 Tiled 导出兼容性

应对：

- 从最小 Tiled JSON 开始。
- 每个导出结果都用固定测试校验必要字段。
- 避免第一阶段使用复杂的 Tiled 特性。

## 18. 后续衔接

第一阶段完成后，后续阶段可以基于当前产物继续扩展：

- 阶段 2：增强校验、生成报告、Tiled 导出稳定性。
- 阶段 3：增加 Web 编辑器、局部重生成、锁定区域。
- 阶段 4：接入地图元素生成和素材库。
- 阶段 5：接入角色 sprite sheet。
- 阶段 6：接入特效动画帧。
- 阶段 7：导出到 Godot、Unity、Phaser。

第一阶段最重要的工程结果是稳定的 `RPGMapSpec`、`TilemapData` 和 Tiled JSON 输出。只要这三个协议稳定，后续所有能力都可以独立扩展。

