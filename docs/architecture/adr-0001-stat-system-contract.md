# ADR-0001: Stat System Contract（v1 接口、信号、实装侧契约冻结）

## Status

Accepted

## Date

2026-05-31

## Last Verified

2026-05-31

## Decision Makers

- 元生项目作者会话（user）
- design-review Round-1 / Round-2 specialists：game-designer、systems-designer、qa-lead、godot-specialist
- creative-director（synthesis）
- 本 ADR 由 architecture-decision skill 在 stat-system GDD `Approved` 后起草

## Summary

冻结 `GlobalState`（Stat System）autoload 的 v1 公开接口、6 个类型化信号、6 个数据集合 schema，并锁定 stat-system GDD §I.4 列出的 8+1 项实装侧契约修复。本 ADR 是后续 12+ 个下游 GDD 与所有相关实装的依据；任何修改均须先更新本 ADR + GDD §C.5/§C.6/§F.5。

## Engine Compatibility

| Field | Value |
|-------|-------|
| **Engine** | Godot 4.6 |
| **Domain** | Core / Scripting（autoload、signal、Dictionary、clampi）|
| **Knowledge Risk** | HIGH — Godot 4.6 是 post-LLM-cutoff（cutoff: 2025-05；4.6: 2026-01） |
| **References Consulted** | `docs/engine-reference/godot/VERSION.md`、`breaking-changes.md`、stat-system GDD §I.4 第 2 项 typed Dictionary 复核、§I.2 autoload 加载顺序复核（均经 Web/Context7 官方文档确认） |
| **Post-Cutoff APIs Used** | `Dictionary[String, int]` typed 容器（Godot 4.4+ 已稳定，4.6 可用）；`clampi(a, mn, mx)` int-only clamp（核心，全版本一致）；`signal` 多参 payload；`Object.CONNECT_DEFERRED`；`Time.get_ticks_usec()`（性能 AC 用）|
| **Verification Required** | `_validate_configs` 启动校验在 Godot 4.6 编辑器内能 `assert(false)` 阻断启动；`Dictionary[String, int]` 反序列化 JSON 时浮点 cast 行为（H.11 AC）；signal 4 参 emit/connect 在 CONNECT_DEFERRED 模式下的栈溢出测试（H.20 AC）|

> **Note**: 本 ADR Knowledge Risk = HIGH。任何引擎升级（4.6 → 4.7 / 5.0）必须把本 ADR 标 `Superseded` 并重新写一份。

## ADR Dependencies

| Field | Value |
|-------|-------|
| **Depends On** | None |
| **Enables** | ADR-0002-autoload-contract（同会话顺序写）；12+ 下游 GDD（dialogue / cutscene-runner / event-flow / npc-system / item-system / era-marker / wallet-credit / combat-core / courage-resource / skill-tree / emotion-state / stat-panel-ui / save-load） |
| **Blocks** | 所有 stat-system H.1–H.20 AC 在本 ADR Accepted + 实装漂移修复完成前不可运行；下游 GDD 进入实现阶段前必须本 ADR Accepted |
| **Ordering Note** | autoload 注册顺序见 ADR-0002；本 ADR 仅锁数据契约。两份 ADR 同 stat-system §I 主题，可并行 Accepted。 |

## Context

### Problem Statement

stat-system 是《元生的六年级》Foundation 层中被 **9+ 系统硬依赖** 的属性容器与广播中枢。GDD 已通过两轮 full-mode design-review（Round-1 8 项 BLOCKING / Round-2 16 项 BLOCKING 全部 close）并 Approved。但目前：

1. `scripts/autoload/global_state.gd` 已落盘，但 `project.godot` 的 `[autoload]` 节**未注册** `GlobalState`，12 个调用点 parse 即报错。
2. 实装侧与 GDD §C.5 / §C.6 / §C.4 / §D.1 / §D.2 / §E.6 / §E.8 多处不一致——上一轮只改 GDD 没改代码（详见 §I.4）。
3. 没有 ADR 把 v1 数据契约 + 8+1 项实装漂移修复任务上锁。下游 GDD 与实现都 BLOCKED。

