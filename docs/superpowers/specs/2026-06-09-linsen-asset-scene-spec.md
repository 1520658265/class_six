# linsen-asset-scene - 场景驱动素材生成 skill 规格书

**日期**：2026-06-09  
**状态**：待实施  
**负责人**：asset_general_system 项目组  
**关联 skill**：`.claude/skills/linsen-asset-scene/SKILL.md`（待创建）

---

## 1. 概述与目标

### 核心目标

将用户编写的 `scene.md` 自然中文场景描述，转换为一个可导入 Godot 的地图资产包：

- 逻辑地图：tilemap、regions、objects、events、collision
- 独立精灵：每个可见 object 对应一个透明 PNG
- Godot 输出：`final/scene.tscn` 打开后能看到 tilemap 和 object sprites

### 关键设计修正

旧方案的问题是 `RulePromptParser` 先用关键词决定地图对象，后续 LLM 只能修饰已识别出的对象，无法补回遗漏对象。新方案必须把 LLM 语义解析前置：

```text
scene.md
  -> ① spec：Claude 生成 map_spec.json
  -> ② map：Python 只做几何放置和逻辑地图导出
  -> ③-⑦ art pipeline：实体、prompt、图片、打包、Godot
```

因此，`RulePromptParser` 不再参与新流水线的场景解析，只作为 legacy CLI 能力保留。

### 非目标（v1 不做）

- 将全图 image layer 作为最终生产级背景方案；全图概念图只用于审美验证、布局参考或临时预览
- 通用 Godot tile atlas 自动编辑器；v1 只输出当前场景需要的 tileset 资源
- 多场景批处理
- 自动选择最佳 Gemini 变体
- 在 Godot 项目内创建完整玩法脚本

---

## 2. 优化后的 8 阶段流水线

### 阶段总览

1. **① spec（语义解析）**：Claude 读取 `scene.md`，生成 `map_spec.json`
2. **② map（地图生成）**：Python 读取 `map_spec.json`，生成 `map_data.json`、`art_request.json`、`preview.png`
3. **③ style（风格定义）**：Claude 生成 `style_profile.json`
4. **④ entities（实体编排）**：Claude 生成 `entities.json`，补充每个 object 的美术上下文
5. **⑤ prompts（提示生成）**：Claude 生成 `prompts.json`
6. **⑥ images（图像生成）**：Python 调 Gemini 生成 `images/{target_id}.png`
7. **⑦ pack（打包应用）**：Python 生成 `art_manifest.json`，写回 `sprite_path`，导出 `final/scene.tscn`
8. **⑧ status（进度查询）**：Python 输出当前阶段、完成项和错误日志

### 职责边界

Claude skill 负责：

- 场景语义理解
- 地图规格编写
- 风格推断
- 美术上下文整理
- prompt body 生成

Python 工具负责：

- schema 校验
- 几何放置
- 文件 I/O
- Gemini 调用
- PNG 命名和复制
- `sprite_path` 写回
- Godot `.tscn` 导出
- 进度和错误日志

---

## 3. 目录结构

单场景目录位于 `asset_general_system/scenes/{title}/`。

```text
asset_general_system/
└── scenes/
    └── dingbu_primary_school_1998/
        ├── scene.md
        ├── map_spec.json
        ├── map_data.json
        ├── art_request.json
        ├── preview.png
        ├── style_profile.json
        ├── entities.json
        ├── prompts.json
        ├── images/
        │   ├── ping_pong_table_01.png
        │   ├── ping_pong_table_01.json
        │   └── ...
        ├── art_manifest.json
        ├── progress.json
        ├── error.log
        └── final/
            ├── scene.tscn
            ├── map_data_applied.json
            ├── objects.json
            ├── tileset.tres
            └── sprites/
                ├── ping_pong_table_01.png
                └── ...
```

说明：

- v1 使用 JSON 作为机器契约格式，避免新增 YAML 解析依赖。
- `title` 建议使用 ASCII slug 作为目录名；中文标题保存在 `scene.md` 和 metadata 中。
- `images/` 保存原始生成图；`final/sprites/` 保存 Godot 包使用的拷贝。

---

## 4. 阶段详解

### ① spec：语义解析

输入：

- `scene.md`
- `asset_general_system/specs/rpg_map_spec.schema.json`
- skill 内置示例和约束

执行者：Claude skill

输出：`map_spec.json`

规则：

- `map_spec.json` 必须兼容现有 `RPGMapSpec` 模型。
- 场景中出现的关键 object 必须进入 `objects[]`。
- `properties` 必须保留美术上下文，供后续 `art_request` 和 `entities` 使用。

**Category 体系**：

`objects[].type` 不再代表具体物品，而是语义分类（placement category）。具体物品身份由 `label`、`properties.object_key` 和 `properties.display_name` 携带。

| category (type) | 含义 | 默认 footprint | 默认 blocking | 放置策略 |
|---|---|---|---|---|
| `building` | 大型建筑 | (8, 5) | true | 沿边界，不重叠 |
| `large_prop` | 大件设施（球台、花坛、石磨） | (2, 1) | true | zone 内随机 |
| `small_prop` | 小件装饰（花盆、水桶、粉笔盒） | (1, 1) | false | 靠近建筑或路径 |
| `thin_prop` | 瘦高物件（旗杆、电杆、路灯） | (1, 2) | true | 单点放置 |
| `npc` | 活动人物 / 动物 | (1, 1) | false | 路径或区域内 |
| `facade_overlay` | 墙面附着物（标语、海报） | (3, 1) | false | 贴建筑正面，要求 `attached_to` |
| `text_sign` | 文字牌匾（招牌、通知栏） | (2, 1) | false | 建筑正面，要求 `attached_to` |

