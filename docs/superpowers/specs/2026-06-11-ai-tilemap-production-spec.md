# AI Tilemap Production - 美术驱动 tilemap 生产方案

**日期**：2026-06-11  
**关联 skill**：`linsen-asset-scene`  
**适用范围**：场景背景、地表 tile、道路/跑道/广场/水岸等 tilemap 结构化素材生成  
**硬约束**：最终美术像素必须来自 AI 生成结果。程序只负责结构规划、切片、拼接、校验、打包和人工编辑，不用程序化图形替代最终美术。

## 1. 背景问题

本轮“校园高达”测试暴露出三个必须解决的问题：

1. 直接让 AI 生成 tileset sprite sheet 时，tile 之间经常不连续，或者被模型理解成一张连续小地图，切片后无法作为重要 tilemap tile 直接使用。
2. 生成概念图之后，必须完整设计 tilemap 的每一块 tileset，甚至精确到每个 tile 格子，否则后续拼接没有结构依据。
3. 自动拼接后的 tilemap 不一定完美，必须提供 HTML 工具支持用户检查和手动调整 tile，才能得到可用的最终产物。

因此，后续流程不能只依赖“AI 直接生成 tileset -> 程序切片 -> 自动 pack”。必须加入格子级 blueprint、AI 美术源管理、自动校验和人工修正闭环。

## 2. 核心原则

### 2.1 AI 负责美术

所有最终进入 tileset、sprite、background tile 的像素都必须来自 AI 生成结果，包括：

- 地表 tile
- 道路 tile
- 边缘 tile
- 圆角 tile
- 水岸 tile
- 建筑/装饰/NPC sprite

程序不能用纯算法绘制最终美术 tile。程序可以做：

- 生成结构化 prompt
- 调用 AI
- 切图
- 拼接
- 校验
- 标记问题
- 生成 HTML editor
- 导出 reviewed JSON

### 2.2 概念图定风格，blueprint 定结构

AI 概念图只负责锁定整体风格：

- 色彩
- 光照
- 视角
- 描边粗细
- 纹理密度
- 氛围

`tilemap_blueprint.json` 负责锁定结构：

- 地图尺寸
- 每个格子的 material
- 每个格子的 role
- 每个格子的 layer
- 每个格子的复用策略
- 每个 tile 与邻接 tile 的合法关系

### 2.3 不强行复用所有 tile

tilemap 生产不是把所有相似格子强行合并。每个 tile candidate 应分级：

- `reusable_tile`：可复用，例如干净草地中心 tile。
- `variant_tile`：同类变体，例如不同草地细节。
- `unique_tile`：只在当前位置使用，例如概念图中受阴影或局部元素影响的格子。

为了最终效果，可以允许更多 unique/variant tile，再由用户在 editor 中手动合并。

### 2.4 AI 美术可用性优先

本方案的第一目标不是自动化程度最高，而是让 AI 生成的美术素材尽可能直接可用。

程序的职责是提高 AI 美术可用率：

- 把自然语言描述拆成更适合 AI 理解的结构化任务。
- 给 AI 提供清晰的风格参考、尺寸、视角、材质、连接关系和禁止项。
- 尽量让同一组、同一材质、同一连接关系的 tile 在同一次 AI 调用中生成。
- 从 AI 输出中选择、切片、标记和组合最可用的候选素材。
- 发现不可用素材后标记原因，并进入 AI 重生流程。

程序不能为了“看起来能用”而用程序化绘图修补最终美术内容。允许的处理包括裁剪、缩放到目标尺寸、透明度检查、元数据标记、拼接预览和打包；不允许用算法补画道路边缘、草地纹理、水岸、阴影、描边或其他最终可见美术细节。

AI 输出的可用性优先级：

