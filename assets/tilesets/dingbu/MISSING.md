# dingbu 缺失素材清单

记录 dingbu 风格 TileSet 当前缺失、留待后续补齐的素材。

## TileSet (resources/tilesets/dingbu_main.tres)

### 已纳入

- ground_32 × 8 source（草/泥/沙/水泥/泥潭/石板/杂草/水面）
- nature_32 × 16 source（树/灌木 12 + 岩石 4）
- buildings_scaled × 5 source（teaching 10×3, dormitory 7×2, shop 3×2, canteen 4×2, toilet 2×2）

### 待补

- **collider_marker.png (32×32)** — 半透明红色占位 tile，用于墙体/不可走区域。需要后续生成 PNG 后追加到 tileset 作为 ColliderAtlas，并配 32×32 矩形 collision shape (physics_layer_0)。
  - 当前 tileset 物理层已声明 (collision_layer=1, mask=0)，但没有任何 tile 配 polygon。
  - 临时方案：home 场景路线 B 中可用 `home_collisions` 子层 + 任何现成 ground tile（如 ground_r1_c0 泥潭）做"假墙体"，或直接用 StaticBody2D + RectangleShape2D 节点画墙。
- **室内家具 tile** — 课桌、黑板、教师讲台、寝室上下铺、商店货架等。当前 nature/buildings 不含室内家具，二班教室/宿舍内景需要这些。
- **路径/小道 tile** — 校园里跑道、林荫道边缘连接等专用 tile（目前用 ground_r0_c2 水泥道兜底）。
- **建筑细节遮罩** — buildings_scaled 是整张贴图被切成 32×32 网格，其中每 tile 的 alpha 边角不规则。如果需要严格的"建筑外轮廓 collision"，需要逐 tile 画 polygon（暂用 StaticBody2D 替代）。
- **门/窗交互高亮 tile** — scene_door 上方的"按 Z 交互"提示视觉，目前由代码层处理，TileSet 不需要。

## 备注

- TileSet 自定义数据层 `trigger_id` (string) 已声明，可在编辑器里给单 tile 标 "scene_classroom_door" 这类字符串，运行时由 TileMapLayer.get_cell_tile_data() 读取。
- 未来如要从 8 个 ground 单 PNG 合成单张 sprite sheet，可放到 `assets/tilesets/dingbu/ground_32_sheet.png` 后做单 atlas + 8 tile，减少 source 数量。当前选 8 source 路线为简化机械化操作。