**Facing 与 footprint 的关系**：

`properties.facing` 影响默认 footprint 的长宽方向：

| facing 值 | 含义 | 对默认 footprint 的影响 |
|---|---|---|
| `east_west` | 长边水平 | 默认 footprint 横向为长边，如 (3, 2) |
| `north_south` | 长边纵向 | 默认 footprint 旋转，如 (2, 3) |
| `faces_south` | 正面朝下 | 不旋转（建筑、牌匾默认） |
| `faces_player` | 正面朝玩家 | 不影响 footprint，影响 prompt 视角 |

对 prompt 生成的影响：
- `east_west` → "侧面可见，长边水平方向"
- `north_south` → "纵深方向，长边垂直"
- `faces_south` → "正面朝观察者（俯视角玩家视角）"

**LLM 输出要求**：

- `objects[].type` 必须是上述 7 种 category 之一。
- `label` 和 `properties.display_name` 描述具体物品。
- `properties.object_key` 必填，使用稳定 ASCII snake_case，作为 target_id、文件名、manifest 和 prompt 查找的物品身份基础。
- `properties.source_clause` 保留原始描述来源。
- `properties.facing` 推荐写，缺失时根据 category 默认（building/facade_overlay/text_sign → faces_south，其余 → east_west）。
- `properties.footprint` 可选写，格式 `"WxH"`；如显式指定则覆盖 category 默认值 + facing 推导。
- `properties.blocking` 可选写，显式值覆盖 category 默认。
- `properties.source_canvas` 可选写，格式 `[W, H]`，表示图像生成源画布像素尺寸，不影响地图占格、碰撞或放置。
- `facade_overlay` 和 `text_sign` 必须写 `properties.attached_to`，指向已有 `regions[].id` 或可确定生成的 object id。
- `text_sign` 可用 `properties.text` 保存实际文字内容，但生成 PNG 时不得把可读文字、汉字或字母烘焙进图像；文字由 Godot 文本层或后续 UI 层渲染。
- `properties.footprint` 格式非法时校验失败，不允许静默降级。

**Footprint 优先级链**：
1. `properties.footprint`（LLM 显式指定）
2. category 默认值 + facing 旋转
3. 最终 fallback：`(1, 1)`

**Placement 优先级链**：
1. `objects[].placement`（显式 zone 指定）
2. `properties.placement`
3. category 对应的默认策略

**source_canvas 与 footprint 的边界**：

- `footprint` 只描述地图瓦片占用、碰撞和放置空间。
- `source_canvas` 只描述单个素材 PNG 的生成画布，单位为像素。
- `source_canvas` 解析顺序：
  1. `properties.source_canvas`（显式 `[W, H]`）
  2. 根据最终 footprint 推导为 `[footprint_w * tile_width, footprint_h * tile_height]`，再应用 category 最小值
  3. 最终 fallback：`[64, 64]`
- category 最小源画布建议值：`building` `[256, 160]`，`large_prop` `[96, 64]`，`small_prop` `[64, 64]`，`thin_prop` `[64, 96]`，`npc` `[64, 64]`，`facade_overlay` `[96, 64]`，`text_sign` `[96, 64]`。

**attached_to 解析边界**：

- 推荐优先引用 `regions[].id`，例如 `school_01`。
- 如需引用 object id，必须使用由 `properties.object_key` 和实例序号确定生成的 id，例如 `gate_01`；对 `count > 1` 的目标不允许只写 `object_key`。
- `scene-validate --stage spec` 只能做语法校验、region id 校验和可确定 object id 预校验；`scene-map-build` 后必须再做一次解析校验，确认 `attached_to` 最终指向真实 region 或 object。

示例：

```json
{
  "version": "1.0.0",
  "id": "dingbu_primary_school_1998",
  "title": "鼎埠县中心小学操场 1998",
  "theme": "school_campus",
  "map": {
    "width": 64,
    "height": 64,
    "tile_width": 32,
    "tile_height": 32,
    "orientation": "orthogonal"
  },
  "regions": [
    {
      "id": "school_01",
      "type": "school",
      "position": "top",
      "size": "large",
      "priority": 95
    },
    {
      "id": "playground_01",
      "type": "playground",
      "position": "center",
      "size": "large",
      "priority": 90
    }
  ],
  "paths": [
    {
      "from": "school_01",
      "to": "playground_01",
      "kind": "dirt_road"
    }
  ],
  "objects": [
    {
      "type": "large_prop",
      "count": 2,
      "placement": "playground",
      "label": "水泥乒乓球台",
      "properties": {
        "object_key": "ping_pong_table",
        "display_name": "水泥乒乓球台",
        "source_clause": "操场东侧有两张水泥乒乓球台",
        "facing": "east_west",
        "footprint": "3x2",
        "source_canvas": [128, 96],
        "material": "weathered concrete",
        "appearance": "faded green painted edge, cracked tabletop",
        "blocking": true
      }
    },
    {
      "type": "text_sign",
      "count": 1,
      "placement": "school_front",
      "label": "木质通知栏",
      "properties": {
        "object_key": "notice_board",
        "display_name": "木质通知栏",
        "source_clause": "教学楼门口有一块旧木质通知栏",
        "facing": "faces_south",
        "footprint": "2x1",
        "source_canvas": [96, 64],
        "attached_to": "school_01",
        "text": "通知",
        "blocking": false,
        "material": "weathered wood",
        "appearance": "faded red frame, blank paper notices without readable text"
      }
    },
    {
      "type": "thin_prop",
      "count": 2,
      "placement": "playground",
      "label": "铁篮球架",
      "properties": {
        "object_key": "basketball_hoop",
        "display_name": "铁篮球架",
        "source_clause": "操场北侧有两个生锈的铁篮球架",
        "facing": "faces_south",
        "footprint": "1x2",
        "source_canvas": [64, 96],
        "blocking": true,
        "material": "rusted steel",
        "appearance": "rusted frame, wooden backboard"
      }
    }
  ],
  "entities": [],
  "constraints": {
    "walkable_spawn": true,
    "connect_key_regions": true,
    "no_blocked_doors": true,
    "objects_require_walkable_neighbor": true
  },
  "seed": 20260609,
  "tileset_id": "default_rpg_32"
}
```

