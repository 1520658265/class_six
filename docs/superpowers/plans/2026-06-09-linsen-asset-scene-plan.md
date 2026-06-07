# linsen-asset-scene Implementation Plan

> **For agentic workers:** 按 task 顺序实施。每个 task 使用 checkbox (`- [ ]`) 跟踪进度；完成一个 task 后先跑该 task 的验收命令，再进入下一个 task。

**Goal:** 实现 `linsen-asset-scene` 场景驱动素材生成流水线：`scene.md -> map_spec.json -> map_data/art_request/preview -> style/entities/prompts -> images -> art_manifest -> final/scene.tscn`。

**Architecture:** LLM 负责语义和美术上下文，Python 负责 schema 校验、几何放置、文件 I/O、图像生成调用、manifest、Godot 导出和进度记录。新流水线不调用 `RulePromptParser.parse()`；旧 `generate.py --type map` 保留为 legacy。

**Tech Stack:** Python 3.x, Pydantic, JSON Schema, Pillow/preview renderer, Gemini image generator, Godot 4.x `.tscn` export, Claude skill.

**关联 spec:** `docs/superpowers/specs/2026-06-09-linsen-asset-scene-spec.md`

---

## File Structure

| 路径 | 责任 | Task |
|---|---|---|
| `asset_general_system/specs/scene_map_spec.schema.json` | scene 专属 map spec 约束 | 1 |
| `asset_general_system/specs/scene_style_profile.schema.json` | style_profile 契约 | 1 |
| `asset_general_system/specs/scene_entities.schema.json` | entities 契约 | 1 |
| `asset_general_system/specs/scene_prompts.schema.json` | prompts 契约 | 1 |
| `asset_general_system/specs/art_manifest.schema.json` | manifest 契约 | 1 |
| `asset_general_system/specs/progress.schema.json` | progress 契约 | 1 |
| `asset_general_system/style_defaults.json` | 默认风格配置 | 1 |
| `asset_general_system/generator/scene/` | 新流水线核心模块 | 2-8 |
| `asset_general_system/generator/map/generator.py` | category-based placement | 3 |
| `asset_general_system/generator/models/tilemap_data.py` | ObjectData 透传字段 | 3 |
| `asset_general_system/generate.py` | 新 CLI 子命令入口 | 4, 7, 8, 9 |
| `asset_general_system/generator/assets/object_generator.py` | 目标命名和 source_canvas 支持 | 7 |
| `asset_general_system/generator/export/godot_exporter.py` | Sprite2D 和 text label 导出 | 8 |
| `.claude/skills/linsen-asset-scene/SKILL.md` | Claude skill 工作流 | 10 |
| `asset_general_system/tests/test_scene_*.py` | 新流水线测试 | 各 task |

建议新增 `asset_general_system/generator/scene/` 下列模块：

```text
asset_general_system/generator/scene/
├── __init__.py
├── constants.py
├── contracts.py
├── ids.py
├── progress.py
├── validation.py
├── map_build.py
├── art_request.py
├── images.py
└── pack.py
```

---

## Task 1: 契约和 schema

**Files:**
- Create: `asset_general_system/specs/scene_map_spec.schema.json`
- Create: `asset_general_system/specs/scene_style_profile.schema.json`
- Create: `asset_general_system/specs/scene_entities.schema.json`
- Create: `asset_general_system/specs/scene_prompts.schema.json`
- Create: `asset_general_system/specs/art_manifest.schema.json`
- Create: `asset_general_system/specs/progress.schema.json`
- Create: `asset_general_system/style_defaults.json`
- Create: `asset_general_system/generator/scene/constants.py`
- Create: `asset_general_system/generator/scene/validation.py`
- Create: `asset_general_system/tests/test_scene_validate.py`

- [ ] **Step 1: 定义 category 常量**

在 `constants.py` 定义：