1. 风格统一：palette、光照、视角、描边、纹理密度一致。
2. 结构正确：tile 的材质、role、连接方向符合 blueprint。
3. 可切片：slot 或 patch 边界清晰，不依赖可见网格线。
4. 可拼接：相邻 tile 的边缘材质、纹理密度、方向和明暗能自然衔接。
5. 可复用：reusable tile 不包含位置专属阴影、物体残影、文字或大面积独特图案。
6. 可编辑：不可用时能定位到具体 tile、group、patch 或 prompt 问题。

如果自动生成的素材不满足上述要求，应优先调整 prompt、分组方式、生成粒度或风格参考后重新调用 AI，而不是用程序替代 AI 美术。

## 3. 总体流程

推荐生产流程：

```text
scene.md
  -> map_spec.json
  -> style_profile.json
  -> AI background concept
  -> tilemap_blueprint.json
  -> tile_family_plan.json
  -> PixelLab create_tileset feasibility gate
  -> PixelLab transition/material tilesets
  -> optional AI tile-aligned full background render
  -> optional AI small tile family sheets / patch candidates
  -> tile_candidates.json + tile candidate PNGs
  -> initial tileset + tilemap preview
  -> tilemap_editor.html human review
  -> tilemap_blueprint.reviewed.json + tilemap_mapping.reviewed.json
  -> final pack / Godot export
```

## 4. 阶段设计

### 4.1 Scene Spec 阶段

输入用户自然语言描述，生成 `map_spec.json`。

职责：

- 解析基础地形：草地、稻田、水面、校园地面等。
- 解析地表结构：道路、跑道、广场、河流、围栏等。
- 解析前景对象：NPC、雕塑、喷泉、树、牌子、机甲等。

要求：

- 地表结构必须进入 `base_terrain`、`composites[]`、`tile_groups[]`。
- 前景对象进入 `objects[]`。
- 不允许把道路、跑道、广场这类 tilemap 结构作为一张大 sprite 处理。
- `objects[].type` 仍然只表示语义分类，不表示具体物品身份。

### 4.2 Concept 阶段

AI 生成完整 RPG 场景概念图：

```text
concept/background_concept.png
```

用途：

- 作为后续 tile 和 sprite 的风格参考。
- 帮助用户确认场景整体感觉。
- 帮助模型分析大结构和视觉重点。

注意：

- 概念图不是最终 tilemap。
- 概念图可以作为临时整图背景，但生产级 tilemap 必须进入 blueprint 和 editor 流程。

### 4.3 Tilemap Blueprint 阶段

新增文件：

```text
tilemap_blueprint.json
```

职责：

- 精确描述每个格子的 tile 语义。
- 让后续 AI 生成、切片、拼接都有结构依据。

示例：

```json
{
  "version": "1.0",
  "map_size": [16, 16],
  "tile_size": [64, 64],
  "layers": {
    "terrain": [
      {"x": 0, "y": 0, "material": "campus_lawn", "role": "center", "reuse": "variant_tile"},
      {"x": 4, "y": 5, "material": "plaza_brick", "role": "corner_top_left", "reuse": "reusable_tile"},
      {"x": 5, "y": 5, "material": "plaza_brick", "role": "edge_top", "reuse": "reusable_tile"}
    ],
    "path": [],
    "decoration": []
  },
  "adjacency_rules": [
    {"from": "campus_lawn", "to": "plaza_brick", "transition": "grass_to_plaza"}
  ]
}
```

必须表达：

- `x/y`：格子坐标。
- `layer`：terrain/path/decoration/building。
- `material`：材质族。
- `role`：center、edge_top、corner_bottom_right 等。
- `reuse`：reusable_tile、variant_tile、unique_tile。
- `source_reason`：为什么这个格子应该是这个 tile。

### 4.4 Tile Family Plan 阶段

新增文件：

```text
tile_family_plan.json
```

职责：

- 从 `tilemap_blueprint.json` 汇总需要生成的 AI tile group。
- 按材质/transition 拆分，不混合生成。

推荐分组：