不立即决定的成本：每写一个下游 GDD（12+ 份）都会反复争论"GlobalState 接口/信号到底什么样"，且最终实装会在多处偏离 GDD。

### Current State

- `global_state.gd` 实装：3 参 signal（`stat_id, delta, new_value`）；全局 `AFFINITY_MIN/MAX = ±10`；无 typed Dictionary；`from_dict` raw 直写不 clamp；`to_dict` 不 sort；无再入守卫；无 `_validate_configs`；无 `class_name`；用 `clamp` 而非 `clampi`。
- GDD v2 契约（已 Approved）：4 参 signal（`stat_id, old_value, new_value, requested_delta`）；per-NPC `AFFINITY_CONFIG[npc_id] = {init, min, max}`；`Dictionary[String, int]` typed；`from_dict` 自愈式（cast + clampi + push_warning）；`to_dict` 内 `keys.sort()`；`_emit_depth` 再入守卫；`_validate_configs` 启动校验；`class_name GlobalState`；`clampi`。

实装侧与 GDD 漂移共 8+1 项。

### Constraints

- **Godot 4.6 已 pinned**（不允许降版）
- 项目已有 12 个 `GlobalState.foo()` 调用点（现有代码 / 后续 GDD 引用），autoload 名必须是 `GlobalState`
- `scripts/autoload/global_state.gd` 路径已被 GDD §I.1 锁死，不允许迁移
- gdunit4 尚未安装（H.* AC 跑不了）— 由独立的 `/test-setup` 处理，不属本 ADR 范围
- 所有 signal payload 形状对下游订阅 GDD 是**接口契约**——一旦 12+ 下游 GDD 开始引用就极难再改

### Requirements

- **R1 接口冻结**：v1 公开接口 11 个方法（C.5 表），`set_*` 绝对赋值禁止
- **R2 信号契约**：`stat_changed / var_changed / affinity_changed` 4 参；`chapter_changed` 2 参；`event_triggered / era_marker_added` 1 参
- **R3 数学正确性**：D.1 / D.2 公式在 INT64 极端值下不 wrap；D.3 边界正确广播
- **R4 数据驱动**：所有 stat / var / affinity 上下限必须从 `*_CONFIG` 读，下游禁止 hardcode
- **R5 序列化稳定**：`to_dict` 同 state 多次 dump 字面级相同（git diff / round-trip 稳定）
- **R6 自愈式 from_dict**：越界 / 浮点 / 未知 ID / 错类型容错，全部走 push_warning
- **R7 再入保护**：实装侧 `_emit_depth` 守卫 + 订阅侧 `CONNECT_DEFERRED` 双重保险
- **R8 启动校验**：`_validate_configs` 在 `_ready()` 第一时间 fail-fast
- **R9 性能**：100 次 `change_stat` + mock subscriber 单次 < 5ms（headless release）

## Decision

**接受 stat-system GDD v1 全部数据契约 + 8+1 项实装漂移修复**。本 ADR 把 GDD §C.5 / §C.6 / §C.1 / §C.4 / §D.1 / §D.2 / §E.6 / §E.8 / §F.5 的所有可代码化条款冻结为 v1，并定义实装责任。

### Architecture