验证：

- Python 读取 `map_spec.json`，用 `RPGMapSpec` Pydantic 模型校验。
- 校验失败时停止流水线，不进入 ② map。

#### 背景 tile family 设计

背景不应以“单张孤立 tile”为生成单位。任何会在地图上相邻出现的地面、道路、跑道、广场、水面、边缘或过渡块，都必须先归入同一个 tile family，再通过一次 sprite sheet 生成并按固定 slot 切片。

`base_terrain` 只表示主背景材质语义，例如麦田、草地、砖石广场；它不再等价于“只生成一张可无限平铺的小图”。真正的生产级背景应由 `tile_groups` 描述：

- `material_group`：同一种材质或表面，例如 wheat_field、grass_lawn、brick_plaza、asphalt_road、rubber_track。成员包含 center、center_variant、edge、corner、decor_variant 等。
- `transition_group`：两种材质的边界，例如 grass_to_brick、wheat_to_road、track_to_grass。成员包含四向边缘、内角、外角，以及必要的连接块。

道路、十字路、环形跑道这类 composite 仍然需要拆成 `parts[]` 和 `layout[]`，但这些 part 的美术生成应优先落入对应 tile family。例如十字道路至少需要无边缘中心块和上下左右四种边缘；环形跑道至少需要跑道中心/直道/边缘/四角弧形块，具体成员由布局需要决定。

tile family 的生成契约：

- 同一 family 必须一次生成为一张 sprite sheet，不允许把相邻 tile 分别单独生成。
- sheet 使用固定 64x64 slot；slot 内必须填满不透明地表像素，不能像物体图标一样留透明边。
- 同一 family 内共享调色板、光照方向、纹理密度、像素密度、描边强度和材质颗粒尺度。
- center、edge、corner、transition 之间必须能无缝衔接，边缘纹理要延续到相邻 slot。
- 不允许可见网格线、边框、标签、文字、sprite sheet 分隔线或 UI 装饰。
- 如果概念图上某个区域整体效果很好，可以作为审美参考或临时整图背景，但最终可扩展 tilemap 仍应回到 tile family 生成和拼接。

示例结构（已进入 schema 和 Python 生成流程）：

```json
{
  "tile_groups": [
    {
      "group_id": "brick_plaza",
      "kind": "material_group",
      "generation_mode": "sprite_sheet",
      "tile_size": [64, 64],
      "members": [
        {"tile_id": "brick_center", "role": "center"},
        {"tile_id": "brick_variant_01", "role": "center_variant"},
        {"tile_id": "brick_edge_top", "role": "edge_top"},
        {"tile_id": "brick_edge_bottom", "role": "edge_bottom"},
        {"tile_id": "brick_edge_left", "role": "edge_left"},
        {"tile_id": "brick_edge_right", "role": "edge_right"},
        {"tile_id": "brick_corner_tl", "role": "corner_top_left"},
        {"tile_id": "brick_corner_tr", "role": "corner_top_right"},
        {"tile_id": "brick_corner_bl", "role": "corner_bottom_left"},
        {"tile_id": "brick_corner_br", "role": "corner_bottom_right"}
      ]
    },
    {
      "group_id": "grass_to_brick_transition",
      "kind": "transition_group",
      "from": "grass_lawn",
      "to": "brick_plaza",
      "generation_mode": "sprite_sheet",
      "tile_size": [64, 64],
      "members": [
        {"tile_id": "grass_brick_edge_top", "role": "edge_top"},
        {"tile_id": "grass_brick_edge_bottom", "role": "edge_bottom"},
        {"tile_id": "grass_brick_edge_left", "role": "edge_left"},
        {"tile_id": "grass_brick_edge_right", "role": "edge_right"}
      ]
    }
  ]
}
```

### ② map：地图生成

输入：

- `map_spec.json`

执行者：Python

命令：

```powershell
python generate.py scene-map-build asset_general_system/scenes/dingbu_primary_school_1998
```

输出：

- `map_data.json`
- `art_request.json`
- `preview.png`
- `progress.json`

实现要求：