- `grass_lawn`：草地中心、草地变体。
- `dirt_road`：泥路中心、上下左右边、转角。
- `grass_to_dirt`：草地到泥路 transition。
- `water_edge`：水面、水岸、内外角。
- `plaza_brick`：广场中心、边缘、圆角。
- `track_surface`：跑道直线、弯道、内外边。

sheet 规模限制：

- 3x3：中心 + 四边 + 四角。
- 2x4：道路、河流、跑道转角专用。
- 4x4：上限，只放同一材质族。
- 禁止 8x8、10x10 大型综合 tileset 作为主流程。

### 4.5 AI Tile 生成阶段

AI tile 生成分为一个候选主路径和若干辅助路径。当前经过真实 Gemini 与 PixelLab `create_pixen` 验证后，普通生图模型直接生成可切片 patch 的方案不能作为主路径。

#### 路径 P：PixelLab create_tileset transition tileset

候选主路径是 PixelLab.ai 的专用 `create_tileset` 接口，而不是普通 `create_pixen` 生图接口。

接口语义：

```python
create_tileset(
    lower_description,
    upper_description,
    transition_description,
    tile_size=16 or 32,
    transition_size=0.5,
    view="high top-down",
    outline="single color black outline" | "selective outline",
    detail="medium detail" | "highly detailed"
)
```

该接口用于生成 Wang tiles / transition tileset，适合两种地表材质之间的连接关系。

推荐用途：

- `grass_lawn -> dirt_road`
- `grass_lawn -> plaza_brick`
- `grass_lawn -> running_track`
- `grass_lawn -> water`
- `wheat_field -> dirt_road`
- `campus_lawn -> campus_walkway`

生产要求：

- `lower_description` 与 `upper_description` 必须是纯材质描述，不包含建筑、角色、装饰物或完整场景。
- `transition_description` 必须描述两种材质的边界细节，不描述完整道路、完整跑道或完整地图。
- PixelLab 源 tile 优先使用该接口支持的最高规格 32x32，再用 nearest-neighbor 无损放大到项目标准 64x64。
- 不使用 `medium detail` 作为生产默认值；默认使用 `highly detailed`，但 prompt 必须要求大形状清晰、颜色层次丰富、避免微碎噪点。
- prompt 必须包含可爱风格、色彩丰富、共享 palette、清晰材质边界、32px 小尺寸可读性等约束。
- 道路类不能只验证一种 dirt road。至少要覆盖乡村泥路、校园步道/石板路、跑道、水岸等多种路面/边界组合。
- 输出原始 JSON 必须保存，不能只保存图片。
- 原始 tile size 只允许 16 或 32，进入本项目 tilemap 前统一无损放大到 64x64。
- 每个返回 tile 必须建立连接签名，用于映射到 blueprint 中的 center、edge、corner、transition、inside/outside corner 等角色。
- 进入正式 pack 前必须经过 `PixelLab create_tileset feasibility gate`。

限制：

- 当前额度已用完，该路径尚未完成真实验证。
- 在验证通过前，它只能作为“候选主路径”，不能替代现有人工 review gate。
- 如果返回结构无法稳定解析、缺少内外角、风格不可控或无法映射到 Godot tilemap，则不得作为主路径。

#### PixelLab create_tileset feasibility gate

额度恢复后，必须先验证以下最小集合：

1. `grass_to_dirt_road`
2. `grass_to_plaza`
3. `grass_to_running_track`
4. `grass_to_water`
5. `wheat_to_dirt_road`
6. `campus_lawn_to_stone_walkway`
7. `campus_lawn_to_brick_walkway`

每个验证项必须输出：

- 原始 API JSON。
- 原始 tileset image 或独立 tile PNG。
- 64x64 放大后的 tile PNG。
- contact sheet。
- 10x10 示例拼接 preview。
- `review.html`。
- 自动解析报告。

通过标准：