```
                        ┌──────────────────────────────────┐
                        │      GlobalState (autoload)      │
                        │  Foundation Layer · 零外部依赖    │
                        ├──────────────────────────────────┤
                        │  6 数据集合（私有，禁止外部直写）  │
                        │   _stats     Dict[String, int]    │
                        │   _vars      Dict[String, int]    │
                        │   _affinity  Dict[String, int]    │
                        │   _triggered Dict[String, bool]   │
                        │   _era_markers Dict[String, bool] │
                        │   _chapter   String               │
                        │  +1 守卫：_emit_depth: int        │
                        ├──────────────────────────────────┤
                        │  11 公开方法（v1 frozen）         │
                        │   get_*  ×4                       │
                        │   change_*  ×3   (+ 再入守卫)     │
                        │   has_* / mark_* ×4               │
                        │   get_chapter / set_chapter       │
                        │   to_dict / from_dict             │
                        │   reset_to_initial                │
                        ├──────────────────────────────────┤
                        │  6 信号（v1 frozen）              │
                        │   stat_changed     (4 args)       │
                        │   var_changed      (4 args)       │
                        │   affinity_changed (4 args)       │
                        │   event_triggered  (1 arg)        │
                        │   era_marker_added (1 arg)        │
                        │   chapter_changed  (2 args)       │
                        └────────────┬─────────────────────┘
                                     │ signals (deferred recommended)
                                     ▼
        ┌────────────────┬──────────────────┬──────────────────┐
        │  Stat Panel UI │  Combat Core     │  NPC System      │  ...12+
        │  (subscribes   │  (subscribes     │  (subscribes     │
        │   stat_changed)│   stat/var)      │   affinity)      │
        └────────────────┴──────────────────┴──────────────────┘

        调用方向（写）：
           Cutscene Runner / Item / Wallet / Event Flow
              ── change_stat / change_var / change_affinity ──▶ GlobalState
              ── mark_triggered / mark_era_marker ──────────▶
              ── set_chapter ──────────────────────────────▶
              ── from_dict / to_dict / reset_to_initial ───▶ (SaveManager only)
```

### Key Interfaces

```gdscript
class_name GlobalState
extends Node

# ─── Signals (v1 frozen, 4-tuple where applicable) ──────────────────────────
signal stat_changed(stat_id: String, old_value: int, new_value: int, requested_delta: int)
signal var_changed(var_id: String, old_value: int, new_value: int, requested_delta: int)
signal affinity_changed(npc_id: String, old_value: int, new_value: int, requested_delta: int)
signal event_triggered(event_id: String)
signal era_marker_added(marker_id: String)
signal chapter_changed(old_chapter: String, new_chapter: String)

# ─── Configs (源数据，启动 fail-fast 校验 min ≤ init ≤ max) ──────────────
const STATS_CONFIG: Dictionary[String, Dictionary] = {
    "xuexi":    {"init": 3, "min": 0, "max": 10},
    "danliang": {"init": 1, "min": 0, "max": 10},
    "koucai":   {"init": 1, "min": 0, "max": 10},
    "tili":     {"init": 3, "min": 0, "max": 10},
}
const VARS_CONFIG: Dictionary[String, Dictionary] = {
    "xinjie":         {"init": 0, "min": 0, "max": 20},  # PROVISIONAL
    "kaguodu_xinli":  {"init": 0, "min": 0, "max": 10},
    "qianbao_xiuchi": {"init": 0, "min": 0, "max": 20},  # PROVISIONAL
}
const AFFINITY_CONFIG: Dictionary[String, Dictionary] = {
    "baoxianjin":   {"init": 0,  "min": -10, "max": 10},
    "baosimu":      {"init": 1,  "min": -10, "max": 10},
    "wangyan":      {"init": 1,  "min": -10, "max": 10},
    "zengjianming": {"init": 1,  "min": -10, "max": 10},
    "caozhengdong": {"init": -3, "min": -15, "max": 10},  # 宿敌 head room
    "huxiaodong":   {"init": 0,  "min": -10, "max": 10},
    "zhanglei":     {"init": 0,  "min": -10, "max": 10},
    "lijing":       {"init": 0,  "min": -10, "max": 10},
    "menwei_daye":  {"init": 0,  "min": -10, "max": 10},
    "fuqin":        {"init": 5,  "min": -10, "max": 10},
    "muqin":        {"init": 5,  "min": -10, "max": 10},
    "jiejie":       {"init": 8,  "min": -10, "max": 15},  # 被托住 head room
}
const AFFINITY_DEFAULT_MIN: int = -10
const AFFINITY_DEFAULT_MAX: int = 10
const TYPO_WARN_DELTA: int = 5

# ─── Public API (v1 frozen, 禁止扩 set_* 绝对赋值) ──────────────────────────
func get_stat(id: String) -> int
func change_stat(id: String, delta: int) -> void
func get_var(id: String) -> int
func change_var(id: String, delta: int) -> void
func get_affinity(npc_id: String) -> int
func change_affinity(npc_id: String, delta: int) -> void
func has_triggered(event_id: String) -> bool
func mark_triggered(event_id: String) -> void
func has_era_marker(marker_id: String) -> bool
func mark_era_marker(marker_id: String) -> void
func get_chapter() -> String
func set_chapter(chapter_id: String) -> void
func to_dict() -> Dictionary
func from_dict(data: Dictionary) -> void
func reset_to_initial() -> void
```

