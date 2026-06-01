# ADR-0001: Stat System Contract (v1)

## Status

Proposed

## Date

2026-06-01

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Engine** | Godot 4.6 (pinned 2026-02-12) |
| **Domain** | Core / Scripting (Autoload + typed Dictionary + Signals) |
| **Knowledge Risk** | MEDIUM — 4.4–4.6 是 LLM cutoff（May 2025）之后的版本，必须以 `docs/engine-reference/` 为准而非训练数据 |
| **References Consulted** | `docs/engine-reference/godot/VERSION.md` / `breaking-changes.md` / `deprecated-apis.md` / `modules/input.md` |
| **Post-Cutoff APIs Used** | `Dictionary[String, int]` 类型化（4.4+，4.6 稳定） |
| **Verification Required** | (a) `Dictionary[String, int]` typed declaration 在 Godot 4.6 编辑器中能正常加载且静态分析无 warning；(b) `clampi` 行为符合 Godot 4.6 docs（与 4.0+ 无差异）；(c) `Object.CONNECT_DEFERRED` 在 4.6 仍按"下一帧 idle 调度"语义（4.5 SDL3/dual-focus 改动不影响该 flag） |

### 与 Engine 4.4–4.6 变更的交叉核对

| 4.x 变更 | 是否影响本 ADR | 处理 |
|---|---|---|
| `Dictionary[K,V]` 类型化（4.4） | ✅ 直接采用 | §3 Decision 强制 typed Dictionary |
| Quaternion 默认 identity（4.6） | ❌ 无关 | — |
| Glow tonemapping 顺序（4.6） | ❌ 无关 | — |
| Jolt 默认（4.6） | ❌ 无关 | — |
| dual-focus / SDL3 gamepad（4.5/4.6） | ❌ 无关 | — |
| Autoload 加载顺序：top-to-bottom 声明序（非字母序） | ✅ 关联 ADR-0002 | 本 ADR 假设 GlobalState 先于其它 autoload 完成 `_ready()`，由 ADR-0002 强制声明顺序 |
| `connect("sig", obj, "method")` 已 deprecated（4.0） | ✅ 间接 | §3 §F.5 强制 `signal.connect(callable)` 风格（不再支持字符串 connect） |

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | None（本 ADR 是项目首个 ADR） |
| **Enables** | ADR-0002-autoload-contract（注册顺序 + 加载顺序冻结）；ADR-0003+ 各下游系统（Save/Load、Dialogue、Cutscene Runner、NPC、Combat、Stat Panel UI）均依赖本 ADR 锁定的 6 个接口 + 6 个信号 |
| **Blocks** | Demo 切片所有 stories — stat-system.md §H 的 20 条 AC 在本 ADR Accepted 之前都属于"待实现"状态；下游 12 份 GDD 在本 ADR 锁定接口前不能进入 Approved |
| **Ordering Note** | 本 ADR 与 ADR-0002 紧密耦合，但 ADR-0001 锁的是"接口契约"，ADR-0002 锁的是"装配顺序"。两者可同会话写完，但 ADR-0001 必须先 Accepted（GlobalState 的接口是 SaveManager / SceneRouter 等其它 autoload 在 `_ready()` 中调用的目标） |

## Context

### Problem Statement

`design/gdd/stat-system.md` 已经经过两轮 design-review 形成 v1 接口契约（§C 接口、§D 公式、§E edge cases、§F.5 invariants、§H 全 20 AC），但 `scripts/autoload/global_state.gd` 的现有实装与该 GDD 在 9 处不一致（GDD §I.4 已逐项列出）。如果不立刻用 ADR 把 v1 接口锁死，三件事会同时发生且互相加剧：

1. **下游 12 份 GDD 引用接口时各自漂**：每份 GDD 写 "calls `GlobalState.foo()`" 时若 `foo` 还没固化，会出现"GDD A 假设 4 元 signal payload，GDD B 假设 3 元"的相互污染。
2. **代码每次重构都要重新协商**：`change_*` 是否报 push_error、`from_dict` 是否自愈、`to_dict` 是否 sort——这些决策没有 ADR 锁定，每个 PR 评审都要重开战。
3. **测试无法验证**：GDD §H 的 20 条 AC 要求 4 元 signal payload、`AFFINITY_CONFIG` per-NPC schema、`_emit_depth` 再入守卫等具体实装行为，但代码当前不满足任何一条，AC 全部"待实现"。

