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

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Engine** | Godot 4.6 |
| **Domain** | Core / Scripting（autoload registration） |
| **Knowledge Risk** | HIGH — Godot 4.6 是 post-LLM-cutoff |
| **References Consulted** | Godot 4.x docs `tutorials/scripting/singletons_autoload.md`（Round-2 已 Web 复核：autoload 按声明顺序 top-to-bottom 初始化）；stat-system GDD §I.1 / §I.2；本仓库 `project.godot` 当前 `[autoload]` 节 |
| **Post-Cutoff APIs Used** | None — autoload 注册机制全版本一致 |
| **Verification Required** | 项目能在 Godot 4.6 编辑器内 launch 不报 `Identifier 'GlobalState' not declared`；GlobalState `_validate_configs` 正常通过；UIRoot `_ready` 时 `GlobalState.chapter_changed.connect(...)` 不报 nil reference |

> **Note**: Knowledge Risk 标 HIGH 因 4.6 是 post-cutoff，但 autoload 注册机制本身在 Godot 4.0+ 全版本稳定，**不是**新特性。LLM 误判过 autoload 按字母序初始化（Round-2 godot-specialist 提出，已通过官方文档复核为错误）——本 ADR 锁住正确做法，避免后续误判。

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | None（与 ADR-0001 同 stat-system §I 主题，ADR 编号上相邻；但本 ADR 不依赖 ADR-0001 内容，可独立 Accepted） |
| **Enables** | ADR-0001 实装漂移修复落地（global_state.gd 改完后必须本 ADR 注册才能 launch）；12+ 下游 GDD（任何一个 autoload 调用都依赖本 ADR） |
| **Blocks** | 项目能在 Godot 4.6 编辑器 launch；任何 `GlobalState.foo()` / `Dialogue.play(...)` / `SaveManager.save(...)` 调用 |
| **Ordering Note** | ADR-0001 修改 `global_state.gd` 实装侧契约 → 本 ADR 修改 `project.godot` 注册 → 项目可 launch。两步必须按这个顺序（先 ADR-0001 改代码再 ADR-0002 注册），否则注册成功后启动时 `_validate_configs` 会立刻 assert。 |

## Context

### Problem Statement

仓库内已落盘 9 个 autoload 单例脚本（`scripts/autoload/*.gd`），其中 12+ 个调用点（包括 ADR-0001 锁定的 `GlobalState`）已经按 `Foo.bar()` 形式直接调用。但 `project.godot` 的 `[autoload]` 节当前**只**声明了 4 个：

```ini
[autoload]
Sprites="*res://scripts/autoload/sprites.gd"
Portraits="*res://scripts/autoload/portraits.gd"
VFX="*res://scripts/autoload/vfx.gd"
Atlas="*res://scripts/autoload/atlas.gd"
```

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
SaveManager="*res://scripts/autoload/save_manager.gd"
SceneRouter="*res://scripts/autoload/scene_router.gd"
Dialogue="*res://scripts/autoload/dialogue.gd"
UIRoot="*res://scripts/autoload/ui_root.gd"
```

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

## Consequences

### Positive

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