### Implementation Guidelines

实装责任落到 godot-gdscript-specialist。按 stat-system §I.4 列出的 8+1 项依次落地：

**1. `class_name GlobalState`**：文件首行追加。下游 typed access：`var gs: GlobalState = get_node("/root/GlobalState")`。

**2. Typed Dictionary K/V**：所有 6 个集合改为 `Dictionary[String, int]` / `Dictionary[String, bool]`。CONFIG 常量改 `Dictionary[String, Dictionary]`。

**3. `clampi(...)`**：所有 clamp 调用替换为 `clampi(...)`（D.1 / D.2），避免 JSON 浮点污染返回类型。

**4. 4 参 signal payload**：每个 `change_*` 函数：
```gdscript
func change_stat(id: String, delta: int) -> void:
    if _emit_depth > 0:
        push_error("[GlobalState] re-entrant change_* during signal handler — use call_deferred")
        return
    if not STATS_CONFIG.has(id):
        push_error("[GlobalState] unknown stat: %s" % id)
        return
    var cfg: Dictionary = STATS_CONFIG[id]
    var old_value: int = _stats[id]
    # 溢出安全：safe_delta 预收敛
    var safe_delta: int = clampi(delta, cfg.min - cfg.max, cfg.max - cfg.min)
    var new_value: int = clampi(old_value + safe_delta, cfg.min, cfg.max)
    if new_value == old_value:
        return  # effective_delta = 0，不广播也不警告
    _stats[id] = new_value
    _emit_depth += 1
    stat_changed.emit(id, old_value, new_value, delta)  # requested 传原始 delta
    _emit_depth -= 1
    # typo warning 在广播之后（effective ≠ 0 才到这）
    if delta > TYPO_WARN_DELTA or delta < -TYPO_WARN_DELTA:
        push_warning("[GlobalState] large delta on %s: %d (typical range [-%d, +%d])"
                     % [id, delta, TYPO_WARN_DELTA, TYPO_WARN_DELTA])
```
`change_var` / `change_affinity` 同构（`change_affinity` 改读 `AFFINITY_CONFIG[npc_id]` 而非全局常量；未知 npc_id `push_error`）。

**5. per-NPC AFFINITY_CONFIG**：删除 `AFFINITY_INIT / AFFINITY_MIN / AFFINITY_MAX`；新建 `AFFINITY_CONFIG`（含 12 行 + 2 个 fallback 全局常量）。`change_affinity` 用 `AFFINITY_CONFIG[npc_id].min/max`。

**6. `from_dict` 自愈式**：
```gdscript
func from_dict(data: Dictionary) -> void:
    reset_to_initial()  # 先回出厂态
    for id in data.get("stats", {}):
        if not STATS_CONFIG.has(id):
            push_warning("[GlobalState] from_dict: unknown stat %s — skipped" % id); continue
        var cfg: Dictionary = STATS_CONFIG[id]
        var raw = data["stats"][id]
        var v: int = int(raw)  # 防 JSON 浮点
        var clamped: int = clampi(v, cfg.min, cfg.max)
        if clamped != v:
            push_warning("[GlobalState] from_dict: %s out-of-range %s, clamped to %d" % [id, raw, clamped])
        _stats[id] = clamped
    # vars / affinity 同构
    # triggered: 接受 Array | Dict 两种历史形状（详见 GDD §E.8）
    var trig = data.get("triggered", [])
    if trig is Dictionary:
        for k in trig.keys():
            if not trig[k]:
                push_warning("[GlobalState] from_dict: triggered key with non-true value: %s" % k)
            _triggered[k] = true
    elif trig is Array:
        for k in trig: _triggered[k] = true
    else:
        push_warning("[GlobalState] from_dict: triggered field has unexpected type, ignored")
    # era_markers 同构
    # chapter
    var ch = data.get("chapter", "prologue")
    if not (ch in ["prologue", "ch1", "ch1_done"]):
        push_warning("[GlobalState] from_dict: out-of-range chapter %s" % ch)
    _chapter = ch
    # 整个 from_dict 路径不发任何 *_changed 信号（load 静默契约 §F.5）
```