### Constraints

- **GDD §C / §D / §E / §F.5 / §H 已 Approved**（2026-05-31 round-2 修订），本 ADR 不重新协商这些条款，只把它们提升为强制约束。
- **现有 12 个调用点已用 `GlobalState.foo()` 形式调用**（见 stat-system §I.1）— 接口名 `GlobalState` 必须保留，autoload 名也必须叫 `GlobalState`。
- **demo 阶段无 schema 版本迁移需求**（仅需 round-trip 一致性），版本字段交给 SaveManager 在外层 wrapper 处理。
- **Godot 4.6 引擎特性可全用**：`Dictionary[K,V]`、`clampi`、`Object.CONNECT_DEFERRED`、`signal.connect(callable)` 风格、`assert(false)` 阻断启动 — 全部已在 4.6 stable。

### Requirements

- 必须满足 stat-system.md §H.1–H.20 共 20 条 AC（含 H.12 < 5 ms / 100 次 change_* + 100 次 callback 的性能预算）。
- 必须满足 §F.5 全 7 条 cross-GDD invariant（含启动 config 校验、CONNECT_DEFERRED 推荐、affinity event idempotent、tone 不得加 juice 等）。
- 必须满足 §I.4 全 8+1 项实装契约修复（class_name / typed Dict / clampi / 4 元 signal / `AFFINITY_CONFIG` / from_dict 自愈 / to_dict sort / `_emit_depth` / `_validate_configs`）。
- 改动必须最小化：保留现有 `GlobalState` autoload 名、`_stats / _vars / _affinity / _triggered / _era_markers / _chapter` 内部字段名（与 GDD §C.1 表一致）。

## Decision

锁定 GlobalState 为 **Autoload 单例 + `class_name GlobalState` + typed Dictionary[K,V] + 4 元化信号 + 自愈式 from_dict + 排序式 to_dict + 再入守卫 + 启动 config 校验** 的固定形态，作为 v1 接口契约。

### 1. Class Identity（§I.4 item 1）

- 文件首行加 `class_name GlobalState`，使下游静态类型代码可写 `var gs: GlobalState = ...`，并允许测试夹具按类型而非按 autoload 名引用。
- 维持 autoload 名 `GlobalState`（与现有 12 个调用点一致；ADR-0002 在 `[autoload]` 节按此名注册）。

### 2. Typed Containers（§I.4 item 2 + §C.1）

```gdscript
var _stats: Dictionary[String, int] = {}
var _vars: Dictionary[String, int] = {}
var _affinity: Dictionary[String, int] = {}
var _triggered: Dictionary[String, bool] = {}    # set-as-dict, 值恒 true
var _era_markers: Dictionary[String, bool] = {}  # 同上
var _chapter: String = "prologue"
```

理由：Godot 4.4+ 的 `Dictionary[K,V]` 让 KeyError 在 parse 期暴露而非运行期，配合 GDScript 静态分析提示。

### 3. Public Interface Freeze（§C.5）

冻结的 6 个公开接口：

```gdscript
get_stat(id: String) -> int
change_stat(id: String, delta: int) -> void
get_var(id: String) -> int
change_var(id: String, delta: int) -> void
get_affinity(npc_id: String) -> int
change_affinity(npc_id: String, delta: int) -> void
has_triggered(event_id: String) -> bool
mark_triggered(event_id: String) -> void
has_era_marker(marker_id: String) -> bool
mark_era_marker(marker_id: String) -> void
get_chapter() -> String
set_chapter(chapter_id: String) -> void
to_dict() -> Dictionary
from_dict(data: Dictionary) -> void
reset_to_initial() -> void
```

**负 API（禁止存在）**：`set_stat / set_var / set_affinity` 三个绝对赋值方法不得添加。任何"绕过 change_* 的赋值"必须经 `from_dict(...)` 注入。该规则由 §H.16 AC 强制 + future PR review 兜底。

### 4. Signal Contract（§C.6 + §I.4 item 4）