- 新增 `scene-map-build` 子命令，读取场景目录下的 `map_spec.json`。
- 复用 `MapGenerator.generate(RPGMapSpec)`。
- 不调用 `RulePromptParser.parse()`。
- 继续复用 `build_map_art_request()`。
- `build_map_art_request()` 的 `category` 字段直接取 `map_spec.objects[].type`，不调用 `infer_map_art_category()`。
- `art_request.objects[].id` 是后续 `target_id` 的唯一来源。
- `art_request.objects[].anchor` 由 Python 根据 category 确定性推导（building/thin_prop → bottom_center，其余 → center），不依赖 Claude 生成。
- `properties.footprint` 的字符串格式 `"WxH"` 仅在 `map_spec.json`（LLM 输入端）使用；Python 解析后全部转为 `[W, H]` 整数数组，后续所有文件（`art_request`、`entities`、`art_manifest`）统一使用数组格式。
- `properties.source_canvas` 在 `map_spec.json` 中使用 `[W, H]` 整数数组；Python 校验后透传到 `art_request.objects[].source_canvas`，后续 `entities`、`prompts`、`images`、`art_manifest` 均使用数组格式。
- `properties.source_canvas` 不参与 footprint、blocking、collision 或 placement 计算，只影响图像生成画布和提示词技术约束。
- `facade_overlay` / `text_sign` 的放置必须读取 `properties.attached_to`，优先贴附到目标 object 或 region 的正面锚点；不能退化为普通随机放置。
- 重构 `MapGenerator` 的 object 放置逻辑为 category-based placement：
  - 废弃 `SCHOOL_OBJECT_META` 作为放置入口。
  - 每个 category 对应一个 PlacementStrategy（`BuildingPlacer`、`LargePropPlacer`、`SmallPropPlacer`、`ThinPropPlacer`、`NpcPlacer`、`FacadeOverlayPlacer`、`TextSignPlacer`）。
  - PlacementStrategy 读取 object 的最终 footprint（按优先级链解析）和 placement zone。
  - `properties.facing` 影响默认 footprint 旋转：facing 为 `north_south` 时交换 W 和 H。
  - 最终 footprint 解析顺序：`properties.footprint`（显式）→ category 默认 + facing 旋转 → `(1, 1)`。
  - 最终 blocking 解析顺序：`properties.blocking`（显式）→ category 默认。
  - 最终 placement 解析顺序：`objects[].placement` → `properties.placement` → category 默认策略。
  - `FacadeOverlayPlacer` 和 `TextSignPlacer` 必须基于 `attached_to` 计算贴附位置，并保证贴附物不阻断目标建筑入口。
- `ObjectData.id` / `art_request.objects[].id` 生成规则：
  - 优先使用 `properties.object_key` 作为 ID 前缀。
  - 同一 object_key 多实例按 `{object_key}_{index:02d}` 生成，例如 `ping_pong_table_01`。
  - 如果缺失 object_key，`scene-validate` 报错，不能从中文 display_name 临时 slug。
- `SCHOOL_OBJECT_META` 可保留为 legacy 兼容层（旧 `--type map` CLI 仍可用），但新流水线不依赖它。
- 校验层：
  - `objects[].type` 不在 7 种 category 内 → 报错，不静默降级。
  - `properties.footprint` 格式非法 → 报错。
  - `properties.source_canvas` 如存在，必须是 `[W, H]` 正整数数组；格式非法 → 报错。
  - `facade_overlay` / `text_sign` 缺少 `properties.attached_to` → 报错。
  - `properties.attached_to` 既不对应已有 `regions[].id`，也无法在 map-build 后解析到已生成 object id → 报错。
  - `text_sign` 的 prompt/image 生成不得请求可读文字；`properties.text` 只作为 Godot 文本层或 metadata 使用。
  - placement zone 不对应已有 region 且不是通用策略名（`random_walkable`、`near_path`）→ 报 warning。
- `scene-validate` 必须在 map-build 前检查：
  - `objects[].type` 必须是 7 种 category 之一，否则报错。
  - `properties.footprint` 格式只允许 `"WxH"`（W/H 为正整数），格式错误报错。
  - `properties.source_canvas` 如存在，格式只允许 `[W, H]`（W/H 为正整数），格式错误报错。
  - `properties.facing` 如存在，必须是 `east_west`/`north_south`/`faces_south`/`faces_player` 之一。
  - `facade_overlay` / `text_sign` 必须包含 `properties.attached_to`。
  - 每个 object 必须包含 `label` 或 `properties.display_name`，否则报错。
  - 每个 object 必须包含 `properties.object_key`，且格式为 ASCII snake_case。
  - 推荐包含 `properties.source_clause`，缺失时报 warning。

### ③ style：风格定义

输入：

- `scene.md`
- `asset_general_system/style_defaults.json`
- `map_spec.json`

执行者：Claude skill

输出：`style_profile.json`

示例：

```json
{
  "version": "1.0",
  "inherits": "../../style_defaults.json",
  "view": "top_down_3_4",
  "art_style": "pixel_art_32",
  "palette_mood": "dingbu_county_90s",
  "lighting": "midday_bright",
  "weather_tags": ["clear_sky"],
  "era_tags": ["late_1990s", "rural_china_county", "school_campus"],
  "atmosphere": "nostalgic",
  "forbidden": ["text_in_image", "watermark", "white_background", "scene_background"]
}
```

### ④ entities：实体编排

输入：

- `art_request.json`
- `map_spec.json`
- `style_profile.json`
- `scene.md`

执行者：Claude skill

输出：`entities.json`

设计：

- 使用 flat list，避免按 region 分组导致 target 查找复杂。
- 每个 entity 必须有 `target_id`，且等于 `art_request.objects[].id`。
- 不允许新增不存在于 `art_request.objects` 的 `target_id`。
- 如需新增实体，必须回到 ① spec 修改 `map_spec.json` 并重跑 ② map。
- `anchor` 不由 Claude 写入 entities.json；anchor 由 Python 在 `art_request` 和 `art_manifest` 中确定性生成（category → anchor 规则）。
- `footprint` 和 `category` 从 `art_request.objects[]` 透传，Claude 可读不可改。
- `object_key`、`source_canvas`、`attached_to` 从 `art_request.objects[]` 或 `map_spec.objects[].properties` 透传，Claude 可读不可改。
- `text_sign` 的 `text` 字段可以进入 `entities.json`，但只表示后续文字层内容，不表示 PNG 内应生成可读文字。