**7. `to_dict` 内部 sort**：
```gdscript
func to_dict() -> Dictionary:
    var trig: Array = _triggered.keys()
    trig.sort()
    var era: Array = _era_markers.keys()
    era.sort()
    return {
        "stats":       _stats.duplicate(true),
        "vars":        _vars.duplicate(true),
        "affinity":    _affinity.duplicate(true),
        "triggered":   trig,
        "era_markers": era,
        "chapter":     _chapter,
    }
```

**8. `_emit_depth` 再入守卫**：见 §4 代码。每个 `change_*` 入口 check 后 emit 前 `_emit_depth += 1`，emit 后 `-= 1`；订阅 GDD 必须用 `Object.CONNECT_DEFERRED`（§F.5 invariant，由 `/consistency-check` 在订阅 GDD 完成后扫描）。

**9. `_validate_configs` 启动校验**：
```gdscript
func _ready() -> void:
    _validate_configs(STATS_CONFIG, VARS_CONFIG, AFFINITY_CONFIG)
    reset_to_initial()

func _validate_configs(stats_cfg: Dictionary, vars_cfg: Dictionary, aff_cfg: Dictionary) -> bool:
    var ok := true
    for ds in [stats_cfg, vars_cfg, aff_cfg]:
        for id in ds:
            var c: Dictionary = ds[id]
            if not (c.min <= c.init and c.init <= c.max and c.min <= c.max):
                push_error("[GlobalState] config invariant violated: %s min=%d init=%d max=%d"
                           % [id, c.min, c.init, c.max])
                ok = false
    if not ok:
        assert(false, "[GlobalState] config validation failed — see push_error above")
    return ok
```
单元测试通过把 `_validate_configs` 抽成独立方法（H.19 AC）注入伪 config 验证三种非法形态。

**触发顺序**：实装漂移修复**必须**在 `project.godot` 注册 `GlobalState`（ADR-0002）之前完成——否则 autoload 注册成功但启动时 `_validate_configs` 会立刻 assert，反而把项目卡住。先在 `global_state.gd` 改完，本地用 `--headless --check-only` 跑一遍语法检查，再合 ADR-0002。

## Alternatives Considered

### Alternative 1: 仅冻结 v1 接口，signal 仅代带 effective delta，推迟 4 参 + 再入守卫到后续 ADR

- **Description**：本 ADR 只锁 11 个方法签名 + per-NPC AFFINITY_CONFIG schema；`stat_changed` 等信号保留 GDD Round-1 之前的 3 参形态（`id, delta, new_value`）；再入守卫与 typed Dictionary 留到下一份 ADR。
- **Pros**：本 ADR 篇幅小、改动少；Round-1 草案可直接 Accepted；implementation lift 较轻
- **Cons**：违背 Round-2 creative-director synthesis 决议（4 参 payload 是 acknowledgment fantasy 的"effective vs requested"边界识别条件；GDD H.1/H.4/H.5/H.14/H.15 全部已经断言 4 参字段名）；再入守卫不立 = 第一个把 stat_changed 接到 cutscene 触发新 stat 改动的下游就要 fix；势必要写 ADR-0001-revision-1，反复改 12+ 下游 GDD
- **Estimated Effort**：本 ADR -50% / 实装 -30%；但后续 ADR + GDD 重做 +200%
- **Rejection Reason**：Round-2 已经把 4 参 + 再入守卫纳入 GDD v1；本 ADR 的责任就是**精确复述 GDD 已 Approved 的契约**，不是在 ADR 层重新讨论。拆解只会制造 ADR/GDD 不一致。

### Alternative 2: 拆为两份 ADR——"接口与信号" + "实装漂移与启动校验"