```python
SCENE_OBJECT_CATEGORIES = {
    "building",
    "large_prop",
    "small_prop",
    "thin_prop",
    "npc",
    "facade_overlay",
    "text_sign",
}

CATEGORY_DEFAULTS = {
    "building": {"footprint": (8, 5), "blocking": True, "source_canvas": (256, 160), "anchor": "bottom_center"},
    "large_prop": {"footprint": (2, 1), "blocking": True, "source_canvas": (96, 64), "anchor": "center"},
    "small_prop": {"footprint": (1, 1), "blocking": False, "source_canvas": (64, 64), "anchor": "center"},
    "thin_prop": {"footprint": (1, 2), "blocking": True, "source_canvas": (64, 96), "anchor": "bottom_center"},
    "npc": {"footprint": (1, 1), "blocking": False, "source_canvas": (64, 64), "anchor": "center"},
    "facade_overlay": {"footprint": (3, 1), "blocking": False, "source_canvas": (96, 64), "anchor": "center"},
    "text_sign": {"footprint": (2, 1), "blocking": False, "source_canvas": (96, 64), "anchor": "center"},
}
```

- [ ] **Step 2: 新增 scene_map_spec schema**

基于 `rpg_map_spec.schema.json` 增加 scene 专属约束：

- `objects[].type` enum 为 7 种 category。
- `properties.object_key` 必填，格式 `^[a-z][a-z0-9_]*$`。
- `properties.footprint` 可选，格式 `^[1-9][0-9]*x[1-9][0-9]*$`。
- `properties.source_canvas` 可选，格式为两个正整数数组。
- `properties.facing` 可选，enum 为 `east_west` / `north_south` / `faces_south` / `faces_player`。
- `facade_overlay` / `text_sign` 要求 `properties.attached_to`。
- `text_sign.properties.text` 只作为 metadata。

- [ ] **Step 3: 新增其他 5 个 schema**

最小字段要求：

- `scene_style_profile.schema.json`: `version`, `view`, `art_style`, `forbidden`.
- `scene_entities.schema.json`: `version`, `scene`, `entities[]`, `target_id`, `category`, `footprint`, `source_canvas`.
- `scene_prompts.schema.json`: `version`, `prompts[]`, `target_id`, `body`, `negative`.
- `art_manifest.schema.json`: `version`, `scene`, `mappings[]`, `target_id`, `sprite_path`, `final_sprite_path`, `footprint`, `anchor`, `category`, `status`.
- `progress.schema.json`: `current_stage`, `completed`, `last_updated`, `errors`.

- [ ] **Step 4: 实现 scene-validate 核心函数**

在 `validation.py` 提供：

```python
def validate_scene_file(scene_dir: Path, stage: str | None = None) -> list[SceneValidationError]:
    ...
```

校验层次：

- JSON schema 校验。
- `target_id` 跨文件校验。
- `attached_to` 指向 `regions[].id` 或生成后的 object id。
- `text_sign` prompt 不允许要求可读文字。

- [ ] **Step 5: 写测试**

覆盖：

- 未知 category 报错。
- `properties.object_key` 缺失报错。
- `properties.footprint` 非 `"WxH"` 报错。
- `source_canvas` 非 `[W, H]` 报错。
- `text_sign` 缺少 `attached_to` 报错。
- 合法最小 `map_spec.json` 通过。