示例：

```json
{
  "version": "1.0",
  "scene": "鼎埠县中心小学操场 1998",
  "entities": [
    {
      "target_id": "ping_pong_table_01",
      "object_key": "ping_pong_table",
      "display_name": "水泥乒乓球台",
      "category": "large_prop",
      "region_id": "playground_01",
      "footprint": [3, 2],
      "source_canvas": [128, 96],
      "facing": "east_west",
      "context": "操场东侧，水泥材质，绿色边框褪色，台面有裂纹和灰尘。长边水平放置。",
      "source_clause": "操场东侧有两张水泥乒乓球台",
      "style_tags": ["weathered_concrete", "faded_green_paint"]
    },
    {
      "target_id": "notice_board_01",
      "object_key": "notice_board",
      "display_name": "木质通知栏",
      "category": "text_sign",
      "region_id": "school_01",
      "footprint": [2, 1],
      "source_canvas": [96, 64],
      "attached_to": "school_01",
      "text": "通知",
      "facing": "faces_south",
      "context": "教学楼门口的旧木质通知栏，红色边框褪色，纸张泛黄但图像素材本身不包含可读文字。",
      "source_clause": "教学楼门口有一块旧木质通知栏",
      "style_tags": ["weathered_wood", "blank_notice_papers"]
    }
  ]
}
```

### ⑤ prompts：提示生成

输入：

- `entities.json`
- `style_profile.json`
- `art_request.json`

执行者：Claude skill

输出：`prompts.json`

规则：

- 每个 `target_id` 生成一个 prompt。
- prompt body 描述 object 本体，不生成完整场景。
- Claude 在 body 中自然描述朝向语义（如"正面朝向观察者"、"侧面展示，长边水平"），但不写尺寸数字和锚点公式。
- `text_sign` 的 prompt 必须描述空白牌面、空白纸张或无字表面；不得要求生成可读文字、汉字、字母、标语内容或手写文字。
- 技术约束由 Python wrapper 追加，包括：`source_canvas` 尺寸、pixel grid、anchor 坐标、`Orientation: horizontal/vertical`。

示例：

```json
{
  "version": "1.0",
  "prompts": [
    {
      "target_id": "ping_pong_table_01",
      "body": "1998 年县城小学操场里的水泥乒乓球台，绿色边框已经褪色，台面有细裂纹和灰尘，整体厚重结实，适合 32px tile 网格的 RPG 地图物件。",
      "emphasis": ["weathered_concrete", "faded_green_paint", "school_playground"],
      "negative": ["text", "watermark", "background", "photorealistic"]
    },
    {
      "target_id": "notice_board_01",
      "body": "1998 年县城小学教学楼门口的旧木质通知栏，褪色红色木框，几张泛黄空白纸贴在板面上，没有任何可读文字，适合 RPG 地图正面贴附物件。",
      "emphasis": ["weathered_wood", "blank_notice_papers", "school_facade"],
      "negative": ["readable text", "Chinese characters", "letters", "watermark", "background", "photorealistic"]
    }
  ]
}
```

### ⑥ images：图像生成

输入：

- `prompts.json`
- `entities.json`
- `art_request.json`
- `style_profile.json`

执行者：Python

命令：

```powershell
python generate.py scene-images asset_general_system/scenes/dingbu_primary_school_1998 --gemini
python generate.py scene-images asset_general_system/scenes/dingbu_primary_school_1998 --target ping_pong_table_01 --force
```

输出：

- `images/{target_id}.png`
- `images/{target_id}.json`
- `progress.json`

实现要求：

- 复用 `ObjectGenerator._build_prompt()` 的技术约束能力。
- `ObjectGenerator` 当前默认按 `object_type + seed/timestamp` 命名；`scene-images` 必须新增目标命名机制，确保最终文件名为 `{target_id}.png` 和 `{target_id}.json`。
- `source_canvas` 是图像生成画布尺寸来源；`footprint` 只用于运行时占格和放置，不直接等价于 PNG 尺寸。
- 支持 `--target TARGET_ID` 单目标生成 / 重生；指定 `--target` 时只处理该 target，配合 `--force` 覆盖已有 PNG。
- 已存在的 PNG 默认跳过；`--force` 时重新生成。
- 失败单项写入 `progress.json.errors[]` 和 `error.log`，不吞掉错误。

### ⑦ pack：打包应用

输入：

- `images/`
- `entities.json`
- `art_request.json`
- `map_data.json`

执行者：Python

命令：

```powershell
python generate.py scene-pack asset_general_system/scenes/dingbu_primary_school_1998
```

输出：

- `art_manifest.json`
- `final/map_data_applied.json`
- `final/scene.tscn`
- `final/objects.json`
- `final/sprites/*.png`

实现要求：

- `art_manifest.json` 由 Python 确定性生成，不由 Claude 手写。
- 对每个 mapping：
  - 查找 `map_data.objects[].id == target_id`
  - 设置顶层字段 `object.sprite_ref = target_id`
  - 设置顶层字段 `object.sprite_path = "sprites/{target_id}.png"`
  - 不写入 `object.properties["sprite_path"]` 作为主字段
- 拷贝 `images/{target_id}.png` 到 `final/sprites/{target_id}.png`。
- 导出 Godot 时必须生成可见 `Sprite2D`，不能只写 metadata。
- `text_sign` 如存在 `properties.text` / `entities[].text`，`scene-pack` 必须单独生成 Godot `Label`、`LabelSettings` 或等价文本 metadata；文字不得依赖 PNG 内烘焙。

Godot 导出要求：

