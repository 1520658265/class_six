<<<<<<< HEAD
# ADR-0002: Autoload Contract（注册清单与加载顺序）

## Status

Accepted

## Date

2026-05-31

## Last Verified

2026-05-31

## Decision Makers

- 元生项目作者会话（user）
- design-review Round-2 godot-specialist 提出（Round-2 review log §I.2）
- creative-director synthesis（Round-2）裁定移到独立 ADR
- 本 ADR 由 architecture-decision skill 在 ADR-0001 写完后顺序起草

## Summary

冻结《元生的六年级》全部 9 个 autoload 单例的注册清单与加载顺序，确保 `GlobalState._ready()` 在所有依赖它的 autoload（SaveManager / SceneRouter / Dialogue / UIRoot 等）`_ready()` 之前完成。Godot 4.6 autoload 按 `project.godot` `[autoload]` 节的**声明顺序（top-to-bottom）**初始化，**不是字母序**——本 ADR 锁定该声明顺序。
=======
# ADR-0002: Autoload Contract (Registration + Load Order)

## Status

Proposed

## Date

2026-06-01
>>>>>>> fdd79b53c10f3ec1bb0e1598c089f6cceaed14f5

## Engine Compatibility

| Field | Value |
|-------|-------|
<<<<<<< HEAD
| **Engine** | Godot 4.6 |
| **Domain** | Core / Scripting（autoload registration） |
| **Knowledge Risk** | HIGH — Godot 4.6 是 post-LLM-cutoff |
| **References Consulted** | Godot 4.x docs `tutorials/scripting/singletons_autoload.md`（Round-2 已 Web 复核：autoload 按声明顺序 top-to-bottom 初始化）；stat-system GDD §I.1 / §I.2；本仓库 `project.godot` 当前 `[autoload]` 节 |
| **Post-Cutoff APIs Used** | None — autoload 注册机制全版本一致 |
| **Verification Required** | 项目能在 Godot 4.6 编辑器内 launch 不报 `Identifier 'GlobalState' not declared`；GlobalState `_validate_configs` 正常通过；UIRoot `_ready` 时 `GlobalState.chapter_changed.connect(...)` 不报 nil reference |

> **Note**: Knowledge Risk 标 HIGH 因 4.6 是 post-cutoff，但 autoload 注册机制本身在 Godot 4.0+ 全版本稳定，**不是**新特性。LLM 误判过 autoload 按字母序初始化（Round-2 godot-specialist 提出，已通过官方文档复核为错误）——本 ADR 锁住正确做法，避免后续误判。
=======
| **Engine** | Godot 4.6 (pinned 2026-02-12) |
| **Domain** | Core / Scripting (Autoload registration + initialization order) |
| **Knowledge Risk** | MEDIUM — Autoload 顺序在 4.x 历来是 `project.godot [autoload]` 节的声明顺序（top-to-bottom），但 LLM 训练数据里常见误导（"按字母序"或"按依赖图"），必须以官方文档为准 |
| **References Consulted** | `docs/engine-reference/godot/VERSION.md`；Godot 官方文档 `tutorials/scripting/singletons_autoload.md`：*"The order of these entries can be adjusted, and they are processed top-to-bottom in the global scene tree"* |
| **Post-Cutoff APIs Used** | 无（autoload 机制本身在 4.0 已稳定） |
| **Verification Required** | (a) 项目能在 Godot 4.6 编辑器 launch 不报"Identifier 'GlobalState' not declared"；(b) 把 GlobalState 临时挪到 [autoload] 节末尾时，SaveManager._ready 内 GlobalState.from_dict 仍能正常调用（验证声明顺序是真的影响 _ready 调度） |

### Autoload 顺序的官方文档复核

stat-system GDD §I.2 已经做过这次复核（godot-specialist Round-2 评审中曾误声称"字母序"，被官方文档否定）。本 ADR 引用该结论，不重复争论：**Godot 4.x autoload 按 [autoload] 节的声明顺序（top-to-bottom）初始化，与 autoload 名字字母序无关。**
>>>>>>> fdd79b53c10f3ec1bb0e1598c089f6cceaed14f5

## ADR Dependencies

