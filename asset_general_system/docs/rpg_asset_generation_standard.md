# RPG 素材生成规范与验收标准

更新时间：2026-06-08

## 1. 目标

当前系统不能只追求“AI 生成了 PNG”，而要产出可放入 RPG 地图的生产级素材。本文定义两件事：

- **Prompt 标准**：生成前必须明确素材类型、地图位置、朝向、尺寸、结构和禁止项。
- **验收标准**：生成后必须同时通过技术、结构、美术、地图适配四类检查。

不满足本文标准的素材不得写入公共资源库，也不得作为地图最终素材引用。

## 2. 基本原则

1. **生成尺寸不等于地图 tile 尺寸**  
   地图里一个对象可能占 `3x2 tiles`，但 AI 工作画布应更高，例如 `512x384` 或 `768x512`。先生成高清源图，再按地图 runtime 尺寸缩放或派生预览。

2. **先定义地图语义，再生成图像**  
   生成对象前必须知道它放在哪里、面向哪里、和谁发生空间关系。不能只拿“乒乓球台”“小卖部”这种短词直接生成。

3. **类型化 prompt，不共用一套模板**  
   建筑、大型道具、小型道具、细长物件、墙面装饰、文字牌匾、角色、特效必须使用不同 prompt 模板。

4. **文字不要交给图像模型硬画**  
   招牌、标语、海报中的文字优先由程序或后处理叠加。图像模型只负责生成底板、牌匾、墙面或海报框。

5. **公共资源库只收合格素材**  
   透明背景干净不代表素材可用。结构不完整、视角错误、主体不可读、风格漂移的图片即使技术校验通过，也不能入库。

## 3. 生成规格字段

每个对象生成前必须整理成 `AssetGenerationSpec`，至少包含：

| 字段 | 说明 |
| --- | --- |
| `asset_id` | 稳定 ID，例如 `school_shop_rural_2008` |
| `display_name` | 用户可读名称，例如 `小卖部` |
| `category` | `building`、`large_prop`、`small_prop`、`thin_prop`、`facade_overlay`、`text_sign`、`character`、`vfx` |
| `map_role` | 它在地图中的作用，例如阻挡建筑、可交互道具、墙面装饰、氛围物件 |
| `placement_zone` | 所在区域，例如 `upper_left`、`school_front`、`playground`、`mud_road`、`school_facade` |
| `relative_position` | 相对关系，例如 `宿舍楼右边`、`食堂左前方`、`教学楼正墙` |
| `footprint` | 地图占格，例如 `3x2 tiles` |
| `source_canvas` | AI 工作画布，例如 `512x384 px` |
| `runtime_size` | 地图显示尺寸，例如 `96x64 px` |
| `anchor` | 放置锚点，例如 `bottom_center`、`center`、`bottom_left` |
| `facing` | 朝向约束，例如 `faces_south`、`faces_playground`、`front_visible` |
| `view_style` | 视角，例如 `top_down_3_4_rpg` |
| `required_parts` | 必须出现的结构件 |
| `forbidden_parts` | 禁止出现的内容 |
| `text_policy` | `no_text`、`programmatic_text`、`large_readable_text_only` |

## 4. 通用 Prompt 模板

所有真实生成 prompt 必须由结构化字段拼装，不允许只使用对象短描述。

```text
Create a production-ready RPG map asset sprite.

Asset:
- Name: {display_name}
- Category: {category}
- Map role: {map_role}
- Placement: {placement_zone}, {relative_position}
- Footprint in map: {footprint} tiles
- Source canvas: {source_canvas}px
- Runtime display size: {runtime_size}px
- Anchor: {anchor}
- Facing: {facing}
- View: {view_style}

Subject requirements:
- Draw exactly one complete {display_name}.
- Required parts: {required_parts}
- Subject should occupy {subject_coverage}% of the usable canvas.
- Keep transparent margins around the object.

Style:
- 16-bit RPG pixel art.
- Crisp hard pixel edges.
- Limited clean palette.
- Same perspective and lighting as the map.

Output:
- Real PNG alpha transparency.
- No background, no floor, no terrain, no sky, no scene.
- No checkerboard, no fake transparency, no UI, no labels, no watermark.
- Text policy: {text_policy}.

Forbidden:
- {forbidden_parts}
```

## 5. 类型模板

### 5.1 建筑 `building`

适用：教学楼、宿舍楼、小卖部、食堂、厕所、广播室。

必须字段：