- `scene.tscn` 包含 tilemap 节点。
- 每个有 `sprite_path` 的 object 生成一个 `Sprite2D` 节点或 `Node2D + Sprite2D` 子节点。
- `text_sign` 的可读文字使用独立文本节点叠加到对应 `Sprite2D` 上方，并继承 `attached_to` / object transform。
- PNG 作为 `Texture2D` ext_resource 写入 `.tscn`。
- object 位置、尺寸、anchor 必须与 `footprint` 和 `tile_size` 对齐。
- 建议渲染层级：tilemap → buildings → props → facade_overlay/text_sign sprites → npcs → text labels。
- 如果资源路径需要 Godot `res://` 前缀，`scene-pack` 提供 `--resource-base res://maps/{scene_slug}` 参数，默认使用相对包路径。

### ⑧ status：进度查询

输入：

- `progress.json`
- `error.log`

执行者：Python

命令：

```powershell
python generate.py scene-status asset_general_system/scenes/dingbu_primary_school_1998
```

输出示例：

```text
Scene: dingbu_primary_school_1998
Current Stage: 6_images
Progress: 10/12 generated

Completed:
  - 1_spec
  - 2_map
  - 3_style
  - 4_entities
  - 5_prompts

In Progress:
  - 6_images

Errors:
  - basketball_hoop_01: Gemini timeout, retry 2/3
```

---

## 5. 数据契约

### 5.1 art_request.json

生成者：`scene-map-build`

消费者：

- ④ entities
- ⑤ prompts
- ⑥ images
- ⑦ pack

要求：

- `objects[].id` 必须唯一。
- `objects[].category`、`footprint`、`runtime_size`、`anchor`、`source_canvas` 必须存在。
- `objects[].category` 直接透传自 `map_spec.objects[].type`，不走推断逻辑。
- `objects[].properties` 应保留 `map_spec.objects[].properties` 中的美术上下文。
- `objects[].source_canvas` 使用 `[W, H]` 整数数组，来自 `properties.source_canvas` 或 Python 默认推导。
- `facade_overlay` / `text_sign` 必须保留 `properties.attached_to`，供贴附放置、prompt 和 Godot 导出使用。
- `text_sign` 可保留 `properties.text`，但该字段只表示文本层内容，不表示 PNG 内已有文字。

### 5.2 art_manifest.json

生成者：`scene-pack`

示例：

```json
{
  "version": "1.0",
  "scene": "dingbu_primary_school_1998",
  "generated_at": "2026-06-09T14:32:10Z",
  "mappings": [
    {
      "target_id": "ping_pong_table_01",
      "sprite_path": "images/ping_pong_table_01.png",
      "final_sprite_path": "sprites/ping_pong_table_01.png",
      "footprint": [3, 2],
      "anchor": "center",
      "category": "large_prop",
      "status": "generated"
    }
  ],
  "metadata": {
    "total_objects": 12,
    "generated_count": 12,
    "failed_count": 0
  }
}
```

### 5.3 progress.json

生成者：所有 Python 子命令

示例：

```json
{
  "current_stage": "6_images",
  "completed": ["1_spec", "2_map", "3_style", "4_entities", "5_prompts"],
  "in_progress": {
    "stage": "6_images",
    "total": 12,
    "completed": 8,
    "failed": 0,
    "current_item": "basketball_hoop_01"
  },
  "last_updated": "2026-06-09T14:32:10Z",
  "errors": []
}
```

---

## 6. 新增 schema

新增文件：

1. `asset_general_system/specs/scene_map_spec.schema.json`
2. `asset_general_system/specs/scene_style_profile.schema.json`
3. `asset_general_system/specs/scene_entities.schema.json`
4. `asset_general_system/specs/scene_prompts.schema.json`
5. `asset_general_system/specs/art_manifest.schema.json`
6. `asset_general_system/specs/progress.schema.json`

复用文件：

- `asset_general_system/specs/rpg_map_spec.schema.json`
- `asset_general_system/specs/tilemap_data.schema.json`

说明：

- `scene_map_spec.schema.json` 在 `rpg_map_spec.schema.json` 基础上叠加 scene 流水线约束：7 种 category enum、必填 `properties.object_key`、`properties.source_canvas` 格式、`facade_overlay` / `text_sign` 的 `properties.attached_to` 要求、`text_sign.properties.text` 的 metadata 语义。
- `scene_map_spec.schema.json` 已新增 `tile_groups[]` 约束，用于描述生产级背景 tile family。`tile_groups[].kind` 只允许 `material_group` 或 `transition_group`，`generation_mode` 固定为 `sprite_sheet`，`tile_size` 默认 `[64, 64]`，`members[].role` 必须使用稳定枚举，例如 `center`、`center_variant`、`edge_top`、`edge_bottom`、`edge_left`、`edge_right`、`corner_top_left`、`corner_top_right`、`corner_bottom_left`、`corner_bottom_right`、`transition_*`。
- `rpg_map_spec.schema.json` 继续作为底层地图结构契约，不承载 scene 专属素材生成规则。

校验策略：

- Claude 生成的 JSON 文件必须立即 schema 校验。
- Python 生成的 JSON 文件也必须在写出后校验。
- `target_id` 完整性不能只靠 JSON schema，需要额外做跨文件校验：
  - `entities.target_id` 必须等于某个 `art_request.objects.id`
  - `prompts.target_id` 必须等于某个 `entities.target_id`
  - `art_manifest.mappings.target_id` 必须等于某个 `entities.target_id`
  - `attached_to` 必须等于某个 `regions[].id` 或已生成 object id

---

## 7. Python 子命令

### 7.1 新增命令