| Field | Value |
|-------|-------|
<<<<<<< HEAD
| **Depends On** | None（与 ADR-0001 同 stat-system §I 主题，ADR 编号上相邻；但本 ADR 不依赖 ADR-0001 内容，可独立 Accepted） |
| **Enables** | ADR-0001 实装漂移修复落地（global_state.gd 改完后必须本 ADR 注册才能 launch）；12+ 下游 GDD（任何一个 autoload 调用都依赖本 ADR） |
| **Blocks** | 项目能在 Godot 4.6 编辑器 launch；任何 `GlobalState.foo()` / `Dialogue.play(...)` / `SaveManager.save(...)` 调用 |
| **Ordering Note** | ADR-0001 修改 `global_state.gd` 实装侧契约 → 本 ADR 修改 `project.godot` 注册 → 项目可 launch。两步必须按这个顺序（先 ADR-0001 改代码再 ADR-0002 注册），否则注册成功后启动时 `_validate_configs` 会立刻 assert。 |
=======
| **Depends On** | ADR-0001-stat-system-contract（必须同时 Accepted；本 ADR 的载入顺序假设 GlobalState 接口与 §10 启动 config 校验已落地） |
| **Enables** | 所有下游 GDD（Save/Load、Dialogue、Cutscene Runner、NPC、Combat 等）— 它们的 `_ready()` 调用 GlobalState 在本 ADR 落地前都会立刻 parse error |
| **Blocks** | Demo 切片所有 stories — 项目当前不能运行；本 ADR 是项目能 launch 的前置 |
| **Ordering Note** | 本 ADR 与 ADR-0001 紧密耦合：ADR-0001 锁"接口契约"，ADR-0002 锁"注册 + 装配顺序"。Migration 阶段两份 ADR 落地必须同 PR（Editor 一旦在 ADR-0001 实装的同时未注册 GlobalState autoload，整个项目会 break） |
>>>>>>> fdd79b53c10f3ec1bb0e1598c089f6cceaed14f5

## Context

### Problem Statement

<<<<<<< HEAD
仓库内已落盘 9 个 autoload 单例脚本（`scripts/autoload/*.gd`），其中 12+ 个调用点（包括 ADR-0001 锁定的 `GlobalState`）已经按 `Foo.bar()` 形式直接调用。但 `project.godot` 的 `[autoload]` 节当前**只**声明了 4 个：
=======
`project.godot` 的 `[autoload]` 节当前只声明了 4 个 autoload（Sprites / Portraits / VFX / Atlas）：
>>>>>>> fdd79b53c10f3ec1bb0e1598c089f6cceaed14f5

```ini
[autoload]
Sprites="*res://scripts/autoload/sprites.gd"
Portraits="*res://scripts/autoload/portraits.gd"
VFX="*res://scripts/autoload/vfx.gd"
Atlas="*res://scripts/autoload/atlas.gd"
```

<<<<<<< HEAD
`GlobalState / SaveManager / SceneRouter / Dialogue / UIRoot` 这 5 个未注册——任何尝试运行的脚本都会立刻报 `Identifier 'GlobalState' not declared`（GDScript parse 阶段）。stat-system GDD §I.1 已经把这件事标为 BLOCKING。

加上 stat-system §F.5 的 load-path UI 契约暗中假设 `GlobalState._ready()` 在 `SaveManager._ready()` 之前完成；UIRoot `_ready` 第一时间调 `GlobalState.chapter_changed.connect(...)`——如果加载顺序反过来，UIRoot 就会读到 nil reference。

不立即决定的成本：当前项目没法 launch、无法跑 H.1–H.20 AC、12+ 下游 GDD 都不能进入 `/dev-story`。

### Current State

`project.godot` `[autoload]` 节只有 4 个 entry。仓库 `scripts/autoload/` 下已落盘的 autoload 脚本：

| 文件 | 当前状态 |
|---|---|
| `global_state.gd` | 落盘，未注册（ADR-0001 修改实装侧后注册）|
| `save_manager.gd` | 落盘，未注册 |
| `scene_router.gd` | 落盘，未注册 |
| `dialogue.gd` | 落盘，未注册 |
| `ui_root.gd` | 落盘，未注册（且 `_ready` 已经引用 GlobalState） |
| `sprites.gd` | 已注册 |
| `portraits.gd` | 已注册 |
| `atlas.gd` | 已注册 |
| `vfx.gd` | 已注册 |
| `asset_ids.gd` | 落盘，**不需要** autoload（是 const 资源 ID 表）|

10 个文件中：4 已注册、5 待注册、1 不需要注册。

### Constraints

- autoload 名必须是 `GlobalState`（其它 12+ 调用点已经 hardcode）
- 路径必须是 `res://scripts/autoload/global_state.gd`（GDD §I.1 锁定）
- 不能引入新的 autoload 中间件 / 包装层（项目规模小，不值得）
- Godot 4.6 autoload 按 `[autoload]` 节**声明顺序（top-to-bottom）**初始化，不能依赖名字字母序（Round-2 复核确认）
- `asset_ids.gd` 不应注册为 autoload（它是 const 资源 ID 表，注册会浪费一个 autoload slot 且引入 ambiguity）

### Requirements

- **R1 全部已落盘的 5 个 autoload 注册到 `project.godot`**：GlobalState / SaveManager / SceneRouter / Dialogue / UIRoot
- **R2 加载顺序固定**：GlobalState 必须在 SaveManager / SceneRouter / Dialogue / UIRoot 之前；具体顺序见 §Decision
- **R3 注册名锁死**：与 12+ 调用点的 identifier 一致（`GlobalState` / `SaveManager` / `SceneRouter` / `Dialogue` / `UIRoot`）
- **R4 启动可运行**：执行后项目能在 Godot 4.6 编辑器 launch 不报 parse / nil ref / assert（依赖 ADR-0001 实装漂移修复完成）
- **R5 不引入字母序前缀**：godot-specialist Round-2 曾建议用 `AGlobalState` 强制顺序——已经过文档复核为不必要，明确拒绝
- **R6 后续扩展锁顺序**：未来新加 autoload 必须在本 ADR 修订后再加（避免破坏依赖链）