- **Description**：ADR-0001 = 11 接口 + 6 信号 schema + per-NPC AFFINITY_CONFIG（设计契约）；ADR-0001b = 8+1 实装漂移修复 + `_validate_configs` + `class_name`（实装契约）。两份同 stat-system 主题，ADR-0001b depends_on ADR-0001。
- **Pros**：设计契约 vs 实装契约逻辑边界清晰；godot-gdscript-specialist 改代码时只看 ADR-0001b；如果未来 v2 重写实装但保留接口，仅替换 ADR-0001b
- **Cons**：两份 ADR 必须同时 Accepted 才能进入实现阶段（实质等价于一份）；下游 GDD 引用时需要同时引两份，引用麻烦；stat-system §I.4 原文写"必须与 §I.1 同 ADR 处理"——拆出来违背 GDD
- **Estimated Effort**：相当
- **Rejection Reason**：GDD §I.4 已经明确"必须与 §I.1 同 ADR 处理"。两份合并写没有实质代价，且 ADR registry 与下游引用更简单。

## Consequences

### Positive

- **下游 GDD 解锁**：12+ 个下游 GDD（dialogue / cutscene-runner / npc-system / save-load 等）现在可以引用 v1 接口契约开始 `/design-system`
- **AC 可运行**：stat-system H.1–H.20 全部 20 条 AC 在实装漂移修复 + gdunit4 安装后可跑（依赖 ADR-0002 + `/test-setup`）
- **跨 GDD invariant 强制基线**：§F.5 7 条 invariant（数值不得 hardcode / load 路径 UI / event_id idempotent / CONNECT_DEFERRED / 启动校验等）都有了 ADR 出处
- **acknowledgment fantasy 可证伪**：4 参 signal payload 让 stat-panel-ui 在边界场景区分"真发生"vs"被吃掉"，pillar 不再是 hand-wave
- **实装与设计零漂移**：8+1 项漂移在同 ADR 内一并修复，避免"GDD 改了代码没改"的二次评审

### Negative

- **接口冻结成本**：v1 接口出错（如 4 参字段名 typo / signal arg 顺序）回滚成本极高，需重做 12+ 下游引用与 H.1–H.20 测试用例
- **typed Dictionary 4.4+ 锁死**：项目无法在不重写本 ADR 的前提下降到 Godot 4.3 以下
- **`_emit_depth` 守卫开销**：每次 `change_*` 多 1 次 int 比较 + 2 次 +/- 操作（可忽略，但记录在案）
- **PROVISIONAL 数值悬而未决**：`xinjie / qianbao_xiuchi.max = 20` 在终章场景设计前不冻结；下游 GDD 必须从 `VARS_CONFIG[id].max` 读，不得 hardcode（§F.5 已约束）

### Neutral

- 序章 + 第一章 demo 范围内的 30–60 条 lookup 表数值不在本 ADR 范围（属于 cutscene-runner / event-flow GDD）
- 章节状态机的运行时白名单校验由 GDD 规则 + code review 兜底，不在代码层强制（Open Question Q2）

## Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| 实装漂移修复在 PR 阶段被部分合并（如 4 参 signal 改了但 `_emit_depth` 漏） | Medium | High | godot-gdscript-specialist 提交一个 PR 包含全部 8+1 项，PR 模板要求逐项打勾对照本 ADR Implementation Guidelines |
| H.19 `_validate_configs` 在 `_ready()` assert 阻断启动，新人开发无法定位 | Low | Medium | push_error msg 必须包含 stat id + min/init/max 值；CLAUDE.md 后续追加"启动 assert 时第一件事是检查 STATS_CONFIG 各表" |
| 下游 GDD 写 affinity-changing 事件时漏掉 §F.5 R-G3 idempotent 约束 | Medium | Medium | `/consistency-check` 在 event-flow / npc-system GDD Approved 后扫描事件表（skill 待实装，过渡期 PR review 兜底）|
| typed Dictionary 在 Godot 4.6 `from_dict` JSON 反序列化时不接受异构 value（如 `{"xuexi": 999.0}` 进 `Dictionary[String, int]`） | Low | Low | from_dict 路径已经 `int(raw)` 显式 cast；H.11 AC 显式覆盖浮点 cast；JSON 解码到顶层用 `Dictionary`（非 typed），自愈路径再 cast |
| 4 参 signal emit 在 CONNECT_DEFERRED 下 payload 序列化开销变大 | Low | Low | demo 范围每帧 < 5 次 `change_*`；H.12 perf AC 100 次 < 5ms 已覆盖最坏路径 |

