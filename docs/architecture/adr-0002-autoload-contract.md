# ADR-0002: Autoload Contract (Registration + Load Order)

## Status

Proposed

## Date

2026-06-01

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Engine** | Godot 4.6 (pinned 2026-02-12) |
| **Domain** | Core / Scripting (Autoload registration + initialization order) |
| **Knowledge Risk** | MEDIUM — Autoload 顺序在 4.x 历来是 `project.godot [autoload]` 节的声明顺序（top-to-bottom），但 LLM 训练数据里常见误导（"按字母序"或"按依赖图"），必须以官方文档为准 |
| **References Consulted** | `docs/engine-reference/godot/VERSION.md`；Godot 官方文档 `tutorials/scripting/singletons_autoload.md`：*"The order of these entries can be adjusted, and they are processed top-to-bottom in the global scene tree"* |
| **Post-Cutoff APIs Used** | 无（autoload 机制本身在 4.0 已稳定） |
| **Verification Required** | (a) 项目能在 Godot 4.6 编辑器 launch 不报"Identifier 'GlobalState' not declared"；(b) 把 GlobalState 临时挪到 [autoload] 节末尾时，SaveManager._ready 内 GlobalState.from_dict 仍能正常调用（验证声明顺序是真的影响 _ready 调度） |

### Autoload 顺序的官方文档复核

stat-system GDD §I.2 已经做过这次复核（godot-specialist Round-2 评审中曾误声称"字母序"，被官方文档否定）。本 ADR 引用该结论，不重复争论：**Godot 4.x autoload 按 [autoload] 节的声明顺序（top-to-bottom）初始化，与 autoload 名字字母序无关。**

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | ADR-0001-stat-system-contract（必须同时 Accepted；本 ADR 的载入顺序假设 GlobalState 接口与 §10 启动 config 校验已落地） |
| **Enables** | 所有下游 GDD（Save/Load、Dialogue、Cutscene Runner、NPC、Combat 等）— 它们的 `_ready()` 调用 GlobalState 在本 ADR 落地前都会立刻 parse error |
| **Blocks** | Demo 切片所有 stories — 项目当前不能运行；本 ADR 是项目能 launch 的前置 |
| **Ordering Note** | 本 ADR 与 ADR-0001 紧密耦合：ADR-0001 锁"接口契约"，ADR-0002 锁"注册 + 装配顺序"。Migration 阶段两份 ADR 落地必须同 PR（Editor 一旦在 ADR-0001 实装的同时未注册 GlobalState autoload，整个项目会 break） |

## Context

### Problem Statement

`project.godot` 的 `[autoload]` 节当前只声明了 4 个 autoload（Sprites / Portraits / VFX / Atlas）：

```ini
[autoload]
Sprites="*res://scripts/autoload/sprites.gd"
Portraits="*res://scripts/autoload/portraits.gd"
VFX="*res://scripts/autoload/vfx.gd"
Atlas="*res://scripts/autoload/atlas.gd"
```

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
SaveManager="*res://scripts/autoload/save_manager.gd"
SceneRouter="*res://scripts/autoload/scene_router.gd"
Dialogue="*res://scripts/autoload/dialogue.gd"
UIRoot="*res://scripts/autoload/ui_root.gd"
```

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

## Consequences

### Positive

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