## Decision

把 `project.godot` `[autoload]` 节扩展为以下 9 个 entry，**严格按这个声明顺序排列**（Godot top-to-bottom 顺序就是初始化顺序）：

```ini
[autoload]

GlobalState="*res://scripts/autoload/global_state.gd"
Sprites="*res://scripts/autoload/sprites.gd"
Portraits="*res://scripts/autoload/portraits.gd"
VFX="*res://scripts/autoload/vfx.gd"
Atlas="*res://scripts/autoload/atlas.gd"
=======
但 `scripts/autoload/` 目录实际有 **9 个真 autoload 候选 .gd**（额外 5 个未注册）：

- `global_state.gd` — Stat System 容器（ADR-0001 锁定）
- `save_manager.gd` — 存档读写
- `scene_router.gd` — 场景切换
- `dialogue.gd` — JSON 对白驱动
- `ui_root.gd` — 全局 UI 根（持有 DialogueBox / StatPanel / ChapterTitle / EraMarkerToast）

外加 1 个 **不是 autoload** 的伪兄弟：
- `asset_ids.gd` — `class_name AssetIds extends RefCounted`，静态常量集，按 `AssetIds.Char.YUANSHENG` 访问，不需要注册到 [autoload]

后果：

1. **Parse error 当场触发**：仓库内已有 12+ 个 `.gd` 文件按 `GlobalState.foo()` / `SaveManager.foo()` / `Dialogue.foo()` / `SceneRouter.foo()` / `UIRoot.foo()` 调用，但这些 identifier 在 GDScript parse 期未声明，整个项目当前无法 launch。
2. **加载顺序未冻结**：即使补全注册，若 SaveManager 排在 GlobalState 之前，SaveManager._ready 内若调 `GlobalState.from_dict(...)` 会触发 KeyError（GlobalState 的 `_stats / _vars / _affinity` 还没初始化）。
3. **未来添加新 autoload 无章可循**：每个新 PR 都要重新协商"放哪个位置"。

### Constraints

- **autoload 名必须是 `GlobalState / SaveManager / SceneRouter / Dialogue / UIRoot`**（与现有 12+ 个调用点一致；改名 = 全仓搜索 + 替换）。
- **项目必须能在 Godot 4.6 编辑器中 launch**（这是 demo 切片成立的最低门槛）。
- **加载顺序必须是确定性的**（不依赖文件系统时序、不依赖名字字母序）。
- **未来扩展（如 AudioBus）**追加在末尾即可，不应改变现有顺序。

### Requirements

- 9 个真 autoload 全部注册到 `[autoload]` 节
- 加载顺序在 ADR 中明确锁定，每个 autoload 注明其依赖关系（"为什么必须在 X 之后"）
- AssetIds 明确**不**进 [autoload]，由本 ADR 显式声明，避免后续 PR 误注册
- 顺序要让 stat-system GDD §F.5 的 "load-path UI 契约"（`reset/from_dict` 静默 + `SaveManager.load_finished` 通知）成立

## Decision

按 **by-feature 装配顺序** 锁定 9 个 autoload 在 `project.godot [autoload]` 节的声明序：

```ini
[autoload]
GlobalState="*res://scripts/autoload/global_state.gd"
Sprites="*res://scripts/autoload/sprites.gd"
Portraits="*res://scripts/autoload/portraits.gd"
Atlas="*res://scripts/autoload/atlas.gd"
VFX="*res://scripts/autoload/vfx.gd"
>>>>>>> fdd79b53c10f3ec1bb0e1598c089f6cceaed14f5
SaveManager="*res://scripts/autoload/save_manager.gd"
SceneRouter="*res://scripts/autoload/scene_router.gd"
Dialogue="*res://scripts/autoload/dialogue.gd"
UIRoot="*res://scripts/autoload/ui_root.gd"
```

<<<<<<< HEAD
`asset_ids.gd` **不**注册为 autoload（保持现状，作为 `const` 资源 ID 表 preload 使用）。

### Architecture

```
启动时序（Godot 4.6 按 [autoload] 节声明顺序，top-to-bottom）：

  [1] GlobalState._ready()
       ├─ _validate_configs(STATS_CONFIG, VARS_CONFIG, AFFINITY_CONFIG)
       │    └─ assert(false) on violation（ADR-0001 §9）
       └─ reset_to_initial()  →  6 集合到 init 值

  [2] Sprites._ready()    ─┐
  [3] Portraits._ready()   ├─ 资产 ID 表加载（无依赖、互不依赖）
  [4] VFX._ready()         │
  [5] Atlas._ready()      ─┘

  [6] SaveManager._ready()
       └─ DirAccess.make_dir_recursive_absolute(SAVE_DIR)
       （后续读档调用 GlobalState.from_dict — 此时 [1] 已完成 ✓）

  [7] SceneRouter._ready()
       （后续 change_scene 调用 GlobalState.set_chapter — 此时 [1] 已完成 ✓）

  [8] Dialogue._ready()
       （后续 play() 调用 GlobalState.get_stat / get_var — 此时 [1] 已完成 ✓）

  [9] UIRoot._ready()
       ├─ instantiate 4 个 CanvasLayer 子场景（dialogue_box / stat_panel / chapter_title / era_marker_toast）
       └─ GlobalState.chapter_changed.connect(_on_chapter_changed)
          GlobalState.era_marker_added.connect(_on_era_marker)
          （此时 [1] 已完成 ✓ — connect 不会读到 nil）