- [ ] **Step 6: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_validate.py
```

---

## Task 2: scene 目录和进度管理

**Files:**
- Create: `asset_general_system/generator/scene/__init__.py`
- Create: `asset_general_system/generator/scene/contracts.py`
- Create: `asset_general_system/generator/scene/progress.py`
- Create: `asset_general_system/tests/test_scene_progress.py`

- [ ] **Step 1: 定义 scene 文件路径约定**

在 `contracts.py` 定义 `ScenePaths`：

- `scene.md`
- `map_spec.json`
- `map_data.json`
- `art_request.json`
- `preview.png`
- `style_profile.json`
- `entities.json`
- `prompts.json`
- `images/`
- `art_manifest.json`
- `progress.json`
- `error.log`
- `final/`

- [ ] **Step 2: 实现 progress 写入**

在 `progress.py` 提供：

- `load_progress(scene_dir)`
- `mark_completed(scene_dir, stage)`
- `mark_in_progress(scene_dir, stage, total=None, current_item=None)`
- `record_error(scene_dir, stage, item, message)`

要求：

- 写入 `progress.json` 后立即通过 `progress.schema.json` 校验。
- 错误同时追加到 `error.log`。
- `last_updated` 使用 ISO 时间字符串。

- [ ] **Step 3: 测试**

覆盖：

- 空目录首次写入 progress。
- completed 去重。
- 单项错误同时出现在 `progress.json.errors[]` 和 `error.log`。

- [ ] **Step 4: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_progress.py
```

---

## Task 3: category-based map placement

**Files:**
- Modify: `asset_general_system/generator/models/tilemap_data.py`
- Modify: `asset_general_system/generator/map/generator.py`
- Create: `asset_general_system/generator/scene/ids.py`
- Create: `asset_general_system/generator/scene/map_build.py`
- Create: `asset_general_system/tests/test_scene_map_build.py`

- [ ] **Step 1: 扩展 ObjectData**

`ObjectData` 继续兼容旧字段，新增或规范化：

- `sprite_ref`
- `sprite_path`
- `properties.object_key`
- `properties.source_canvas`
- `properties.attached_to`
- `properties.text`

优先保持字段在 `properties` 中透传，避免破坏旧测试。

- [ ] **Step 2: 实现 ID 生成**

在 `ids.py` 中实现：

```python
def make_object_ids(objects: list[ObjectSpec]) -> dict[int, list[str]]:
    ...
```

规则：

- 使用 `properties.object_key`。
- 多实例生成 `{object_key}_{index:02d}`。
- 不从中文 `display_name` 临时 slug。

- [ ] **Step 3: 实现解析函数**

在 `map_build.py` 或 `generator.py` 中提供：

- `parse_footprint(properties, category, facing) -> tuple[int, int]`
- `parse_blocking(properties, category) -> bool`
- `parse_source_canvas(properties, category, footprint, tile_size) -> tuple[int, int]`
- `parse_anchor(category) -> str`
- `parse_placement(object_spec, category) -> str`

- [ ] **Step 4: 重构 MapGenerator 新入口**

保留 legacy school 分支可运行，但新增 scene category 路径：

- 当 `spec.objects[].type` 全部属于 7 种 category 时，走 category-based placement。
- 不读取 `SCHOOL_OBJECT_META` 作为新路径放置入口。
- 每个 category 至少有一个 placer：
  - `BuildingPlacer`
  - `LargePropPlacer`
  - `SmallPropPlacer`
  - `ThinPropPlacer`
  - `NpcPlacer`
  - `FacadeOverlayPlacer`
  - `TextSignPlacer`

- [ ] **Step 5: 实现 attached placement**

`FacadeOverlayPlacer` / `TextSignPlacer`：

- 必须读取 `properties.attached_to`。
- 优先贴到 region 正面边缘。
- 引用 object id 时贴到该 object 的 bounds。
- 不阻断建筑入口。
- 不能退化成普通随机放置。

- [ ] **Step 6: 生成 map_data / preview / art_request**

`scene-map-build` 核心函数：

```python
def build_scene_map(scene_dir: Path, force: bool = False) -> None:
    ...
```

输出：

- `map_data.json`
- `art_request.json`
- `preview.png`
- `progress.json`

- [ ] **Step 7: 测试**

覆盖：

- 7 种 category 都能放置。
- `ObjectData.id` 使用 `object_key_01`。
- `properties.footprint` 优先于 category 默认。
- `source_canvas` 透传到 art_request。
- `text_sign` 基于 `attached_to` 放置。
- 旧 `RulePromptParser` 测试不被破坏。