冻结的 6 个信号 payload 形态：

```gdscript
signal stat_changed(stat_id: String, old_value: int, new_value: int, requested_delta: int)
signal var_changed(var_id: String, old_value: int, new_value: int, requested_delta: int)
signal affinity_changed(npc_id: String, old_value: int, new_value: int, requested_delta: int)
signal event_triggered(event_id: String)
signal era_marker_added(marker_id: String)
signal chapter_changed(old_chapter: String, new_chapter: String)
```

广播规则（§C.6）：
- 三个 `*_changed` 仅在 `new_value != old_value`（即 `effective_delta != 0`）时广播；payload 字段中 `requested_delta` 是调用方传入的**原始** delta（**不**被 clamp 修剪），允许订阅者识别"半吃掉"边界场景。
- `event_triggered / era_marker_added` 仅在 ID 首次进入集合时广播（idempotent 重复 mark 静默忽略）。
- `chapter_changed` 仅在 `new_chapter != old_chapter` 时广播。
- `reset_to_initial()` 与 `from_dict(...)` **不**广播任何信号（load 路径静默契约，订阅者由 `SaveManager.load_finished` / `_ready` 时主动 re-read）。

### 5. Clamp Formulas（§D.1 / §D.2 / §D.3 + §I.4 item 3）

**显性属性 / 隐性变量公式（D.1）**：

```gdscript
# 实装契约：先把 delta 预收敛到溢出安全区间再加，避免 INT64 wrap。
var safe_delta := clampi(delta, cfg.min - cfg.max, cfg.max - cfg.min)
var new_value  := clampi(current + safe_delta, cfg.min, cfg.max)
```

**NPC 好感度公式（D.2，per-NPC 范围）**：

```gdscript
var npc := AFFINITY_CONFIG[npc_id]   # {init, min, max}
var safe_delta := clampi(delta, npc.min - npc.max, npc.max - npc.min)
var new_aff    := clampi(current + safe_delta, npc.min, npc.max)
```

**广播判定（D.3）**：

```gdscript
if new_value != old_value:
    signal.emit(id, old_value, new_value, requested_delta)   # requested 字段是原始 delta，未 clamp
```

强制使用 `clampi`（不用 `clamp`）— 防止 from_dict 路径加载 JSON 浮点污染返回类型（GDD §I.4 item 3）。

### 6. AFFINITY_CONFIG Per-NPC Schema（§C.4 + §I.4 item 5）

废弃旧的 `AFFINITY_INIT` + 全局 `AFFINITY_MIN/MAX = ±10`，改为 per-NPC `{init, min, max}`：

```gdscript
const AFFINITY_DEFAULT_MIN := -10
const AFFINITY_DEFAULT_MAX := +10

const AFFINITY_CONFIG := {
    "baoxianjin":   {"init": 0,  "min": -10, "max": +10},
    "baosimu":      {"init": 1,  "min": -10, "max": +10},
    "wangyan":      {"init": 1,  "min": -10, "max": +10},
    "zengjianming": {"init": 1,  "min": -10, "max": +10},
    "caozhengdong": {"init": -3, "min": -15, "max": +10},  # "宿敌"留 BOSS 战头室
    "huxiaodong":   {"init": 0,  "min": -10, "max": +10},
    "zhanglei":     {"init": 0,  "min": -10, "max": +10},
    "lijing":       {"init": 0,  "min": -10, "max": +10},
    "menwei_daye":  {"init": 0,  "min": -10, "max": +10},
    "fuqin":        {"init": 5,  "min": -10, "max": +10},
    "muqin":        {"init": 5,  "min": -10, "max": +10},
    "jiejie":       {"init": 8,  "min": -10, "max": +15},  # "被托住" pillar 头室
}
```

未来章节扩展 NPC 必须先在 `AFFINITY_CONFIG` 表中声明范围再 `change_affinity`（§F.5 invariant）；未注册 NPC 经 §E.2 修订规则触发 push_error（H.13 强制）。

### 7. from_dict 自愈式 Cast + Clamp（§E.6 + §I.4 item 6）