依赖关系：
  GlobalState ←── SaveManager（读 + 写）
  GlobalState ←── SceneRouter（间接，通过 set_chapter）
  GlobalState ←── Dialogue（读 condition）
  GlobalState ←── UIRoot（订阅 signal）
  Sprites/Portraits/VFX/Atlas ←── (无依赖，互不依赖)
  Dialogue ←── UIRoot（dialogue_box 通过 signal）
  SaveManager / SceneRouter ←── UIRoot（间接）

→ GlobalState 必须最前；UIRoot 必须最后。
→ Sprites/Portraits/VFX/Atlas 顺序无关，但放在 GlobalState 后、SaveManager 前，保持 4 个资产 autoload 紧邻。
→ SaveManager / SceneRouter / Dialogue 任意顺序均合法（它们彼此不依赖），但选 SaveManager → SceneRouter → Dialogue 作为约定，便于阅读。
```

### Key Interfaces

本 ADR 不引入新接口——只锁住已存在的 9 个 autoload identifier 与它们的注册路径。所有调用点形式：

```gdscript
GlobalState.change_stat("xuexi", +1)
SaveManager.save(0, scene_id, pos, facing)
SceneRouter.change_scene("classroom_2b", "from_door_left")
Dialogue.play("ch1/12_yuekao_ranking")
UIRoot.show_chapter_title("第一章 · 月考")
Sprites.get_animation_set("yuansheng")
Portraits.get_portrait("baoxianjin")
Atlas.get_tile_atlas("classroom_floor")
VFX.get_clip("dust_kick")
```

### Implementation Guidelines

由 godot-gdscript-specialist 在 ADR-0001 实装漂移修复合并后的同 PR 或紧邻 PR 中执行：

1. **打开 `project.godot`**，定位到 `[autoload]` 节
2. **完整替换**该节为 §Decision 列出的 9 行（不要在中间插入，避免顺序错乱）
3. **保存文件**
4. **本地启动 Godot 4.6 编辑器**：观察 Output 面板：
   - 不应有 "Could not autoload" 错误
   - 不应有 `Identifier 'GlobalState' not declared` 错误
   - GlobalState 的 `_validate_configs` 不应触发 assert（依赖 ADR-0001 已合并）
5. **最小冒烟**：在编辑器里 F5 启动主场景；UIRoot `_ready` 不报 nil；按 ESC 干净退出
6. **PR 标题**：`feat(autoload): register 5 missing autoloads + lock load order per ADR-0002`，引用本 ADR
7. **CI 确认**：`godot --headless --check-only --path .` 不报 parse error

**关于 `asset_ids.gd`**：保持现状（`const ASSET_IDS = {...}` 形式），由其他脚本 `const AssetIds = preload("res://scripts/autoload/asset_ids.gd")` 引用。后续如确实需要从 autoload 访问，单独写 ADR 修订，不在本 ADR 范围。

## Alternatives Considered

### Alternative 1: 用字母序前缀（如 `AGlobalState`）强制最早初始化

- **Description**：把 `GlobalState` 重命名为 `AGlobalState`，依赖"autoload 按字母序初始化"假设
- **Pros**：如果该假设成立，则不依赖声明顺序，更"防误改"
- **Cons**：godot-specialist Round-2 提出此方案后，**经官方文档复核（`tutorials/scripting/singletons_autoload.md`）该假设为错误**——Godot 4.x autoload 按 `[autoload]` 节**声明顺序（top-to-bottom）**初始化，与名字字母序无关；同时项目内 12+ 调用点已 hardcode `GlobalState`，重命名成本极高
- **Estimated Effort**：+3x（重命名 + 改 12+ 调用点）
- **Rejection Reason**：该方案基于错误的引擎行为假设；改名成本远高于直接锁声明顺序。已在 stat-system GDD §I.2 archive 复核结果。

### Alternative 2: 把 `asset_ids.gd` 也注册为 autoload

- **Description**：在 `[autoload]` 加一行 `AssetIds="*res://scripts/autoload/asset_ids.gd"`
- **Pros**：访问方式与其他 autoload 对齐（`AssetIds.YUANSHENG` vs `const AssetIds = preload(...); AssetIds.YUANSHENG`）
- **Cons**：`asset_ids.gd` 是纯 const 表，无 `_ready` / 状态 / 信号——注册成 autoload 会让它出现在 `/root/AssetIds`，被 SceneTree 视为 Node，浪费一个 instance + autoload slot；多数 const 表更适合 preload 而非 autoload
- **Estimated Effort**：相当
- **Rejection Reason**：const 表用 `preload` 是更地道的 GDScript 模式；autoload 应保留给"有状态 / 有 `_ready` / 提供信号"的单例。本 ADR 不为它额外注册，将来如有需要单独 ADR 处理。

### Alternative 3: 把 SaveManager / Dialogue 等都内嵌进 UIRoot

- **Description**：减少 autoload 数量，把 Save / Scene / Dialogue 都做成 UIRoot 的子节点
- **Pros**：autoload 数量从 9 降到 5
- **Cons**：违反"职责单一" / 按 GDD 切分系统的设计；SaveManager / SceneRouter / Dialogue 各自有独立的生命周期与对外接口；下游 GDD 已经按"autoload 调用"形式引用
- **Estimated Effort**：+5x（重构 5 个系统接口）
- **Rejection Reason**：autoload 数量不是问题；项目规模与系统切分对得上 9 个 autoload 的合理范围。
=======
`AssetIds` (`scripts/autoload/asset_ids.gd`) **不**注册 — 它是 `class_name AssetIds extends RefCounted` 的静态常量集，靠 `AssetIds.Char.YUANSHENG` 访问。

### Architecture Diagram

```
project.godot [autoload]  (top-to-bottom 初始化顺序)
─────────────────────────────────────────────────
1. GlobalState     ← Foundation（无依赖）
2. Sprites         ← 资源加载（无依赖）
3. Portraits       ← 资源加载（无依赖）
4. Atlas           ← 资源加载（无依赖）
5. VFX             ← 资源加载（无依赖）
6. SaveManager     ← 依赖 GlobalState（_ready 内可能 from_dict）
7. SceneRouter     ← 依赖 GlobalState（读 chapter）+ 资源（切场要 walk_frames）
8. Dialogue        ← 依赖 GlobalState（读 stat/var/affinity 评估 condition）+ Portraits
9. UIRoot          ← 依赖 GlobalState（订阅 stat_changed 给 StatPanel）+ Dialogue（DialogueBox）
─────────────────────────────────────────────────