- [ ] **Step 8: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_map_build.py tests/test_map_generator.py tests/test_rule_parser.py
```

---

## Task 4: art_request 契约重建

**Files:**
- Modify: `asset_general_system/generate.py`
- Create: `asset_general_system/generator/scene/art_request.py`
- Create: `asset_general_system/tests/test_scene_art_request.py`

- [ ] **Step 1: 拆出 art_request 构建**

从 `generate.py` 中现有 `build_map_art_request()` 拆到 `generator/scene/art_request.py`，保留旧函数作为 wrapper 兼容。

- [ ] **Step 2: 修改 category 来源**

新函数要求：

- `category = map_spec.objects[].type` 或 `ObjectData.properties["category"]`。
- 不调用 `infer_map_art_category()`。
- `anchor` 由 category 确定性生成。

- [ ] **Step 3: 字段要求**

`art_request.objects[]` 必须包含：

- `id`
- `type`
- `display_name`
- `object_key`
- `category`
- `x`, `y`
- `footprint`
- `pixel_bounds`
- `runtime_size`
- `source_canvas`
- `placement_zone`
- `facing`
- `anchor`
- `blocking`
- `attached_to`（如有）
- `text`（如有）
- `source_clause`
- `properties`

- [ ] **Step 4: 测试**

覆盖：

- category 直接来自 `map_spec.objects[].type`。
- `footprint` 是数组，不是 `"WxH"`。
- `source_canvas` 是数组。
- `text_sign.text` 透传但不进入 prompt 图片要求。

- [ ] **Step 5: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_art_request.py
```

---

## Task 5: CLI 子命令接入

**Files:**
- Modify: `asset_general_system/generate.py`
- Create: `asset_general_system/tests/test_scene_cli.py`

- [ ] **Step 1: 增加子命令**

在现有 argparse 下新增：

```text
python generate.py scene-map-build <scene_dir> [--force]
python generate.py scene-images <scene_dir> [--gemini] [--force] [--variants N] [--target TARGET_ID]
python generate.py scene-pack <scene_dir> [--force] [--resource-base RES_PATH]
python generate.py scene-status <scene_dir>
python generate.py scene-validate <scene_dir> [--stage STAGE]
```

- [ ] **Step 2: scene-map-build 不调用 RulePromptParser**

实现时直接读取 `scene_dir/map_spec.json`，用 `RPGMapSpec` / `scene_map_spec.schema.json` 校验后调用 `MapGenerator.generate()`。

- [ ] **Step 3: 跳过和 force 规则**

- 输出文件存在且未指定 `--force` 时跳过当前阶段。
- 指定 `--force` 时只覆盖当前阶段产物，不清理用户手写的 `scene.md`、`map_spec.json`、`style_profile.json` 等输入。

- [ ] **Step 4: 测试**

覆盖：

- `scene-validate` 成功 / 失败退出码。
- `scene-map-build` 不 import 或调用 `RulePromptParser.parse()`。
- `scene-images --target` 参数能解析。