```text
python generate.py scene-map-build <scene_dir> [--force]
python generate.py scene-background-assets <scene_dir> [--gemini] [--force]
python generate.py scene-images <scene_dir> [--gemini] [--force] [--variants N] [--target TARGET_ID]
python generate.py scene-pack <scene_dir> [--force] [--resource-base RES_PATH]
python generate.py scene-status <scene_dir>
python generate.py scene-validate <scene_dir> [--stage STAGE]
```

### 7.2 现有代码复用

保留并复用：

- `MapGenerator.generate()`
- `build_map_art_request()`
- `ObjectGenerator`
- `GeminiImageGenerator`
- `PreviewRenderer`
- `GodotExporter`
- Pydantic models under `generator.models`

### 7.3 legacy 代码处理

保留但不用于新流水线：

- `RulePromptParser`
- `generate.py --type map`
- `infer_map_object_additions()`

删除策略：

- v1 完成前不删除 legacy 代码。
- 新流水线端到端稳定后，再单独提交清理变更。

---

## 8. SKILL.md 设计

路径：`.claude/skills/linsen-asset-scene/SKILL.md`

Frontmatter：

```yaml
---
name: linsen-asset-scene
description: 场景驱动素材生成：scene.md -> Godot tilemap + sprites
arguments:
  - name: title
    description: 场景目录名
    required: true
  - name: stage
    description: spec/map/style/entities/prompts/images/pack/status/all
    required: false
    default: all
  - name: review-all
    description: 每个 Claude 阶段输出后等待用户复核
    flag: true
  - name: force
    description: 覆盖已存在输出
    flag: true
  - name: variants
    description: images 阶段每个实体生成多个变体
    type: integer
    default: 1
---
```

命令示例：

```text
/linsen-asset-scene dingbu_primary_school_1998
/linsen-asset-scene dingbu_primary_school_1998 --stage spec
/linsen-asset-scene dingbu_primary_school_1998 --stage images --force
/linsen-asset-scene dingbu_primary_school_1998 --stage status
```

skill 状态机：

1. 检查 `scene_dir` 和 `scene.md`
2. 对当前阶段检查前置文件
3. Claude 阶段写 JSON 后调用 `scene-validate`
4. Python 阶段调用对应子命令
5. 更新或读取 `progress.json`
6. 如启用 `--review-all`，在 ① 输出后、③ 输出后、④ 输出后、⑤ 输出后暂停等待用户确认，再进入下一阶段。

---

## 9. 实施计划

### Phase 1：契约和验证

任务：

1. 新增 6 个 schema
2. 新增 `style_defaults.json`
3. 新增 `scene-validate`
4. 创建 skill 骨架

验收：

- `python generate.py scene-validate <scene_dir> --stage spec` 能校验 `map_spec.json`
- `scene_map_spec.schema.json` 能校验 category enum、`object_key`、`source_canvas`、`attached_to` 等 scene 专属字段
- schema 错误能定位到字段路径

### Phase 2：LLM spec 前置

任务：

1. skill 读取 `scene.md` 生成 `map_spec.json`
2. map spec 使用现有 `RPGMapSpec` 字段
3. object 上下文写入 `objects[].properties`

验收：

- 不依赖 `RulePromptParser`
- 用户描述中的关键 object 进入 `map_spec.objects[]`

### Phase 3：scene-map-build

任务：

1. 新增 `scene-map-build`
2. 读取 `map_spec.json`
3. 重构 `MapGenerator` 新流水线入口为 category-based placement
4. 新增 7 类 PlacementStrategy：building / large_prop / small_prop / thin_prop / npc / facade_overlay / text_sign
5. 实现 `properties.object_key` 驱动的稳定 `ObjectData.id` 生成
6. 解析 `properties.footprint`、`properties.blocking`、`properties.facing`、`properties.source_canvas`、`properties.attached_to`、placement zone
7. 实现 `facade_overlay` / `text_sign` 基于 `attached_to` 的贴附放置
8. 保留 legacy `RulePromptParser` / `SCHOOL_OBJECT_META` 路径的兼容测试
9. 输出 `map_data.json`、`art_request.json`、`preview.png`

验收：

- `art_request.objects[].id` 唯一
- `art_request.objects[].id` 使用 `object_key` 前缀
- 7 种 category 都至少有一个单元测试覆盖
- `facade_overlay` / `text_sign` 缺少或错误 `attached_to` 时校验失败
- legacy `generate.py --type map` 仍可运行或明确标记为 legacy only
- `preview.png` 可打开
- `progress.json` 更新到 `2_map`

### Phase 4：style/entities/prompts

任务：

1. skill 生成 `style_profile.json`
2. skill 生成 `entities.json`
3. skill 生成 `prompts.json`
4. 每步调用 `scene-validate`

验收：

- `target_id` 跨文件完整性校验通过
- `text_sign` prompt 不包含可读文字生成要求
- prompt 不包含完整场景背景要求

### Phase 5：background tile families

任务：

1. 从 `base_terrain`、`composites[]` 和 reviewed `background_plan.json` 汇总生产级 `tile_groups[]`
2. 为每个 `material_group` / `transition_group` 生成一张 sprite sheet prompt
3. Gemini 一次生成整组 tile sheet，保证同组 tile 的材质、尺度、光照、边缘连续性一致
4. 按固定 64x64 slot 切片到 `background_tiles/{tile_id}.png`
5. 记录 sheet 原图、slot manifest 和每个 tile 的来源，供 review 和 pack 追踪

验收：