伪兄弟（不在 [autoload]）：
   AssetIds  ← class_name AssetIds extends RefCounted（静态常量集）
```

### 顺序的依赖原因（逐项）

| # | Autoload | 必须在...之后 | 理由 |
|---|---|---|---|
| 1 | **GlobalState** | （无）| Foundation 层，零依赖，必须最先 _ready 让其它 autoload 在 _ready 中可读 |
| 2 | **Sprites** | （无）| 资源加载层，零业务依赖 |
| 3 | **Portraits** | （无）| 资源加载层 |
| 4 | **Atlas** | （无）| 资源加载层 |
| 5 | **VFX** | （无）| 资源加载层 |
| 6 | **SaveManager** | GlobalState | 任何 `load_slot()` 调用会触发 `GlobalState.from_dict(...)`，GlobalState 必须已 ready |
| 7 | **SceneRouter** | GlobalState, Sprites | 切场可能读 `GlobalState.get_chapter()`；NPC 资源从 Sprites 取 |
| 8 | **Dialogue** | GlobalState, Portraits | Dialogue 节点的 `condition` 字段读 stat/var/affinity；立绘从 Portraits 取 |
| 9 | **UIRoot** | GlobalState, Dialogue | UIRoot._ready 实例化 DialogueBox / StatPanel；StatPanel 订阅 GlobalState 的 stat_changed |

### Key Interfaces

本 ADR 不引入新代码接口 — 它**约束** `project.godot` `[autoload]` 节的内容形态：

1. **声明顺序**：必须严格按上述 9 行顺序排列。
2. **路径前缀**：`*res://scripts/autoload/<file>.gd`，前缀 `*` 表示该 autoload 是 Node 单例（非 GDScript class 静态访问）。
3. **不允许的 autoload**：`AssetIds` 不在该节，由本 ADR §"伪兄弟"显式声明。
4. **新增 autoload 流程**：未来添加（如 AudioBus、Localization）必须经新 ADR 修订本 ADR，并明确说明插入位置 + 依赖关系（默认追加到 9 之后）。

## Alternatives Considered

### Alternative 1: 按字母序排列

- **Description**：让 [autoload] 节按 autoload 名字母序：`Atlas / Dialogue / GlobalState / Portraits / SaveManager / SceneRouter / Sprites / UIRoot / VFX`
- **Pros**：机械化，不用思考
- **Cons**：
  - 字母序下 `Dialogue` 在 `GlobalState` 前，`SaveManager` 在 `SceneRouter` 前 — 都违反依赖
  - **Godot 4.x autoload 按声明顺序而非字母序初始化**（官方文档明确，stat-system GDD §I.2 已复核）
  - 与"by-feature"理念冲突
- **Rejection Reason**：无任何技术 / 工程收益，且违反多个依赖关系。

### Alternative 2: deferred-load（按需 initialise）

- **Description**：所有 autoload 在 `_ready` 中只设置最小骨架，真正初始化（如读 STATS_CONFIG）延迟到第一次 `get_*()` 调用。
- **Pros**：理论上避免顺序问题（被动 demand-load）
- **Cons**：
  - 把"何时 ready"的明确性变成"何时第一次被调用"的隐式行为
  - stat-system §F.5 的"启动 config 校验" R-S6 失效（要 fail-fast 但变成 fail-on-first-use）
  - SaveManager / SceneRouter 切场时 `GlobalState` 是否完整初始化需要每次 if 检查