- `facing`：建筑正面朝向，通常朝向道路、操场、入口或玩家可接近方向。
- `door_side`：门在哪一侧，例如 `south/front`。
- `roof_visible`：屋顶是否可见，默认可见。
- `facade_visible`：正面必须可见，不能只画屋顶。
- `required_parts`：墙体、屋顶、门、窗、基础装饰。

推荐画布：

- 小建筑：`640x384` 或更高。
- 中大型建筑：`768x512`、`1024x768`。

建筑验收：

- 缩放到地图尺寸后仍能看出门、窗、屋顶和主体轮廓。
- 正面必须朝向指定区域，不能随机转向。
- 不能带地面、天空、远景、道路、花草场景。
- 建筑不能被裁切，不能只画局部。

示例约束：

```text
小卖部位于宿舍楼右边、食堂前方，正面朝向校园内侧/操场方向。生成时必须画出一层砖房、瓦顶、开口柜台和小卖部招牌底板；招牌文字后处理叠加，不让模型直接画字。
```

### 5.2 大型道具 `large_prop`

适用：乒乓球台、升旗台、淘米池、长椅、花坛、柜台。

必须字段：

- `axis`：横向或纵向摆放。
- `interaction_side`：玩家可交互的一侧。
- `required_parts`：完整主体结构，不允许只画局部细节。

推荐画布：`384x256`、`512x384`。

验收重点：

- 必须完整。比如乒乓球台必须同时有台面、支撑、中间网。
- 缩小后主体仍清楚，不应只剩一条线或几个碎块。
- 不能带场地地面或阴影块。

示例约束：

```text
水泥乒乓球台位于操场中，长边沿操场横向排列。必须生成完整浅灰水泥台面、两个支撑块、中间红砖网；禁止球拍、球、人、地面和散落砖块。
```

### 5.3 小型道具 `small_prop`

适用：花盆、饭盒堆、煤堆、柴堆、水桶、鸡、狗、零食柜台小件。

推荐画布：最低 `256x256`，复杂小件 `384x384`。

验收重点：

- 主体占画布不能过小。
- 缩放到 `32x32` 或 `48x48` 后仍能识别。
- 不能生成多个变体，除非明确要求 sprite atlas。

### 5.4 细长物件 `thin_prop`

适用：电线杆、高音喇叭、旗杆、篮球架、单杠、双杠、晾衣绳、栏杆。

推荐画布：

- 竖向：`320x512`、`384x640`。
- 横向：`512x256`。

验收重点：

- 主体不能过细导致缩小后断裂。
- 必须有明确锚点，例如旗杆/电线杆锚定底部中心。
- 附件方向要符合地图位置，例如喇叭朝向操场，篮球框朝向可活动区域。

### 5.5 墙面装饰 `facade_overlay`

适用：海报、标语横幅、黑板报、招牌底板、墙面栏杆、走廊装饰。

推荐策略：

- 生成为覆盖层，不作为独立地面物件。
- 视角和建筑正面一致。
- 默认不生成真实文字，只生成可承载文字的底板。

验收重点：

- 必须能贴合目标建筑正面。
- 不能生成独立场景或带墙外环境。
- 如果与建筑绑定，应记录 `parent_object_id` 和 `attach_side`。

### 5.6 文字牌匾 `text_sign`

适用：`丁埠小学` 招牌、`好好学习 天天向上` 标语、厕所牌、小卖部牌。

推荐策略：

1. AI 生成空白牌匾、横幅、墙面底板。
2. 程序使用字体或像素字库叠加文字。
3. 导出时保存文字内容、字体、颜色、位置。

验收重点：

- 文字必须可读。
- 小尺寸不可读时，不应硬塞完整文字，应使用局部符号或在高清预览层显示。

## 6. 地图位置与朝向约束

对象朝向不能只由素材类型决定，必须由地图位置和交互关系决定。

### 6.1 坐标约定

- 地图上方：north / top。
- 地图下方：south / bottom。
- 地图左侧：west / left。
- 地图右侧：east / right。
- 玩家常见观察方向：从地图下方向上看，建筑正面通常朝 south/down。

### 6.2 建筑朝向规则

| 放置关系 | 默认朝向 |
| --- | --- |
| 建筑位于操场上方 | 正面朝 south/down，面向操场 |
| 建筑位于道路上方 | 正面朝 south/down，门朝道路 |
| 建筑在主建筑左侧 | 正面朝 south 或 south-east，面向校园内侧 |
| 建筑在主建筑右侧 | 正面朝 south 或 south-west，面向校园内侧 |
| 建筑作为地图顶部背景 | 可弱化正面，但入口必须朝可达路径 |