```gdscript
func from_dict(data: Dictionary) -> void:
    reset_to_initial()
    for id in data.get("stats", {}):
        if not STATS_CONFIG.has(id):
            push_warning("[GlobalState] from_dict: unknown stat: %s" % id)
            continue
        var raw = data["stats"][id]
        var cast_v := int(raw)                                  # JSON 浮点 → int
        var cfg = STATS_CONFIG[id]
        var clamped := clampi(cast_v, cfg.min, cfg.max)
        if clamped != raw:
            push_warning("[GlobalState] from_dict: %s out-of-range %s, clamped to %d" % [id, raw, clamped])
        _stats[id] = clamped
    # _vars / _affinity 同构路径; _triggered / _era_markers 见下条; _chapter 越界写入 + push_warning
    # 不广播任何 *_changed（load 路径静默）
```

未识别 ID 跳过 + push_warning（H.17 强制）；chapter 越界写入但 push_warning（H.18 强制）；`_triggered` 字段若是 dict 含 falsy value（旧存档兼容）按 keys 重建并 push_warning（H.10 round-trip 容错）。

### 8. to_dict 排序契约（§E.8 + §I.4 item 7）

```gdscript
func to_dict() -> Dictionary:
    var trig := _triggered.keys(); trig.sort()
    var era  := _era_markers.keys(); era.sort()
    return {
        "stats":       _stats.duplicate(true),
        "vars":        _vars.duplicate(true),
        "affinity":    _affinity.duplicate(true),
        "triggered":   trig,
        "era_markers": era,
        "chapter":     _chapter,
    }
```

`_triggered` / `_era_markers` 序列化为已 sort 的 Array（**只输出 keys，不输出 value**）；保证 round-trip 字面级稳定（H.10 显式断言字典升序）。`_stats` / `_vars` / `_affinity` key 顺序由 `STATS_CONFIG / VARS_CONFIG / AFFINITY_CONFIG` 声明顺序决定，无需额外 sort。

### 9. Re-entrancy Guard（§C.6 + §E.3 + §I.4 item 8）

```gdscript
var _emit_depth: int = 0

func change_stat(id: String, delta: int) -> void:
    if _emit_depth > 0:
        push_error("[GlobalState] re-entrant change_stat during signal handler — use call_deferred")
        return  # 不修改集合、不发新信号
    if not STATS_CONFIG.has(id):
        push_error("[GlobalState] unknown stat: %s" % id)
        return
    # ...clamp + emit logic...
    _emit_depth += 1
    stat_changed.emit(id, old, new, delta)
    _emit_depth -= 1
```

订阅 GDD（[[stat-panel-ui]] / [[combat-core]] / [[npc-system]] 等）必须在自己的 Dependencies 节声明 `connect(handler, Object.CONNECT_DEFERRED)`；这是双重保险（§F.5 invariant + §I.4 item 8）。同帧多次 change_* 仍正确广播（H.20 强制），CONNECT_DEFERRED 把订阅 handler 调度到下一帧。

### 10. Startup Config Validation（§F.5 R-S6 + §I.4 额外条 + §H.19）

```gdscript
func _ready() -> void:
    if not _validate_configs(STATS_CONFIG, VARS_CONFIG, AFFINITY_CONFIG):
        assert(false, "GlobalState config invariant violated")
    reset_to_initial()

func _validate_configs(stats_cfg, vars_cfg, affinity_cfg) -> bool:
    # 每个 entry 必须满足 min ≤ init ≤ max 且 min ≤ max
    # 违反即 push_error 并返回 false
```