- [ ] **Step 5: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_cli.py
```

---

## Task 6: Claude 阶段文件约束

**Files:**
- Create: `asset_general_system/examples/scenes/dingbu_primary_school_1998/scene.md`
- Create: `asset_general_system/examples/scenes/dingbu_primary_school_1998/map_spec.example.json`
- Create: `asset_general_system/examples/scenes/dingbu_primary_school_1998/style_profile.example.json`
- Create: `asset_general_system/examples/scenes/dingbu_primary_school_1998/entities.example.json`
- Create: `asset_general_system/examples/scenes/dingbu_primary_school_1998/prompts.example.json`
- Create: `asset_general_system/tests/test_scene_contract_examples.py`

- [ ] **Step 1: 写最小真实示例**

示例必须包含：

- `large_prop`: `ping_pong_table`
- `thin_prop`: `basketball_hoop`
- `text_sign`: `notice_board`
- `text_sign.properties.attached_to`
- `text_sign.properties.text`
- 每个对象的 `source_canvas`

- [ ] **Step 2: style 示例**

`style_profile.example.json` 包含：

- `view`
- `art_style`
- `palette_mood`
- `forbidden`，其中必须包含 `text_in_image`, `watermark`, `white_background`, `scene_background`

- [ ] **Step 3: entities 示例**

`entities.example.json` 必须从 `art_request` 透传：

- `target_id`
- `object_key`
- `category`
- `footprint`
- `source_canvas`
- `attached_to`（如有）
- `text`（如有）

- [ ] **Step 4: prompts 示例**

`text_sign` prompt：

- body 写空白牌面 / 空白纸张。
- negative 包含 `readable text`, `Chinese characters`, `letters`。

- [ ] **Step 5: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_contract_examples.py
python generate.py scene-validate examples/scenes/dingbu_primary_school_1998 --stage spec
```

---

## Task 7: scene-images

**Files:**
- Modify: `asset_general_system/generator/assets/object_generator.py`
- Create: `asset_general_system/generator/scene/images.py`
- Create: `asset_general_system/tests/test_scene_images.py`

- [ ] **Step 1: 目标命名机制**

`ObjectGenerator` 或 wrapper 必须支持指定输出 basename：

- PNG: `images/{target_id}.png`
- JSON: `images/{target_id}.json`

不要沿用 `object_type + seed/timestamp` 作为最终文件名。

- [ ] **Step 2: source_canvas**

`scene-images` 读取 `art_request.objects[].source_canvas` 作为生成画布尺寸；`footprint` 只用于 prompt 的占格语义，不直接决定 PNG 尺寸。

- [ ] **Step 3: prompt wrapper**

Python wrapper 追加：

- source canvas 尺寸
- pixel grid
- anchor
- orientation
- transparent background
- no scene background

`text_sign` 额外追加：

- no readable text
- no Chinese characters
- no letters
- blank sign surface only

- [ ] **Step 4: --target**

`--target TARGET_ID` 只处理一个目标：

- target 不存在时报错。
- target 已有图片且无 `--force` 时跳过。
- target 已有图片且有 `--force` 时覆盖。

- [ ] **Step 5: variants**

`--variants N` 可生成候选，但最终稳定文件仍为 `{target_id}.png`。若暂不做选择 UI，v1 可保留第一个成功结果，并把候选参数写入 `{target_id}.json`。

- [ ] **Step 6: 测试**

使用 mock Gemini / mock ObjectGenerator：

- 缺失图片断点续跑。
- `--target` 只生成指定 target。
- `source_canvas` 传给 generator。
- `text_sign` prompt 不包含真实文字。

- [ ] **Step 7: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_images.py
```

---

## Task 8: scene-pack 和 Godot Sprite2D

**Files:**
- Modify: `asset_general_system/generator/export/godot_exporter.py`
- Create: `asset_general_system/generator/scene/pack.py`
- Create: `asset_general_system/tests/test_scene_pack.py`

- [ ] **Step 1: 生成 art_manifest**

`scene-pack` 生成 `art_manifest.json`，不要由 Claude 写。

`mappings[]` 包含：

- `target_id`
- `sprite_path`
- `final_sprite_path`
- `footprint`
- `anchor`
- `category`
- `source_canvas`
- `status`

- [ ] **Step 2: 拷贝 sprites**

从：

```text
images/{target_id}.png
```

复制到：

```text
final/sprites/{target_id}.png
```

- [ ] **Step 3: 写回 map_data_applied**

对每个成功 mapping：

- `object.sprite_ref = target_id`
- `object.sprite_path = "sprites/{target_id}.png"`
- 不把 `sprite_path` 当作 `object.properties["sprite_path"]` 主字段。

- [ ] **Step 4: Godot 导出 Sprite2D**

扩展 `GodotExporter`：

- 为每个有 `sprite_path` 的 object 创建 `Node2D + Sprite2D`。
- 为 PNG 写入 `Texture2D` ext_resource。
- 按 `anchor` 修正 Sprite2D offset / position。
- object 位置、尺寸与 `footprint` 和 tile size 对齐。

- [ ] **Step 5: text_sign 文本层**

当 object 是 `text_sign` 且存在 `text`：

- 生成独立 `Label` 或 metadata。
- 文字不依赖 PNG 烘焙。
- label 层级在 text_sign sprite 之上。

- [ ] **Step 6: 渲染层级**

建议 order：

```text
tilemap -> buildings -> props -> facade_overlay/text_sign sprites -> npcs -> text labels
```

v1 可用节点顺序和 `z_index` 同时保证。

- [ ] **Step 7: 测试**

覆盖：

- `art_manifest.json` schema 通过。
- `map_data_applied.json` 写顶层 `sprite_path`。
- `.tscn` 包含 `Sprite2D` 和 `Texture2D` ext_resource。
- `text_sign` 包含独立文本层或 metadata。

- [ ] **Step 8: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_scene_pack.py
```