1. 能稳定解码 API 返回内容。
2. 能识别或人工标注每个 tile 的连接签名。
3. 放大到 64x64 后像素风不糊。
4. 示例拼接没有明显断边、黑线、透底或材质跳变。
5. transition 覆盖至少四边、四角和必要的内外角。
6. 不混入建筑、角色、文字、图标或不属于材质的装饰物。
7. review 后的 mapping 能被 pack 使用。

如果该 gate 通过，路径 P 替代原先的 small tile family sheet / patch generation，成为地表和 transition tileset 的主生成路径。

#### 路径 A：AI tile-aligned full background render

生成完整背景图：

```text
ai_background/background_tile_aligned.png
```

要求：

- 输出尺寸 = `map_width * tile_size` × `map_height * tile_size`。
- 例如 16x16、64px tile 输出 1024x1024。
- 不画可见网格。
- 所有材质边界必须贴合隐形 64px 网格。
- 根据 `tilemap_blueprint.json` 绘制每格内容。

用途：

- 保证整体连续性。
- 提供 `from_full_render` tile candidates。
- 对局部 unique/variant tile 特别有价值。

限制：

- 该路径不能被视为稳定的 reusable tileset 来源，因为 AI 不一定严格遵守隐形网格。
- 该路径优先用于生成整体风格、局部连续感、unique tile、variant tile 和人工参考。
- 如果某个区域切片后边界不自然，应标记为 `needs_regeneration`，改用 tile family sheet 或 patch regeneration。

#### 路径 B：AI small tile family sheets

按 `tile_family_plan.json` 生成小型 sprite sheet。该路径降级为辅助路径，只在 PixelLab `create_tileset` 不能覆盖某类材质、或需要生成装饰性 variant tile 时使用。

要求：

- 每个 sheet 只包含同一材质或同一 transition。
- 共享 palette、光照、纹理密度、描边。
- 地表 tile 必须不透明铺满。
- 不混入物件 sprite。

必须加入禁止项：

```text
no visible grid lines
no labels
no text
no frames
no icons floating on background
no perspective drift
no shadows that make tiles look like objects
this is an asset catalog sheet, not a map preview
adjacent slots are not neighboring map cells
do not draw one continuous scene across slots
no black separator seams
each slot must work after being cropped alone
```

#### 路径 C：AI tile patch generation

该路径已经过真实 Gemini 与 PixelLab `create_pixen` 快速验证，结论是：基础地表和简单十字路有局部可用性，但复杂 transition、跑道弯道、水岸弯道不稳定。因此它不能作为主生产路径，只能作为受限候选来源。

对连续性要求高但不要求严格 reusable tileset 的地表，可以生成小型 patch，再切片为 unique/variant tile。

推荐 patch：

- 3x3：中心 tile 与四边四角，用于草地、广场、泥地、砖地。
- 2x3 / 3x2：横向或纵向道路、河流、跑道直线段。
- 3x3 / 4x4：道路交叉口、跑道弯道、水岸内外角、小广场边界。

patch 生成要求：

- 画面是同一材质或同一 transition 的连续小区域。
- 输出尺寸必须是 `tile_size * patch_grid`。
- 不显示网格线、边框、编号或标签。
- 每个 64x64 单元切出后都能独立作为 tile 使用。
- patch 内部边缘必须自然连续；patch 外边缘必须符合连接签名。

patch 适合补充 unique/variant tile，不适合作为复杂 reusable transition tileset 的主来源。

#### 生成粒度选择规则

不同素材采用不同 AI 调用方式：

- 大面积基础地表：优先 `patch generation`，再从 patch 中切出 center/variant tile。
- 道路、跑道、河流：优先按直线段、交叉口、弯道、端点分 patch 生成。
- 材质 transition：优先按 3x3 transition patch 生成，必须包含内角、外角和边缘。
- 装饰性地表细节：可以作为 variant tile 或 decoration tile 单独生成。
- 前景对象：单独透明 sprite 生成，不混入地表 tile。