启动期 fail-fast：避免 `clampi(x, min, max)` 在 `min > max` 时未定义行为悄悄腰斩 change_affinity 的所有调用（H.19 强制）。

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  AUTOLOAD: GlobalState (class_name GlobalState)                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  STATE CONTAINERS                                        │   │
│  │  _stats: Dict[String,int]    _vars: Dict[String,int]     │   │
│  │  _affinity: Dict[String,int] _triggered: Dict[String,bool]│   │
│  │  _era_markers: Dict[String,bool]   _chapter: String       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ↑ ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PUBLIC INTERFACE (frozen v1, §C.5)                      │   │
│  │  get_*  →  read-only                                     │   │
│  │  change_*  →  clamp + emit (re-entrancy guard)           │   │
│  │  mark_*  →  set + emit on first only                     │   │
│  │  to_dict / from_dict / reset_to_initial → serialization  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          ↓ emit                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SIGNALS (frozen v1, §C.6, 4-tuple / 2-tuple payloads)   │   │
│  │  stat_changed / var_changed / affinity_changed           │   │
│  │  event_triggered / era_marker_added / chapter_changed    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↓ CONNECT_DEFERRED
   ┌──────────────────────────────────────────────────────────┐
   │  DOWNSTREAM SUBSCRIBERS (each in its own GDD)            │
   │  Stat Panel UI  ←  stat_changed                          │
   │  Combat Core / Courage / Skill / Emotion  ←  stat_/var_  │
   │  NPC System  ←  affinity_changed                         │
   │  Era Marker / Toast  ←  era_marker_added / chapter_      │
   │  SaveManager  ↔  to_dict / from_dict / reset_to_initial  │
   └──────────────────────────────────────────────────────────┘