---

## Task 9: scene-status 和端到端 mock

**Files:**
- Modify: `asset_general_system/generate.py`
- Create: `asset_general_system/tests/test_full_scene_pipeline_mock.py`

- [ ] **Step 1: scene-status**

读取：

- `progress.json`
- `error.log`

输出：

- scene id
- current stage
- completed stages
- in-progress item
- errors

- [ ] **Step 2: all-stage mock 测试**

用固定 fixture 和 mock image generator 跑：

```text
scene-validate -> scene-map-build -> scene-images -> scene-pack -> scene-status
```

Claude 阶段文件用 fixture 代替。

- [ ] **Step 3: 断点续跑测试**

覆盖：

- 已完成 `scene-map-build` 后再跑不会覆盖产物。
- `scene-images` 对已有 PNG 默认跳过。
- `--force` 只覆盖指定阶段。

- [ ] **Step 4: 验收**

```powershell
cd asset_general_system
python -m pytest tests/test_full_scene_pipeline_mock.py
```

---

## Task 10: Claude skill

**Files:**
- Create: `.claude/skills/linsen-asset-scene/SKILL.md`
- Create: `.claude/skills/linsen-asset-scene/examples/minimal-map-spec.json`
- Create: `.claude/skills/linsen-asset-scene/examples/minimal-style-profile.json`
- Create: `.claude/skills/linsen-asset-scene/examples/minimal-entities.json`
- Create: `.claude/skills/linsen-asset-scene/examples/minimal-prompts.json`

- [ ] **Step 1: skill frontmatter**

参数：

- `title`
- `stage`
- `review-all`
- `force`
- `variants`
- `target`

- [ ] **Step 2: stage state machine**

实现流程：

1. 检查 `scene_dir` 和 `scene.md`
2. `spec`: Claude 写 `map_spec.json`
3. 调用 `python generate.py scene-validate <scene_dir> --stage spec`
4. `map`: 调用 `scene-map-build`
5. `style`: Claude 写 `style_profile.json`
6. `entities`: Claude 写 `entities.json`
7. `prompts`: Claude 写 `prompts.json`
8. `images`: 调用 `scene-images`
9. `pack`: 调用 `scene-pack`
10. `status`: 调用 `scene-status`

- [ ] **Step 3: spec 生成规则写入 skill**

必须强调：

- `objects[].type` 是 category，不是具体物品名。
- 具体物品用 `properties.object_key`、`label`、`properties.display_name`。
- `properties.footprint` 只能是 `"WxH"`。
- `properties.source_canvas` 是 `[W, H]`。
- `facade_overlay` / `text_sign` 必须写 `attached_to`。
- `text_sign` 的真实文字写 `properties.text`，不能要求 PNG 生成可读文字。