建筑 prompt 必须包含：

```text
The front facade faces {target_zone}. The entrance/door is on the {door_side} side and must remain visible.
```

### 6.3 道具朝向规则

| 道具类型 | 朝向/轴向 |
| --- | --- |
| 乒乓球台、长椅、淘米池 | 长边沿放置区域主轴，操场通常横向，路边通常沿路 |
| 篮球架 | 篮筐朝向操场可活动区域 |
| 电线杆高音喇叭 | 喇叭朝向操场或人群区域 |
| 晾衣绳、栏杆 | 沿建筑墙面或边界横向贴合 |
| 水井、花盆、水桶 | 无强朝向，但必须有可交互侧 |
| 动物/NPC | 默认朝行进方向；静态交互对象朝向玩家可接近方向 |

### 6.4 墙面元素绑定规则

墙面元素不能随意生成成地面物件。必须记录：

- `parent_object_id`：绑定建筑，例如 `school_main_01`。
- `attach_side`：`front/south`、`left/west`、`right/east`。
- `attach_offset`：相对建筑正面的偏移。
- `layer_order`：绘制在建筑上方还是下方。

示例：

```json
{
  "display_name": "红漆标语横幅",
  "category": "facade_overlay",
  "parent_object_id": "school_main_01",
  "attach_side": "front",
  "facing": "faces_south",
  "text_policy": "programmatic_text"
}
```

### 6.5 地图语义到素材约束示例

用户描述：

```text
教学楼下方是一片操场，操场上有篮球架、单杠双杠、水泥乒乓球台。
```

应解析为：

```json
[
  {
    "display_name": "教学楼",
    "category": "building",
    "placement_zone": "school",
    "relative_position": "north of playground",
    "facing": "faces_south",
    "door_side": "south",
    "anchor": "bottom_center"
  },
  {
    "display_name": "水泥乒乓球台",
    "category": "large_prop",
    "placement_zone": "playground",
    "axis": "east_west",
    "interaction_side": "south",
    "anchor": "center"
  },
  {
    "display_name": "篮球架",
    "category": "thin_prop",
    "placement_zone": "playground",
    "facing": "hoop_faces_play_area",
    "anchor": "bottom_center"
  }
]
```

## 7. 验收标准

### 7.1 技术验收

- PNG 必须有真实 alpha。
- 四角必须透明。
- 透明区域 RGB 应清零或不污染。
- 不允许棋盘格、纯色底、黑底噪点。
- 不允许明显半透明杂色边。
- 源图尺寸必须达到类别最低工作画布。

### 7.2 结构验收

- 必须出现 `required_parts` 中所有结构。
- 不能只画局部、碎片、装饰细节。
- 不能把单物件生成成完整场景。
- 不能生成多个互相竞争的主体。

### 7.3 地图适配验收

- 朝向与 `placement_zone`、`relative_position` 一致。
- 锚点正确，放入地图不会漂浮或错位。
- footprint 与实际主体宽高比例一致。
- 交互对象旁边必须留出可行走 tile。
- 墙面覆盖层必须能贴到父建筑对应面。

### 7.4 美术验收

- 缩放到 runtime 尺寸后仍可识别。
- 轮廓清楚，主体占比合适。
- 像素边缘清晰，不是模糊滤镜感。
- 透视、光照、色板与同地图素材一致。
- 不允许伪文字、乱码、不可读小字。

## 8. 入库规则

公共资源库写入前必须保存：

- 原始用户 prompt。
- 结构化 `AssetGenerationSpec`。
- 最终生成 prompt。
- 源图路径。
- runtime 派生图路径。
- 质量报告。
- 人工或自动验收状态。

只有 `accepted` 状态可以被默认复用。`rejected` 和 `needs_review` 不得作为缓存命中结果。

## 9. 当前待办

- [ ] 为 `AssetGenerationSpec` 建模，补充 `category / placement_zone / relative_position / facing / anchor / required_parts / forbidden_parts / text_policy`。
- [ ] Python CLI 在生成前展示结构化对象规格，让用户逐项确认位置、朝向、尺寸和生成策略。
- [ ] 为建筑、大型道具、小型道具、细长物件、墙面装饰、文字牌匾分别实现 prompt 模板。
- [ ] 公共资源库增加 `accepted / needs_review / rejected` 状态，不合格素材不得命中缓存。
- [ ] 增加地图预览级验收：把素材按 footprint 放回地图，检查朝向、锚点、缩放后可读性。