同一材质族、同一 transition 族、同一道路/跑道语义组应尽量在同一次 AI 调用中生成，避免分散调用导致 palette、描边和纹理密度漂移。

在路径 P 验证通过后，生成粒度优先级调整为：

1. PixelLab `create_tileset` 生成 transition/material family。
2. Gemini concept 作为整体风格参考。
3. `create_pixen` 只生成独立 sprite 或明确单 tile，不生成完整 patch。
4. patch generation 只作为 unique/variant tile 辅助来源。

### 4.6 Tile Candidate 阶段

新增目录和文件：

```text
tile_candidates/
  *.png
tile_candidates.json
```

程序从 AI 输出中裁切候选 tile：

- 从 `background_tile_aligned.png` 按格裁切。
- 从 small tile family sheet 按 slot 裁切。
- 对每个 candidate 记录来源和语义。

示例：

```json
{
  "candidate_id": "plaza_brick_edge_top_01",
  "source": "from_tile_sheet",
  "source_image": "tile_sheets/plaza_brick_3x3.png",
  "source_rect": [64, 0, 64, 64],
  "material": "plaza_brick",
  "role": "edge_top",
  "reuse": "reusable_tile"
}
```

### 4.7 初版拼接和校验阶段

生成：

```text
tilemap_mapping.json
tileset.png
preview_applied.png
```

程序根据 blueprint 和 candidates 生成初版 tilemap。

自动校验：

- 缺失 tile。
- 非法邻接。
- 透明地表 tile。
- slot 边缘明显黑线。
- tile 尺寸错误。
- candidate 来源不一致。
- 同一 reusable tile 在不同位置表现明显不适配。

校验只标记问题，不直接替代美术。

### 4.8 HTML Tilemap Editor 阶段

新增：

```text
tilemap_editor.html
```

这是质量闭环的核心工具。

必须支持：

- 显示最终 tilemap preview。
- 显示 AI full background render。
- 支持两者叠加对比，带透明度滑杆。
- 显示/隐藏网格。
- 显示 layer：terrain/path/decoration/collision。
- 点击格子查看：
  - x/y
  - material
  - role
  - tile_id
  - candidate_id
  - source
  - reuse 类型
- 支持从 tileset palette 替换某个格子。
- 支持吸管。
- 支持矩形刷。
- 支持橡皮擦。
- 支持将 tile 标记为 reusable/variant/unique。
- 支持把多个 candidate 合并为同一个 tile_id。
- 支持标记某个 tile 或 tile group 需要重新 AI 生成。
- 支持导出 reviewed JSON。

由于纯 `file://` 页面不能静默写回本地，至少要提供复制按钮：

```text
Copy reviewed tilemap JSON
Copy reviewed mapping JSON
```

后续可以增加本地 server 模式写回文件。

### 4.9 AI Patch Regeneration 阶段

用户在 editor 中标记不满意项后，重新调用 AI。

支持三种粒度：

1. 单 tile 重生。
2. 小型 tile group 重生。
3. 区域 patch 重生，例如 3x3 或 4x4。

所有 patch 仍然来自 AI 生成结果。

### 4.10 Final Pack 阶段

使用 reviewed 文件打包：

```text
tilemap_blueprint.reviewed.json
tilemap_mapping.reviewed.json
```

输出：

```text
final/tilesets/scene_tileset.png
final/map_data_applied.json
final/preview_applied.png
final/scene.tscn
```

## 5. 文件结构

建议最终场景目录结构：

```text
scene.md
map_spec.json
style_profile.json

concept/
  background_concept.png
  background_concept.json

tilemap_blueprint.json
tile_family_plan.json

ai_background/
  background_tile_aligned.png
  background_tile_aligned.json

tile_sheets/
  grass_lawn_3x3.png
  plaza_brick_3x3.png
  campus_walkway_2x4.png

tile_candidates/
  *.png
tile_candidates.json

tilemap_mapping.json
tilemap_editor.html
tilemap_blueprint.reviewed.json
tilemap_mapping.reviewed.json

images/
  foreground sprites

final/
  preview_applied.png
  map_data_applied.json
  tilesets/scene_tileset.png
  scene.tscn
```