- [ ] **Step 4: review-all**

`--review-all` 在以下阶段后暂停：

- spec
- style
- entities
- prompts

Python 阶段不暂停，只报告结果。

- [ ] **Step 5: 验收**

人工检查：

- 运行 skill 的 `--stage spec` 能生成符合 schema 的 `map_spec.json`。
- `--stage images --target notice_board_01 --force` 能透传 target。

---

## Task 11: 文档和开发说明

**Files:**
- Modify: `asset_general_system/QUICKSTART.md`
- Modify: `asset_general_system/docs/USAGE.md`
- Create: `asset_general_system/docs/linsen_asset_scene_pipeline.md`

- [ ] **Step 1: 写快速使用说明**

包含：

```powershell
python generate.py scene-validate asset_general_system/scenes/dingbu_primary_school_1998 --stage spec
python generate.py scene-map-build asset_general_system/scenes/dingbu_primary_school_1998
python generate.py scene-images asset_general_system/scenes/dingbu_primary_school_1998 --gemini
python generate.py scene-images asset_general_system/scenes/dingbu_primary_school_1998 --target notice_board_01 --force
python generate.py scene-pack asset_general_system/scenes/dingbu_primary_school_1998
python generate.py scene-status asset_general_system/scenes/dingbu_primary_school_1998
```

- [ ] **Step 2: 写字段解释**

重点解释：

- `type` 是 category。
- `object_key` 是具体物品身份。
- `footprint` 与 `source_canvas` 的区别。
- `attached_to` 的引用规则。
- `text_sign.text` 和 PNG 文字分离。

- [ ] **Step 3: 验收**

文档中的命令必须和 `generate.py --help` 输出一致。

---

## Overall Verification

全部 task 完成后运行：

```powershell
cd asset_general_system
python -m pytest tests/test_scene_validate.py tests/test_scene_progress.py tests/test_scene_map_build.py tests/test_scene_art_request.py tests/test_scene_cli.py tests/test_scene_contract_examples.py tests/test_scene_images.py tests/test_scene_pack.py tests/test_full_scene_pipeline_mock.py
python generate.py scene-validate examples/scenes/dingbu_primary_school_1998 --stage spec
python generate.py scene-map-build examples/scenes/dingbu_primary_school_1998 --force
python generate.py scene-images examples/scenes/dingbu_primary_school_1998 --target notice_board_01 --force
python generate.py scene-pack examples/scenes/dingbu_primary_school_1998 --force
python generate.py scene-status examples/scenes/dingbu_primary_school_1998
```

如果本地没有 Gemini 配置，`scene-images` 端到端验收使用 mock generator；真实 Gemini 只做人工 smoke test。

---

## Non-Goals

- 不删除 legacy `RulePromptParser`。
- 不改旧 `generate.py --type map` 行为，除非为兼容测试做最小修复。
- 不实现图片质量自动 gate。
- 不做多场景批处理。
- 不做 tile atlas 自动替换。

---

## Done Definition

- [ ] 6 个 schema 全部存在并被测试覆盖。
- [ ] `scene-map-build` 不调用 `RulePromptParser.parse()`。
- [ ] `objects[].type` 使用 7 种 category enum。
- [ ] `ObjectData.id` / `target_id` 使用 `object_key_01` 稳定命名。
- [ ] `source_canvas` 从 `map_spec` 透传到 `art_request`、`entities/prompts/images` 和 `art_manifest`。
- [ ] `facade_overlay` / `text_sign` 的 `attached_to` 通过跨文件校验。
- [ ] `text_sign` 的可读文字不烘焙进 PNG。
- [ ] `scene-images --target TARGET_ID --force` 可单素材重生。
- [ ] `scene-pack` 生成 `Sprite2D`，不是只写 metadata。
- [ ] `final/scene.tscn` 在 Godot 中能看到 object sprites。
- [ ] mock 端到端测试通过。

---

**END OF PLAN**