## Performance Implications

| Metric | Before（v0 实装） | Expected After（v1） | Budget |
|--------|------------------|---------------------|--------|
| `change_stat` 单次（含 emit + 1 mock subscriber） | < 50 µs | < 50 µs（多 1 次 int 比较 + safe_delta clamp） | < 50 µs |
| 100 次 `change_stat` 连续（H.12 perf AC，含 mock） | 未测 | < 5 ms（headless release，重复 3 次取最差） | < 5 ms |
| Memory（全部 6 集合 + 守卫字段） | ~3 KB | ~3 KB（typed Dict 反而更紧凑） | < 16 KB |
| `_validate_configs` 启动开销 | N/A | < 100 µs（19 项 entry × 3 次比较） | < 1 ms |
| `to_dict` + sort（满状态：~30 triggered + ~10 era_markers） | < 100 µs | < 200 µs（多 2 次 sort）| < 1 ms |

预算来源：CLAUDE.md → technical-preferences → Performance Budgets（60 fps / 16.6 ms 帧预算 / Stat System 是 Foundation 层零热路径）。

## Migration Plan

1. **新建分支** `feat/adr-0001-stat-system-contract`
2. **改 `scripts/autoload/global_state.gd`**：按 Implementation Guidelines §1–§9 顺序实装；逐项 commit（小步快跑、commit message 引用本 ADR）
3. **本地语法检查**：`godot --headless --check-only --path . scripts/autoload/global_state.gd`
4. **暂不**注册 autoload（等 ADR-0002 处理）
5. **撰写并 Accept ADR-0002-autoload-contract**（同会话顺序）
6. **修改 `project.godot`**：按 ADR-0002 加 `GlobalState` autoload 注册（最前）
7. **本地启动 Godot 4.6 编辑器**：验证不报 `Identifier 'GlobalState' not declared`、`_validate_configs` 不 assert
8. **运行 `/test-setup`** 装 gdunit4（独立 ADR / `/test-setup` skill 处理）
9. **写 `tests/unit/stat_system/`**：H.1–H.20 共 20 条 AC，全部 PASS
10. **更新 `docs/registry/architecture.yaml`**：本 ADR Phase 5 处理（state ownership / interface contracts / forbidden patterns / api decisions / performance budgets）
11. **PR 合 master**：标题 `feat(stat-system): freeze v1 contract per ADR-0001`，引用本 ADR 与 stat-system GDD

**Rollback plan**：若 H.1–H.20 出现 ≥ 3 项 BLOCKING 失败：(a) 不回滚整个 ADR，按 push_error / push_warning / failed AC 反推具体哪一项实装漂移没改对；(b) 在该项上单独 revision；(c) 12+ 下游 GDD 还没开始引用接口前，调整成本可接受。一旦下游 GDD 引用启动，rollback 成本陡增——所以 H.* AC 必须先全绿再开始下游 GDD `/design-system`。

## Validation Criteria

- [ ] `scripts/autoload/global_state.gd` 通过 godot-gdscript-specialist code review
- [ ] `class_name GlobalState` 落地；6 集合全部 typed Dictionary
- [ ] 6 信号全部按 v1 schema（4 / 4 / 4 / 1 / 1 / 2 args）
- [ ] `_emit_depth` 再入守卫在所有 3 个 `change_*` 函数生效
- [ ] `_validate_configs` 在 `_ready()` 调用、单元测试可注入伪 config
- [ ] `clampi` 全面替代 `clamp`
- [ ] `from_dict` 自愈式（cast / clamp / push_warning）覆盖 stats / vars / affinity / triggered / chapter 五条路径
- [ ] `to_dict` 对 `_triggered` / `_era_markers` keys `sort()`
- [ ] `AFFINITY_CONFIG` 12 行 + 2 fallback 常量全部到位
- [ ] H.1–H.20 共 20 条 gdunit4 AC 全部 PASS（依赖 ADR-0002 Accepted + `/test-setup` 完成）
- [ ] `docs/registry/architecture.yaml` 5 类条目（state ownership / interfaces / api_decisions / forbidden_patterns / performance_budgets）写入，referenced_by 至少含本 ADR 路径
- [ ] PR 合并后跑一次 `/architecture-review`（在 fresh session 中）覆盖率自检