- **Rejection Reason**：复杂度爆炸，与 ADR-0001 §10 启动校验 fail-fast 设计冲突。

### Alternative 3: 把 Resource autoloads (Sprites/Portraits/Atlas/VFX) 放在 GlobalState 之前

- **Description**：先 4 个资源 autoload，再 GlobalState 与其它业务 autoload。
- **Pros**：资源 autoload 真的零业务依赖，"先准备好资源 → 再初始化业务"读起来自然
- **Cons**：
  - GlobalState 也是零依赖（不读任何资源），把它放在 #1 让 stat-system §F.5 R-S6 校验"在最早可能的时机失败"语义最强
  - GlobalState 在 #1 时，未来若新增"在 _ready 期需要读 GlobalState 的资源 autoload"（极小可能但不能排除），本顺序仍兼容
- **Rejection Reason**：边际不适，但选 by-feature 的"业务核心优先"语义更稳健。
>>>>>>> fdd79b53c10f3ec1bb0e1598c089f6cceaed14f5

## Consequences

### Positive

<<<<<<< HEAD
- **项目可 launch**：`Identifier 'GlobalState' not declared` 等 parse 错误全部消失
- **加载顺序确定**：所有依赖 GlobalState 的 autoload 都能在 `_ready` 安全访问它（`_validate_configs` 已通过 + 6 集合已 init）
- **解锁 H.1–H.20 AC**：依赖 ADR-0001 + 本 ADR 双双 Accepted 后，gdunit4 测试可在 `--headless` 下跑
- **解锁 12+ 下游 GDD**：所有 `GlobalState.foo()` / `SaveManager.foo()` / `Dialogue.foo()` 调用都能 parse
- **`/architecture-review` 可执行**：autoload 注册是 `/architecture-review` Phase 6 的隐含前提
- **未来扩展边界明确**：新加 autoload 必须修订本 ADR，避免静默破坏依赖链

### Negative

- **`project.godot` 修改是大改**：5 行变 9 行；初次合并 PR 后 Godot 编辑器会重写 `project.godot` 缩进与 quoting，需手工保持一致
- **顺序依赖隐式**：未来新人开发可能不知道"autoload 必须按声明顺序"，习惯性地把新 autoload 加到末尾——若新 autoload 需要在 GlobalState 之前初始化，就会破坏。Mitigation：本 ADR 在 Validation Criteria 锁住 GlobalState 必须最前，未来新 autoload 默认插在 GlobalState 之后即可
- **Editor 重新打开后 Output 顺序变化**：从"Sprites 先 ready"变成"GlobalState 先 ready"，影响调试时的日志阅读习惯（一次性成本）

### Neutral

- `asset_ids.gd` 保持非 autoload 形态，与现有 import 模式一致
- 9 个 autoload 在 GL Compatibility / 60 fps 目标下没有性能影响（autoload 启动 < 50 ms 总和）

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| 编辑器 GUI 操作（"添加 Autoload"按钮）会自动按字母序排列，覆盖手工顺序 | Medium | High | 本 ADR Validation Criteria 锁声明顺序；CI 加一个简单 grep 校验 `[autoload]` 节第一行是 `GlobalState=`（防 GUI 误操作） |
| ADR-0001 实装漂移没改完就先合 ADR-0002 | Low | High | Migration Plan §1 明确两个 ADR 必须按"先 0001 改代码 → 再 0002 注册"顺序；如顺序反过来，启动时 `_validate_configs` 会 assert 阻断（fail-fast 实际上是 mitigation） |
| `[autoload]` 节其它配置（如 `[input]` `[rendering]`）位置错乱 | Low | Low | 本 ADR Decision 只规定 `[autoload]` 节内容，不动其它节 |
| 未来加新 autoload 时新人插在 GlobalState 之前 | Medium | Medium | CLAUDE.md 后续追加 "新 autoload 必须修订 ADR-0002" 一行；PR 模板 checkbox |
| Godot 升级到 5.0 后 autoload 加载机制变化 | Low | High | Engine Compatibility 标 HIGH；任何升级都触发本 ADR 重新验证 |

## Performance Implications

| Metric | Before | Expected After | Budget |
|--------|--------|---------------|--------|
| 启动时 autoload 总耗时 | ~10 ms（4 个） | ~30 ms（9 个） | < 100 ms |
| GlobalState `_ready` 耗时 | N/A | < 200 µs（含 `_validate_configs` + `reset_to_initial`） | < 1 ms |
| Memory：autoload 总占用 | ~50 KB | ~80 KB（多 5 个 Node + 状态） | < 1 MB |

启动开销可忽略；不会影响 60 fps 帧预算。

## Migration Plan