## 6. 前景对象生成规则

物件 sprite 单独生成，不混进地表 sheet。

包括：

- 树
- 箱子
- NPC
- 牌子
- 门
- 椅子
- 喷泉
- 雕塑
- 机甲

要求：

- 透明背景。
- 居中。
- 尺寸符合 `source_canvas`。
- `faces_south` 等朝向必须正向约束。
- 禁止 checkerboard、fake transparency、背景板。

## 7. 验收标准

一个场景的 tilemap 生产合格条件：

1. `tilemap_blueprint.json` 能解释每个格子的 material/role。
2. 地表 tile 的最终像素全部来自 AI 输出。
3. 地表 tile 不透明铺满 64x64。
4. 所有 AI sheet 都通过切片尺寸校验。
5. 初版 preview 可打开，且不是空图。
6. HTML editor 能打开并修改 tile mapping。
7. 用户 reviewed JSON 可被 pack 使用。
8. final preview 与 reviewed mapping 一致。
9. Godot export 能引用最终 tileset。

美术可用性验收还必须检查：

1. 同一 tile family 内 palette、光照、描边、纹理密度一致。
2. 相邻 tile 的边缘没有明显断裂、黑线、错位、材质跳变或透底。
3. reusable tile 不包含文字、角色、建筑残影、局部阴影或明显位置专属元素。
4. transition tile 的四边连接类型与 blueprint 邻接关系一致。
5. 道路、跑道、河流等线性结构的直线段、转角、交叉口、端点都能被 tile 语法解释。
6. full background render 切出的 tile 如果不可复用，必须被标记为 unique、variant 或 needs_regeneration。
7. 不可用素材必须记录失败原因，例如 `style_drift`、`edge_mismatch`、`wrong_role`、`contains_object_artifact`、`bad_transparency`、`not_tile_aligned`。
8. 重新生成后必须保留失败记录和新候选记录，方便比较不同 AI prompt 或生成粒度的效果。

## 8. 不再作为主流程的做法

以下做法只能作为临时调试，不能作为生产主流程：

- 直接让 AI 生成 8x8、10x10 综合大 tileset。
- 没有 blueprint 就直接生成 tile。
- 没有 editor 就把自动 pack 结果视为最终产物。
- 强行合并所有相似 tile。
- 用程序化图形替代 AI 美术 tile。
- 用程序自动补画、延展或重绘最终可见的地表、道路、水岸、阴影、描边。
- 明知道 tile family 风格漂移仍继续 pack，而不是标记并重新 AI 生成。

## 9. 实施优先级

### P0：结构闭环

1. 增加 `tilemap_blueprint.json` schema 和生成阶段。
2. 增加 `tile_family_plan.json` schema 和生成阶段。
3. 增加 tile candidate 切片和 `tile_candidates.json`。
4. 增加初版 `tilemap_editor.html`。

### P1：AI 生成质量

1. 支持 AI tile-aligned full background render。
2. 支持小型 tile family sheet 生成。
3. 支持按 concept image 作为风格参考。
4. 支持局部 patch regeneration。

### P2：编辑体验

1. 支持 palette 替换。
2. 支持吸管和矩形刷。
3. 支持 layer 开关。
4. 支持问题高亮。
5. 支持本地 server 模式写回 JSON。

## 10. 结论

最终方案不是“AI 直接出 tileset”，而是：

**AI 出风格图和 tile-aligned 美术源，系统做结构化切片、拼接、校验，用户用 HTML editor 做最终修正。**

这个方案同时满足：

- 美术全部依赖 AI。
- tilemap 结构有 blueprint 依据。
- tile 连续性可以通过完整背景 render 和人工 review 提高。
- 最终产物可以被用户检查、修正和确认。
