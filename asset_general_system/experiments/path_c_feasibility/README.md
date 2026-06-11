# Path C Feasibility Spike

日期：2026-06-11

目的：快速验证 `AI tile patch generation` 是否能作为 tilemap 美术生产路径。

验证方法：

1. 用 Gemini 生成 4 类小型 patch。
2. 将原图规整到目标尺寸。
3. 按 64x64 切片。
4. 重拼原 patch。
5. 将中心 tile 重复铺成 4x4。
6. 生成 `review.html` 和 `reports/contact_sheet.png` 人工检查。

## Case 结果

### Gemini

| case | 初步结论 | 说明 |
| --- | --- | --- |
| `grass_3x3_patch` | 通过 | 纯地表连续性好，center tile 重复铺基本可用。 |
| `grass_to_plaza_3x3_patch` | 不通过 | 画面好看，但不是规范 3x3 transition 语法，center repeat 不可用。 |
| `road_cross_3x3_patch` | 条件通过 | 十字路结构清晰，切片后角色可解释，是 Path C 的正例。 |
| `track_curve_4x4_patch` | 不通过 | 生成了完整小赛道局部，而不是可复用的四分之一弯道 tile 语法。 |

### Pixellab v2

| case | 初步结论 | 说明 |
| --- | --- | --- |
| `grass_3x3_patch` | 不通过 | 生成了 9 个重复的岛状草坪 tile，不是一整片连续地表。 |
| `grass_to_plaza_3x3_patch` | 不通过 | 画成了带建筑/台阶/装饰的场景局部，不是纯 transition family。 |
| `road_cross_3x3_patch` | 条件通过 | 道路结构可解释，但偏离为城市道路/石板角落，并混入井盖等装饰。 |
| `track_curve_4x4_patch` | 不通过 | 生成完整环形跑道和周边装饰，不是可复用四分之一弯道部件。 |

## 初步判断

Path C 不是无条件可作为主生产路径。

可以继续使用的范围：

- 纯基础地表，如草地、泥地、稻田、砖地中心变体。
- 简单、强结构、容易用 3x3 表达的道路交叉或局部结构。
- unique/variant tile 的来源。

不能直接依赖的范围：

- 不规则 transition。
- 复杂曲线，例如跑道弯道、水岸弯道。
- 需要严格可复用边缘语法的 tileset family。

## 后续策略

1. Path C 必须从“默认主路径”调整为“按材质/结构验证后启用”。
2. 对 transition 和复杂曲线，需要更严格的 tile grammar：
   - 四边连接签名。
   - 明确内角、外角、边缘、中心、端点。
   - 每次只生成一个很小的语义部件，而不是让 AI 画完整局部地图。
3. 正式流程应保留 `tile_patch_feasibility_test`，每个新 material/transition family 首次使用前都先生成小样。

## 产物

- `prompts/`：4 个验证 prompt。
- `raw/`：Gemini 原图，已 gitignore。
- `sliced/`：64x64 切片，已 gitignore。
- `recomposed/`：重拼图、网格预览、center repeat，已 gitignore。
- `reports/summary.json`：自动指标，已 gitignore。
- `reports/contact_sheet.png`：人工总览图，已 gitignore。
- `review.html`：人工 review 页面，已 gitignore。

Pixellab v2 对比产物：

- `raw_pixellab/`：Pixellab 原图，已 gitignore。
- `sliced_pixellab/`：64x64 切片，已 gitignore。
- `recomposed_pixellab/`：重拼图、网格预览、center repeat，已 gitignore。
- `reports_pixellab/summary.json`：自动指标，已 gitignore。
- `reports_pixellab/contact_sheet.png`：人工总览图，已 gitignore。
- `review_pixellab.html`：人工 review 页面，已 gitignore。