1. **前置**：ADR-0001 实装漂移修复（`global_state.gd`）已合并到 master
2. **打开 `project.godot`** 并替换 `[autoload]` 节为 §Decision 列出的 9 行
3. **本地 launch Godot 4.6 编辑器**：观察 Output 面板无 parse error / nil ref / assert
4. **F5 跑主场景**：进入 demo 场景；按 ESC 干净退出（冒烟级别）
5. **运行 `godot --headless --check-only --path .`**：CI 等价校验
6. **追加注册条目到 `docs/registry/architecture.yaml`**：本 ADR Phase 5 处理（autoload 注册顺序作为 api_decision）
7. **PR 合 master**：标题 `feat(autoload): register 5 missing autoloads + lock load order per ADR-0002`
8. **PR 合并后**：进入 `/test-setup` 装 gdunit4（独立 skill），跑 H.1–H.20 AC

**Rollback plan**：
- 启动时 `_validate_configs` assert：先回滚 ADR-0001 中的 `_validate_configs` 改动定位非法 config，不回滚本 ADR 的注册（注册是已落盘事实，回滚会让 12+ 调用点重新报 parse error）
- UIRoot `_ready` 报 nil：检查 `[autoload]` 节顺序——`GlobalState=` 必须在 `UIRoot=` 之前
- 12+ 调用点中某个 identifier 报 not declared：在 `[autoload]` 节确认拼写（区分大小写）
- 实在不行：还原 `[autoload]` 到原 4 行 + revert ADR-0001 实装改动；项目回到"已知不能 launch"的稳定态

## Validation Criteria

- [ ] `project.godot` `[autoload]` 节第一行是 `GlobalState="*res://scripts/autoload/global_state.gd"`
- [ ] `[autoload]` 节包含全部 9 个 entry，顺序与 §Decision 一致
- [ ] 项目能在 Godot 4.6 编辑器 launch 不报 parse error / nil ref
- [ ] GlobalState `_validate_configs` 不 assert（依赖 ADR-0001 实装合并）
- [ ] UIRoot `_ready` 时 `GlobalState.chapter_changed.connect(...)` 不报 nil reference
- [ ] `godot --headless --check-only --path .` 退出码 0
- [ ] `docs/registry/architecture.yaml` 含 autoload 加载顺序条目（api_decisions 节）

## GDD Requirements Addressed

| GDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/gdd/stat-system.md` | Stat System | §I.1 BLOCKING：autoload 注册 `GlobalState` | Decision § `[autoload]` 第 1 行 `GlobalState=...` |
| `design/gdd/stat-system.md` | Stat System | §I.2 BLOCKING：加载顺序冻结（GlobalState 在 SaveManager 前） | Decision § Architecture 时序图锁定 [1] GlobalState → [6] SaveManager |
| `design/gdd/stat-system.md` | Stat System | §I.2 官方文档复核：autoload 按声明顺序非字母序 | Engine Compatibility 与 Alternative 1 拒绝理由均引用文档复核结论 |
| `design/gdd/stat-system.md` | Stat System | §F.5 load-path UI 契约（reset/from_dict 静默 + UIRoot 主动 re-read） | Architecture § 时序图保证 GlobalState [1] 早于 SaveManager [6] 与 UIRoot [9]，UIRoot 调用 connect 时 GlobalState 已 _ready |
| Future GDDs（dialogue / save-load / scene-routing / stat-panel-ui 等） | Foundation/Core | autoload 调用语法：`GlobalState.foo()` 等 | Key Interfaces 锁住 9 个 autoload identifier |

## Related

- `ADR-0001-stat-system-contract.md`（同 stat-system §I 主题，先合 0001 再合 0002）
- `design/gdd/stat-system.md` §I.1 / §I.2 / §I.4 / §F.5
- `design/gdd/reviews/stat-system-review-log.md`（Round-2 godot-specialist 字母序误判 → 官方文档复核 archive）
- `project.godot`（本 ADR 修改目标）
- `scripts/autoload/`（10 个文件，9 注册 + 1 保持非 autoload）
- `docs/engine-reference/godot/VERSION.md`（Godot 4.6 pinned）
- Godot 官方文档：`tutorials/scripting/singletons_autoload.md`（声明顺序而非字母序）

---

> **下一步路径**：
> 1. 等 ADR-0001 实装漂移修复合并 master
> 2. 修改 `project.godot` 按本 ADR Decision
> 3. 本地 + CI 启动验证
> 4. `/test-setup` 装 gdunit4
> 5. 跑 H.1–H.20 AC
> 6. fresh session 跑 `/architecture-review`
> 7. `/design-system asset-loading` 继续
=======
- 项目立刻能 launch（解 BLOCKING）
- stat-system §F.5 R-S6 启动校验在最早可能的时机失败，typo config 当场 assert(false)
- 9 个 autoload 的 `_ready` 调度顺序确定 — `SaveManager._ready` 调 `GlobalState.from_dict` 不会 KeyError
- 未来新 autoload 有明确的"追加 + 写 ADR 修订"流程
- AssetIds 的"非 autoload" 身份显式锁定，避免后续 PR 误注册

### Negative

- `project.godot` 的 `[autoload]` 节是 ADR 的"事实源"，任何手动 reorder 必须经 ADR 修订（PR review 兜底）
- 9 行硬编码排列，给"自动化排序工具"留的空间为 0（这本就是该这样：声明顺序就是依赖顺序）
- 未来 AudioBus 等新 autoload 加入时，必须经 ADR 修订本 ADR，不能直接在 `project.godot` 里手动加（否则 ADR 与现实漂移）

### Risks

- **风险 1：开发期手动重排 [autoload]**
  - 缓解：本 ADR Status=Accepted 后，`project.godot` 的 `[autoload]` 节作为受 ADR 约束的"产物"。在 PR review 中扫描 diff 是否触及该节；触及则要求引用 ADR-0002 修订
- **风险 2：未来引擎升级改 autoload 加载机制**
  - 缓解：Godot 4.x 系列稳定；5.x 升级时复跑 stat-system §H.19 启动校验 AC + 写新 ADR 替代本 ADR
- **风险 3：deferred-load autoload 选项被误用**
  - 缓解：路径前缀 `*` 强制 autoload 在场景加载时立即 ready（不是 lazy）；ADR-0002 §"路径前缀"明确禁用其它形态

## GDD Requirements Addressed

| GDD System | Requirement | How This ADR Addresses It |
|---|---|---|
| stat-system.md §I.1 | "GlobalState 必须在 project.godot [autoload] 中按 GlobalState 名注册，路径 *res://scripts/autoload/global_state.gd" | §"Decision" 注册块 #1 行 |
| stat-system.md §I.2 | "GlobalState._ready() 必须在 SaveManager._ready() 之前完成；按声明顺序排列即可保证" | §"Decision" 顺序 #1 vs #6 |
| stat-system.md §F.5 R-S6 | "启动 config 校验在 _ready 中 fail-fast" | §"顺序的依赖原因" 把 GlobalState 锁在 #1，让 fail 时机最早 |
| stat-system.md §F.5 load-path | "reset/from_dict 静默 + SaveManager.load_finished 通知 UI re-read" | §"顺序的依赖原因" 把 SaveManager 锁在 GlobalState 后、UIRoot 之前，让 SaveManager.load_finished 在 UIRoot 已 ready 后才被消费 |

## Performance Implications

- **CPU**：无影响（autoload 顺序只影响 _ready 调度，对 frame budget 透明）
- **Memory**：9 个 autoload 总占用极小（demo 阶段内部状态全部 < 数 KB）
- **Load Time**：autoload _ready 总时间 < 50 ms（GlobalState reset、4 个资源加载、SaveManager 检查目录、UIRoot 实例化 4 个 CanvasLayer 子场景），主要时间在 UIRoot 实例化阶段
- **Network**：N/A

## Migration Plan

### 阶段 1：补全 [autoload] 注册（一次 PR）

修改 `project.godot` 的 `[autoload]` 节为本 ADR §"Decision" 中的 9 行排列。**与 ADR-0001 实装阶段 1 同 PR 提交**（否则 GlobalState 注册了但 9 项契约漂移未修复，状态半新半旧）。

### 阶段 2：launch 测试

启动 Godot 4.6 编辑器：
- 项目能成功 launch 不报 parse error
- `main.tscn` 启动后控制台 print 无 KeyError / unknown identifier
- 调 `GlobalState.get_stat("xuexi")` 返回 3（init 值）

### 阶段 3：顺序回归测试

把 GlobalState 临时挪到 [autoload] 末尾，启动 SaveManager.load_slot(0) 应触发可观察错误（KeyError 或 GlobalState 状态空），证明顺序确实影响行为。然后还原到 ADR §Decision 顺序。

### 阶段 4：ADR Accepted

阶段 1–3 完成后，把本 ADR Status 从 `Proposed` 升 `Accepted`，并在 stat-system GDD §I.1 / §I.2 末尾标注"由 ADR-0002 落实"。

## Validation Criteria

- [ ] `project.godot` `[autoload]` 节包含 9 行，顺序与 §"Decision" 严格一致
- [ ] `Grep "AssetIds=" project.godot` 零匹配（AssetIds 不应注册）
- [ ] Godot 4.6 编辑器 launch `main.tscn` 不报 parse error
- [ ] `Grep "extends Node" scripts/autoload/global_state.gd` 匹配（autoload 单例必须 extends Node）
- [ ] 同样的 grep 对 SaveManager / SceneRouter / Dialogue / UIRoot 都匹配（每个 autoload 都是 Node）
- [ ] AssetIds.gd 仍然 `extends RefCounted` 且 `class_name AssetIds`（非 autoload 形态）
- [ ] 项目运行后调 `GlobalState.get_stat("xuexi")` 返回 3（验证 _ready 走完了 reset_to_initial）

## Related Decisions

- **ADR-0001-stat-system-contract**（同会话写作伙伴）— 本 ADR 是 ADR-0001 §10 启动 config 校验、§7 from_dict 静默契约的运行环境前提。两 ADR 必须 Accepted 同 PR。
- **GDD design/gdd/stat-system.md §I.1 / §I.2** — 本 ADR 是该 GDD 的实装承诺。
- **未来 ADR-XXXX-audio-bus**（Post-Demo）— 添加 AudioBus autoload 时引用本 ADR 修订其 [autoload] 节。
>>>>>>> fdd79b53c10f3ec1bb0e1598c089f6cceaed14f5