## GDD Requirements Addressed

| GDD Document | System | Requirement | How This ADR Satisfies It |
|-------------|--------|-------------|--------------------------|
| `design/gdd/stat-system.md` | Stat System | §C.5 v1 公开接口（11 方法） | Decision § Key Interfaces 完整声明 11 个方法签名，禁止 `set_*` 绝对赋值 |
| `design/gdd/stat-system.md` | Stat System | §C.6 6 信号契约（4/4/4/1/1/2 args） | Decision § Key Interfaces 完整声明 6 信号；§Implementation Guidelines §4 给出 emit 顺序；再入守卫见 §8 |
| `design/gdd/stat-system.md` | Stat System | §C.4 per-NPC AFFINITY_CONFIG | Decision § Key Interfaces 完整列出 12 行 AFFINITY_CONFIG（jiejie.max=15 / caozhengdong.min=-15）+ 2 fallback 常量 |
| `design/gdd/stat-system.md` | Stat System | §D.1 / §D.2 溢出安全 clamp | Implementation Guidelines §4 / §5 给出 `safe_delta = clampi(delta, mn-mx, mx-mn)` 预收敛代码 |
| `design/gdd/stat-system.md` | Stat System | §E.6 from_dict 自愈式 | Implementation Guidelines §6 完整 from_dict 代码（cast / clampi / push_warning / Array \| Dict 容错） |
| `design/gdd/stat-system.md` | Stat System | §E.8 to_dict 内 sort | Implementation Guidelines §7 完整 to_dict 代码 |
| `design/gdd/stat-system.md` | Stat System | §E.3 / §C.6 再入守卫 | Implementation Guidelines §4 / §8 `_emit_depth` 模式；§F.5 invariant 推订阅侧 CONNECT_DEFERRED |
| `design/gdd/stat-system.md` | Stat System | §F.5 启动 config 校验 invariant | Implementation Guidelines §9 `_validate_configs` 完整代码 + assert(false) 阻断启动 |
| `design/gdd/stat-system.md` | Stat System | §H.1–H.20 AC 可执行 | Validation Criteria 把"H.* PASS"列为本 ADR 验收条件之一；Migration Plan §9 锁顺序 |
| `design/gdd/stat-system.md` | Stat System | §I.4 实装侧 8+1 项契约漂移 | Implementation Guidelines §1–§9 与 §I.4 列表逐项对应；Validation Criteria 逐项打勾 |

## Related

- `design/gdd/stat-system.md`（v1 GDD，状态：Approved 2026-05-31）
- `design/gdd/reviews/stat-system-review-log.md`（两轮 full-mode + lean re-review 历史）
- `design/gdd/systems-index.md`（Stat System #1，状态：Approved）
- `scripts/autoload/global_state.gd`（实装目标文件）
- `docs/engine-reference/godot/VERSION.md`（Godot 4.6 pinned）
- `ADR-0002-autoload-contract.md`（同会话顺序写，注册 + 加载顺序）
- `.claude/docs/technical-preferences.md`（Naming Conventions / Performance Budgets / 引擎专家路由）

---

> **下一步路径**：
> 1. ADR-0001 Accepted → ADR-0002 起草并 Accepted（同会话）
> 2. godot-gdscript-specialist 改 `global_state.gd`（按 Implementation Guidelines §1–§9）
> 3. `/test-setup` 装 gdunit4
> 4. 写 H.1–H.20 共 20 条 gdunit4 AC
> 5. 在 fresh session 跑 `/architecture-review` 验证覆盖率
> 6. `/design-system asset-loading` 继续 retrofit 设计顺序 #2