- 不再为相邻地表 tile 分别孤立生成图片
- 同一材质或过渡 family 至少有 center / edge / corner 或布局所需等价角色
- 切片后的 tile 尺寸固定为 64x64
- `scene-pack` 能优先使用 `background_tiles/{tile_id}.png` 组装最终预览

### Phase 6：images

任务：

1. 新增 `scene-images`
2. Gemini 生成 PNG
3. 强制输出命名为 `{target_id}.png`
4. 使用 `source_canvas` 作为图像生成画布尺寸
5. 支持 `--target TARGET_ID` 单目标重生
6. 记录每张图的参数 JSON

验收：

- 缺失图片可断点续跑
- 指定 `--target` 时只重生一个素材
- 失败项写入 `error.log`

### Phase 7：pack + Godot sprites

任务：

1. 新增 `scene-pack`
2. Python 生成 `art_manifest.json`
3. 写回 `ObjectData.sprite_ref` 和 `ObjectData.sprite_path`
4. 扩展 `GodotExporter`，让 `scene.tscn` 直接包含可见 `Sprite2D`
5. 为 `text_sign` 的 `text` 生成独立 Godot 文本层或 metadata

验收：

- `final/scene.tscn` 在 Godot 中打开能看到 object sprites
- `text_sign` 的可读文字来自 Godot 文本层，不来自 PNG 烘焙
- `final/map_data_applied.json` 中每个成功 mapping 都有顶层 `sprite_path`

### Phase 8：status 和端到端

任务：

1. 新增 `scene-status`
2. skill `all` 模式串联所有阶段
3. Mock Gemini 集成测试

验收：

- 完整流水线可重复运行
- 已完成阶段默认跳过
- `--force` 可覆盖指定阶段

---

## 10. 测试策略

单元测试：

- `test_scene_validate.py`
- `test_scene_map_build.py`
- `test_scene_images.py`
- `test_scene_pack.py`

集成测试：

- `test_full_scene_pipeline_mock.py`

人工测试：

- 使用真实 Dingbu school scene
- 打开 `preview.png`
- 打开 Godot `final/scene.tscn`
- 检查 sprite 锚点、尺寸和遮挡

---

## 11. 风险与缓解

### 风险 1：Claude 生成 JSON 不稳定

缓解：

- 每个 Claude 输出都必须 schema 校验
- skill prompt 内置最小合法示例
- 校验失败时输出字段路径，要求修正当前文件后重试

### 风险 2：LLM 生成的 map_spec 与 MapGenerator 能力不匹配

缓解：

- `objects[].type` 强制限制为 7 种 category enum，不允许具体物品名进入 type。
- 具体物品身份必须通过 `properties.object_key`、`label`、`properties.display_name` 表达。
- `properties.object_key` 必须是稳定 ASCII snake_case，不能从中文名临时推断。
- `properties.footprint`、`properties.facing`、`properties.blocking`、`properties.source_canvas` 由 `scene-validate` 做强校验。
- `facade_overlay` / `text_sign` 必须声明 `properties.attached_to`，并在跨文件校验中确认引用目标存在。
- `scene-map-build` 对未知 placement 给出清晰 warning，并按规则降级到 category 默认策略或 `random_walkable`。

### 风险 3：Gemini 图像质量不稳定

缓解：

- `--variants N`
- 保留 `images/{target_id}.json`
- 支持 `--target TARGET_ID --force` 单个素材强制重生成
- 使用 `source_canvas` 为细小或瘦高物件提供更合适的源画布，避免仅靠 footprint 推导导致图像过小

### 风险 4：text_sign 文字不可控或错误入图

缓解：

- `text_sign` prompt 必须要求空白牌面或无字表面，并在 negative 中加入 readable text / Chinese characters / letters。
- 实际文字只进入 `properties.text`、`entities[].text` 或 Godot 文本层，不进入 PNG。
- `scene-pack` 为 `text_sign` 单独生成文本节点或 metadata，确保后续可替换、可本地化、可调整字号。

### 风险 5：Godot 资源路径不稳定

缓解：

- `scene-pack` 统一拷贝 sprites 到 `final/sprites/`
- 导出时使用统一 `resource_base`
- 在 README 中写清复制到 Godot 项目的目标路径

---

## 12. DONE 定义

- [ ] 用户创建 `scene.md`
- [ ] `/linsen-asset-scene {title}` 可跑完整流水线
- [ ] `map_spec.json` 不依赖 `RulePromptParser` 生成
- [ ] `art_request.json` 包含所有关键 object
- [ ] `source_canvas` 从 `map_spec` 透传到 `art_request`、`entities`、`prompts/images` 和 `art_manifest`
- [ ] `facade_overlay` / `text_sign` 的 `attached_to` 通过跨文件校验
- [ ] `text_sign` 的可读文字由 Godot 文本层或 metadata 承载，不烘焙进 PNG
- [ ] `entities.json`、`prompts.json`、`art_manifest.json` 通过 schema 和跨文件校验
- [ ] `images/{target_id}.png` 命名稳定
- [ ] `scene-images --target TARGET_ID --force` 能单独重生指定素材
- [ ] `final/map_data_applied.json` 写入顶层 `sprite_path`
- [ ] `final/scene.tscn` 在 Godot 中能看到 object sprites
- [ ] 重跑时已完成阶段跳过
- [ ] 错误写入 `error.log`

---

## 13. 后续扩展

- `--add-entity`：补充实体后回到 ① spec 局部更新
- 多场景批处理
- 图像变体选择 UI
- 通用 tile atlas 编辑和多场景 tileset 合并
- 全图 image layer 仅作为概念参考或临时预览，不作为长期生产背景主路径
- Godot 运行时交互脚本生成

---

**END OF SPEC**