```

### Key Interfaces

见 §3（公开接口冻结）+ §4（信号 payload）+ §6（AFFINITY_CONFIG schema）。所有下游 GDD 引用本 ADR 时必须使用其中明文契约，不得自行扩展或更名。

## Alternatives Considered

### Alternative 1: RefCounted Service + 依赖注入

- **Description**：把 GlobalState 改成 `RefCounted` 类，由场景树根节点实例化并通过构造参数 / setter 注入到下游订阅者。
- **Pros**：
  - 测试可独立 new 一个隔离实例，不污染全局
  - 移除"硬依赖 autoload 名"的耦合
- **Cons**：
  - 改动量大：12 个现有 `GlobalState.foo()` 调用点全部要改
  - 与 stat-system GDD §I.1 "保留 GlobalState autoload 名"约束冲突
  - 需要再设计一层"谁第一个 new、谁负责传递"的生命周期管理（实质在重新实现 autoload 已有功能）
- **Rejection Reason**：GDD 已明确指向 autoload 方案；测试性问题可以通过 gdunit4 `before_test` 中调 `reset_to_initial()` + 断连信号（§H 测试夹具契约）解决，不需要换底盘。

### Alternative 2: 拆 stats / vars / affinity 为 3 个独立 autoload

- **Description**：分别 `StatStore` / `VarStore` / `AffinityStore` autoload，每个只负责自己的集合。
- **Pros**：单个 autoload 内部更简单；理论上可独立测试
- **Cons**：
  - **失 round-trip 原子性**：`to_dict / from_dict` 必须由某一方协调，否则不是一份原子存档
  - **失 reset 原子性**：新游戏触发时三个 store 的 reset 可能产生中间态（一个已 reset、一个还没）
  - 增加 3 倍 autoload 接口面（GDD §C.5 锁的 6 个接口要复制 3 份）
  - chapter / triggered / era_markers 三个仍然要塞到某一个里，要么再开第 4 个 autoload
- **Rejection Reason**：原子性 + 接口面成本 > 内部解耦收益；GDD §F.2 已经把 9 个下游系统都按"一个 GlobalState"设计依赖图。

### Alternative 3: 保留现状 + 不写 ADR

- **Description**：让 `global_state.gd` 与 GDD §C 的 9 项漂移继续存在，由 PR review 兜底。
- **Pros**：零工作量
- **Cons**：
  - GDD §H 全 20 条 AC 永远跑不通（4 元 signal payload / `AFFINITY_CONFIG` / `_emit_depth` 全部缺失）
  - 下游 12 份 GDD 写到某一份时一定要重新协商接口（哪个 GDD 第一个声明"我读 4 元"哪个就推迟）
  - 测试无法 gate；新 PR 会引入更多漂移
- **Rejection Reason**：GDD §I.4 已明确把这 9 项标为 BLOCKING；不写 ADR 等同于让 BLOCKING 永久存在。

## Consequences

### Positive

- stat-system GDD §H 的 20 条 AC 全部具备实装基础，可在 `/test-setup` 安装 gdunit4 后立刻跑
- 下游 12 份 GDD 引用 GlobalState 时有唯一权威源，不会出现"GDD A 假设 4 元 signal、GDD B 假设 3 元"的污染
- `change_*` 接口的 push_error / push_warning / `_emit_depth` 守卫让 dev console 立刻暴露所有契约违反，零静默 typo
- `from_dict` 自愈让玩家不会因"曾经写错的存档"被踢出系统
- `_validate_configs` 启动校验把 `min > max` 这类 typo 在 launch 阶段 fail-fast
- AFFINITY_CONFIG per-NPC schema 让 jiejie / caozhengdong 的"被托住" / "宿敌" pillar 头室在数据层成立，不靠下游硬编码

### Negative

- 一次 ADR Accepted 后，§3 / §4 / §6 的接口不能再改 — 任何修改都要走 supersede ADR
- 实装侧 9 项漂移的修复改动 = 一份完整 PR（stat-system GDD §I.4 列表），需要专门时间
- `Dictionary[String, int]` 类型化要求所有上游调用方在传 key 时不得传 StringName 等隐式转换源
- `_emit_depth` 再入守卫意味着订阅者**绝对不能**在 handler 里同步调 change_*；CONNECT_DEFERRED 是事实上的强制约定（虽然实装侧用 push_error 兜底）

### Risks

- **风险 1：调用方传非 String key（如 StringName）**
  - 缓解：`Dictionary[String, int]` 在静态分析期 warn；实装中所有 public API 参数已 typed `String`，编译器会拒绝 mismatched literal
- **风险 2：未来需要原子事务（一次提多个 delta，失败回滚）**
  - 缓解：当前不实装；GDD Q1 已留 Open Question，由后续 ADR 增量。本 ADR §3 接口锁定不阻拦后续加 `change_batch(...)` 类新方法（追加非破坏）
- **风险 3：autoload 加载顺序在 ADR-0002 落地之前未冻结**
  - 缓解：本 ADR 与 ADR-0002 同会话写完；本 ADR §"ADR Dependencies → Enables" 已声明强依赖
- **风险 4：Godot 4.x 未来版本可能改 `Dictionary[K,V]` 行为**
  - 缓解：4.4 起稳定，4.6 已 ship；新版升级时需复跑 §H AC 套件，由 `docs/engine-reference/` 升级流程兜底

## GDD Requirements Addressed

| GDD System | Requirement | How This ADR Addresses It |
|---|---|---|
| stat-system.md §C.1 | 6 个 state container（_stats / _vars / _affinity / _triggered / _era_markers / _chapter）的存在与类型 | §2 Decision 锁 typed Dictionary 与字段名 |
| stat-system.md §C.4 | per-NPC affinity {init, min, max} schema（jiejie max=15、caozhengdong min=-15） | §6 Decision 完整声明 AFFINITY_CONFIG |
| stat-system.md §C.5 | 6 个公开接口冻结 + 负 API（无 set_*） | §3 Decision 列出全部 + 负 API |
| stat-system.md §C.6 | 6 个信号的 4 元 / 2 元 payload + `_emit_depth` 再入守卫 | §4 + §9 Decision |
| stat-system.md §D.1 | clamp 公式 + INT64 溢出安全 | §5 Decision |
| stat-system.md §D.2 | per-NPC affinity clamp | §5 + §6 Decision |
| stat-system.md §D.3 | 广播判定（new ≠ old 才发） | §4 + §5 Decision |
| stat-system.md §E.2 | 未知 ID push_error（三类对称） | §9 Decision（change_stat 示例 push_error 路径） |
| stat-system.md §E.6 | from_dict 自愈式 cast + clamp + push_warning | §7 Decision |
| stat-system.md §E.8 | to_dict keys sort + round-trip 字面级稳定 | §8 Decision |
| stat-system.md §E.10 | TYPO_WARN_DELTA = 5 + abs 溢出修复（符号比较） | §9 Decision（push_error 与 push_warning 路径） |
| stat-system.md §F.5 | 启动 config 校验（R-S6） | §10 Decision |
| stat-system.md §H.1–H.20 | 20 条 AC | §3–§10 Decision 整体让 AC 跑通的实装基础具备 |
| stat-system.md §I.1 / §I.4 | 9+1 项实装契约修复 | §1–§10 Decision 完整覆盖 |

## Performance Implications

- **CPU**：100 次 `change_stat` + 100 次 mock subscriber 回调总耗时 < 5 ms（H.12 锁定，3 次最差仍 < 5 ms，headless --release 构建）
- **Memory**：6 个 Dictionary 总占用极小（demo 范围 4 stats + 3 vars + 12 affinities + 章节字符串 + 已触发事件集合 ~30 条），< 1 KB
- **Load Time**：`reset_to_initial()` 一次性写入 19 个键值对，< 0.1 ms
- **Network**：N/A（demo 单机，无联网）

> 关键：`_emit_depth` 守卫是 `int +=1 / -=1`，零分配；CONNECT_DEFERRED 把 handler 调度到下一帧 idle，不挤占当前帧 physics_process 时间预算。

## Migration Plan

### 阶段 1：实装侧 9 项漂移修复（一次 PR）

实装责任 = `scripts/autoload/global_state.gd`。按 stat-system GDD §I.4 顺序：

1. 加 `class_name GlobalState`
2. 把 `_stats / _vars / _affinity / _triggered / _era_markers` 改 typed Dictionary[K,V]
3. `clamp(...)` 全部改 `clampi(...)`
4. 信号 payload 改 4 元 / 2 元（捕获 clamp 前 old_value 快照）
5. 合并 `AFFINITY_INIT` + 全局 `AFFINITY_MIN/MAX` 为 `AFFINITY_CONFIG`
6. `from_dict` 加 cast + clampi + push_warning（覆盖 stats / vars / affinity / chapter / triggered / unknown ID）
7. `to_dict` 加 keys sort（_triggered + _era_markers）
8. `change_*` 加 `_emit_depth` 守卫
9. `_ready` 加 `_validate_configs` 启动校验（违反 push_error + assert(false)）

### 阶段 2：调用点回归

`Grep -r "GlobalState\." scripts/` 找全部 12 个调用点，确认：
- 未调用不存在的 `set_stat / set_var / set_affinity`（应无）
- 未在信号 handler 内同步 change_*（应无）

### 阶段 3：测试夹具

`/test-setup` 装 gdunit4 → `tests/unit/stat_system/` 实现 H.1–H.20 共 20 个测试方法（按 §H 测试夹具契约 5 条）。

### 阶段 4：ADR Accepted

20 条 AC 全绿后，把本 ADR Status 从 `Proposed` 升 `Accepted`，并在 stat-system GDD §I.4 末尾标注"由 ADR-0001 落实"。

## Validation Criteria

- [ ] gdunit4 跑通 H.1–H.20 全 20 条 AC（含 H.12 性能预算）
- [ ] `Grep "set_stat\|set_var\|set_affinity"` 在 `scripts/` 中零匹配（负 API §3 强制）
- [ ] `Grep "AFFINITY_INIT\|AFFINITY_MIN\|AFFINITY_MAX"` 在 `scripts/` 中零匹配（已合并为 AFFINITY_CONFIG）
- [ ] 任何 `change_*` 在 signal handler 内同步触发新 `change_*` 时，dev console 立刻收到 push_error
- [ ] 启动一份 typo config（如 jiejie min=16, max=15）launch 时立即 assert(false) + push_error
- [ ] from_dict 加载越界 999 后属性面板显示 clamp 后值（10），dev console 含 push_warning
- [ ] `Grep "Dictionary\[" scripts/autoload/global_state.gd` 显示全部 5 个内部容器都有类型化声明

## Related Decisions

- **ADR-0002-autoload-contract**（同会话紧跟撰写）— 锁定 `[autoload]` 注册顺序，强制 GlobalState 在 SaveManager / SceneRouter / Dialogue / UIRoot 之前 `_ready()`。本 ADR 的 §10 启动 config 校验、§7 from_dict 静默契约、§F.5 load-path UI 契约都依赖该顺序成立。
- **GDD design/gdd/stat-system.md** — 本 ADR 是该 GDD 的实装承诺。每条 §C / §D / §E / §F.5 / §H 条款都对应本 ADR 的一段 Decision。
- **GDD design/gdd/systems-index.md 高风险项 #2** — 本 ADR 落地后，stat-system 的"被 9 个系统依赖" 风险从"接口未冻结"降为"已锁，可放心写下游"。
