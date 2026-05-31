# Stat System

> **Status**: Revised v2 (pending lean re-review) — Round-1 8 项 + Round-2 16 项 BLOCKING 全部处理 2026-05-31
> **Author**: 元生项目（user + design-system 主会话；qa-lead 介入 Section H；systems-designer 介入 Section D）
> **Last Updated**: 2026-05-31（Round-2 design-review 修订后）
> **Implements Pillar**: 被看见 / 被记住（infrastructure 层支撑）
> **Review Mode**: full × 2（Round-1 4 specialists + creative-director；Round-2 4 specialists + creative-director synthesis 完成于 2026-05-31）
> **Creative Director Review**: 两轮均已完成（Round-1 synthesis: NEEDS REVISION → 修订后 8 项 BLOCKING 全部处理；Round-2 synthesis: NEEDS REVISION → 修订后 16 项 BLOCKING 全部处理）

## Overview

《元生的六年级》的 Stat System 是 Foundation 层的属性容器与广播中枢：它存储 4 项显性属性（学习 / 胆量 / 口才 / 体力，0–10）、3 项隐性变量（心结 / 卡过渡届心理度 / 钱包羞耻度，整数有界）、12 位 demo NPC 的好感度（−10 到 +10）、章节进度、已触发事件 ID 集合、已点亮的时代切片标记，并通过类型化信号广播每一次变化，供 Dialogue / Cutscene Runner / NPC / Item / Combat / UI / Save 等下游订阅。

在玩家视角，它是"被看见"和"被记住"的载体：每一次主动报全名、每一次蹲下不吭声、每一次摸口袋不敢进小卖部，都会在这里留下整数级别的痕迹——属性面板的飘字让玩家立刻看到自己的选择被系统接住，隐性变量则在几小时之后让一段对白的语气悄悄变了。它不是一个游戏机制，但它是项目的 Pillar 承诺里"被看见 / 被记住 / 被允许"三条得以成立的全部底座。

本系统已有事实源：`docs/design/属性变量定义-spec.md`（设计契约）与 `scripts/autoload/global_state.gd`（已实装 autoload 单例）。两者口径完全一致，本 GDD 的职责是把它们规范化为 8 节合规设计文档并冻结接口。数据契约的工程实现细节（autoload 加载顺序、序列化版本、信号订阅模式）将由后续 ADR 锁定（占位：`ADR-XXXX-stat-system-contract`）。

## Player Fantasy

Stat System 的玩家幻想不是 power fantasy，而是 **acknowledgment fantasy** —— 一种"游戏看见了我刚才那一下"的踏实感。

**直接层（4 项显性属性）**：玩家每选一次主动报全名、每一次喊老师、每一次推回去，属性面板会立刻弹出 +1 / +2 飘字。这不是经验值条爬满的爽感，更像第一次摸到答题卡发下来的"老师真的看了一眼"——一个细小的、整数级别的、没有特效的回执。玩家会逐渐建立直觉：胆量 +1 不是变强，是元生今天比昨天敢一点点。当某个对白选项因为"胆量 ≥ 3"而第一次解锁，玩家会感到那不是奖励，是自己一路攒出来的资格。

**隐性层（心结 / 钱包羞耻度 / 卡过渡届心理度）**：这一层不弹飘字，没有面板。玩家蹲下不吭声、转身离开、低头摸口袋的时候，系统在背后默默 +1，玩家本人并不知道。直到几小时甚至几个章节之后，鲍师母的某句对白措辞悄悄变了，元生回宿舍躺下时屏幕暗角加深了——玩家会突然意识到："它一直在记。" 这种被记忆带来的慢热羞涩感，对应 game concept 里"那些'心结 +1'会以某种方式回到你身上"的承诺。

**参考体感**：直接层接近《Persona》系列的属性反馈节奏（看得见、可经营、不打断节拍）；隐性层接近《Night in the Woods》《极乐迪斯科》的被动累积感（不告诉你正在被计入，但终究会回到对白里）。但本作的语气更克制——所有飘字都是单色无音效的整数，避免任何"奖励感"，让玩家保留"这只是真实童年的一次次小动作"的代入。

**服务的 Pillar**：直接对应"**被看见**"（飘字即回执）、"**被记住**"（隐性变量驱动后续对白基调）、"**被允许**"（A 选项也是合法路径，胆量 -1 不是负分，是另一种性格的累积）。

## Detailed Design

### Core Rules

#### C.1 数据集合（state container）

Stat System 维护 6 个集合：

| 集合 | 类型 | 内容 | 范围 |
|---|---|---|---|
| `_stats` | `Dictionary[String → int]` | 4 项显性属性 | 见 C.2 表 |
| `_vars` | `Dictionary[String → int]` | 3 项隐性变量 | 见 C.3 表 |
| `_affinity` | `Dictionary[String → int]` | 12 个 NPC 好感度 | 见 C.4 表 |
| `_triggered` | `Dictionary[String → bool]`（作 Set 用） | 已触发事件 ID 集合 | 任意非空字符串 |
| `_era_markers` | `Dictionary[String → bool]`（作 Set 用） | 已点亮的时代切片 ID 集合 | 任意非空字符串 |
| `_chapter` | `String` | 当前章节 ID | `prologue` / `ch1` / `ch1_done`（demo 范围内）|

> 注：所有集合在 `_ready()` 经 `reset_to_initial()` 用 `STATS_CONFIG / VARS_CONFIG / AFFINITY_INIT` 完整初始化；运行时不允许 dictionary 为空导致 KeyError。

#### C.2 显性属性表（4 项，UI 可见）

| ID | 名称 | 初值 | 下限 | 上限 | 含义 / Demo 内主要变更点 |
|---|---|---|---|---|---|
| `xuexi` | 学习 | 3 | 0 | 10 | 课业能力。Demo: 月考排名（ch1/12）+1 |
| `danliang` | 胆量 | 1 | 0 | 10 | 冲突承受度。Demo: 曹正东抢钱 A −1 / B +1 / C +2（且 C 需胆量 ≥ 3） |
| `koucai` | 口才 | 1 | 0 | 10 | 表达能力。Demo: 报全名 +1 / 主动搭话王炎 +1 / 蒸饭盒道谢 +1 / 跳跳糖 C +1 |
| `tili` | 体力 | 3 | 0 | 10 | 体能。Demo 范围内不影响选项（埋点）|

#### C.3 隐性变量表（3 项，UI 不可见）

| ID | 名称 | 初值 | 下限 | 上限 | 含义 / Demo 内主要变更点 |
|---|---|---|---|---|---|
| `xinjie` | 心结 | 0 | 0 | 20 | "卡过渡届最后一届"心理压力。ch1/12 月考转身 +1；小卖部 B +1；曹正东后回宿舍 +2 |
| `kaguodu_xinli` | 卡过渡届心理度 | 0 | 0 | 10 | 对身份的明确感知。序章走廊偷听老师 +1 |
| `qianbao_xiuchi` | 钱包羞耻度 | 0 | 0 | 20 | 路过/进入小卖部摸口袋的羞耻感。序章首次路过 +1；小卖部 A +1；曹正东后回宿舍 +2 |

#### C.4 NPC 好感度表（12 项，UI 不可见）

每个 NPC 拥有 per-NPC `{init, min, max}` 配置（schema 与 STATS_CONFIG / VARS_CONFIG 同构）。绝大多数 NPC 用全局默认 `[-10, +10]`；`jiejie` / `caozhengdong` 因叙事承重需要更大头室，配独立上下限。

| ID | 角色 | init | min | max | 备注 |
|---|---|---|---|---|---|
| `baoxianjin` | 鲍先进（班主任） | 0 | −10 | +10 | 默认范围 |
| `baosimu` | 鲍师母 | 1 | −10 | +10 | 默认范围 |
| `wangyan` | 王炎 | 1 | −10 | +10 | 默认范围 |
| `zengjianming` | 曾建明 | 1 | −10 | +10 | 默认范围 |
| `caozhengdong` | 曹正东 | −3 | **−15** | +10 | 留出"宿敌"下行空间（post-demo 第八章 BOSS 战 D 选项铺垫） |
| `huxiaodong` | 胡晓东 | 0 | −10 | +10 | 默认范围 |
| `zhanglei` | 张磊 | 0 | −10 | +10 | 默认范围 |
| `lijing` | 李静 | 0 | −10 | +10 | 默认范围 |
| `menwei_daye` | 门卫大爷 | 0 | −10 | +10 | 默认范围 |
| `fuqin` | 父亲 | 5 | −10 | +10 | 默认范围 |
| `muqin` | 母亲 | 5 | −10 | +10 | 默认范围 |
| `jiejie` | 姐姐 | 8 | −10 | **+15** | "被托住" pillar 承重 NPC，需要 ≥ 5 次暖意累积空间 |

**Schema 实现注**：`AFFINITY_CONFIG` 取代旧 `AFFINITY_INIT`，键为 npc_id，值为 `{init: int, min: int, max: int}`。全局常量 `AFFINITY_DEFAULT_MIN = -10` / `AFFINITY_DEFAULT_MAX = +10` 仅作为 fallback——本表 12 行已全部展开，避免歧义；新增 NPC 必须先在表中声明范围再开始 change_affinity。

具体增量见 NPC System GDD（[[npc-system]]，待写）；Stat System 只保证存储与广播。

#### C.5 公开接口冻结（v1）

```gdscript
# 显性属性
get_stat(id: String) -> int
change_stat(id: String, delta: int) -> void
# 隐性变量
get_var(id: String) -> int
change_var(id: String, delta: int) -> void
# NPC 好感度
get_affinity(npc_id: String) -> int
change_affinity(npc_id: String, delta: int) -> void
# 已触发事件
has_triggered(event_id: String) -> bool
mark_triggered(event_id: String) -> void
# 时代切片标记
has_era_marker(marker_id: String) -> bool
mark_era_marker(marker_id: String) -> void
# 章节
get_chapter() -> String
set_chapter(chapter_id: String) -> void
# 序列化
to_dict() -> Dictionary
from_dict(data: Dictionary) -> void
reset_to_initial() -> void
```

**未提供 `set_stat / set_var / set_affinity`（绝对赋值）**：所有变更必须经 `change_*(id, delta)`，以保证信号广播 delta 值供 UI 飘字使用。如果未来需要绝对赋值（例如 cheat / 测试），通过 `from_dict(...)` 注入完整状态而不是 set。

#### C.6 信号契约

```gdscript
signal stat_changed(stat_id: String, old_value: int, new_value: int, requested_delta: int)
signal var_changed(var_id: String, old_value: int, new_value: int, requested_delta: int)
signal affinity_changed(npc_id: String, old_value: int, new_value: int, requested_delta: int)
signal event_triggered(event_id: String)
signal era_marker_added(marker_id: String)
signal chapter_changed(old_chapter: String, new_chapter: String)
```

**chapter_changed 用 (old, new) 而非单参（Round-2 修订）**：与 stat/var/affinity 信号在"是否需要订阅端缓存上一次值"上保持对称。Era Marker / Cutscene Runner 可以基于 `(old, new)` 判定方向（例如"是否从 ch1 回退到 prologue 的非法路径，由 from_dict 触发"），订阅端无需自缓存 `_last_chapter`。`from_dict(...)` 路径仍按 §F.5 静默契约不发该信号，所以 `(old, new)` 仅出现在 `set_chapter` 显式调用路径。

**为什么是四元组**（设计 rationale，design-review 修订）：
- `old_value` / `new_value` 让订阅者直接计算 `effective_delta = new_value - old_value`，不需要在订阅端缓存上一次值
- `requested_delta` 保留调用方"试图改变多少"的原始意图——当 effective ≠ requested（clamp 边界）时，UI 可以选择"软"反馈（"你试过了"），而不是显示与状态不匹配的飘字
- 三者并存让 Stat Panel UI 在 `acknowledgment fantasy` 边界场景拥有完整信息：`requested = effective` 时显示 +N 飘字；`|requested| > |effective|` 时（典型为 floor/ceiling 吞掉）UI 可改为静默或"软"反馈

**广播规则**：
- `stat_changed / var_changed / affinity_changed`：仅在 *clamp 后的* `new_value` 与 `old_value` 不同时广播（即 `effective_delta ≠ 0`）。`old_value` 是 clamp 前的旧值快照；`new_value` 是 clamp 后的最终值；`requested_delta` 是调用方传入的原始 delta（**不**是 clamp 修剪后的值）。
- `event_triggered / era_marker_added`：仅在该 ID 是 *第一次* 进入集合时广播；重复 mark 静默忽略。
- `chapter_changed`：仅在 `new_chapter ≠ old_chapter` 时广播；payload 携带 `(old_chapter, new_chapter)`。

**再入保护契约（Round-2 修订新增）**：
- 实装端：每个 `change_*` 在 emit 之前增量 `_emit_depth`，emit 之后递减；进入函数时若 `_emit_depth > 0` 直接 `push_error("[GlobalState] re-entrant change_* during signal handler — use call_deferred")` 并 return（不修改任何集合、不发新信号）。
- 订阅端：建议 `connect(handler, Object.CONNECT_DEFERRED)`，把"不得在 handler 内同步 change_*"从调用方负担转给订阅方契约。这一条由 §F.5 cross-GDD invariant 推给所有订阅 GDD（[[stat-panel-ui]] / [[combat-core]] / [[npc-system]] 等）。

**底/顶完全吞掉时不广播**（`effective_delta = 0`）：见 §D.3 与 §E.1 — 维持"acknowledgment fantasy 不假装看见"的设计意图；player 在底/顶值仍执行的"动作"由 Stat Panel UI 选择是否给"软"反馈（如 0.5 秒灰色 "—"），属于 [[stat-panel-ui]] GDD 的设计空间，本系统不强制。

### States and Transitions

Stat System 本身是无状态机器（只有数据），但 `_chapter` 字段实际是一个有限状态枚举。

**Chapter state machine**（demo 范围）：

| From | To | Trigger | Notes |
|---|---|---|---|
| —（启动） | `prologue` | `_ready()` / `reset_to_initial()` | 初始 |
| `prologue` | `ch1` | Event Flow 完成序章末事件 + `set_chapter("ch1")` | demo 范围内的唯一前进 |
| `ch1` | `ch1_done` | Event Flow 完成 ch1 末 cutscene + `set_chapter("ch1_done")` | demo 终点 |
| 任意 | 任意 | `from_dict(saved)` | 仅经存档读取，不允许业务代码反向跳 |

> 章节回退（`ch1 → prologue` 等）**仅** 在 `from_dict` 路径合法。Cutscene Runner / Dialogue 不应直接调 `set_chapter` 回退。

### Interactions with Other Systems

数据流方向：**Stat System ← inputs ← 业务系统**；**Stat System → signals → 订阅者**。所有交互通过 6 个公开接口 + 6 个信号，不允许下游直接读 `_stats / _vars / ...` 私有字段。

| 下游系统 | 调用 / 订阅 | 接口契约 |
|---|---|---|
| **Dialogue** | 调用：`get_stat / get_var / get_affinity / has_triggered / has_era_marker / get_chapter`<br>订阅：无（条件查询而已） | Dialogue 节点的 `condition` 字段读取 stat/var/affinity 值用于分支；它**不**修改属性，修改通过 `effect` 字段委派给 Cutscene Runner |
| **Cutscene Runner** | 调用：`change_stat / change_var / change_affinity / mark_triggered / mark_era_marker / set_chapter`<br>订阅：无 | Cutscene 指令"`stat_change xuexi 1`"直译为 `change_stat("xuexi", 1)`；指令"`mark_event ch1/12_yuekao_ranking`"直译为 `mark_triggered(...)` |
| **NPC System** | 调用：`get_affinity / change_affinity`<br>订阅：`affinity_changed` | NPC 出场逻辑根据 affinity 选问候台词；初值表此 GDD C.4 已固定，NPC GDD 引用而不重定义 |
| **Item System** | 调用：`change_stat / change_var / mark_triggered`（道具触发的属性变化）<br>订阅：无 | 道具不进背包，直接以"获得道具"事件触发属性变更并 `mark_triggered` |
| **Era Marker** | 调用：`mark_era_marker / has_era_marker`<br>订阅：`era_marker_added`（弹 toast） | toast UI 订阅信号；累积逻辑（终章读集合大小）由 Era Marker GDD 处理 |
| **Wallet & Credit** | 调用：`change_var qianbao_xiuchi / change_affinity baosimu` | 钱包不属于 stat（金额是独立计数器），但赊账影响 `qianbao_xiuchi`、`affinity_baosimu` |
| **Combat Core / Courage / Skill / Emotion** | 调用：`get_stat danliang / get_var xinjie / get_var qianbao_xiuchi`<br>订阅：`stat_changed / var_changed`（用于实时刷新情绪状态判定）| 战斗 4 子系统读胆量决定技能可达性；读心结/钱包羞耻度决定"自卑"情绪 |
| **Stat Panel UI** | 订阅：`stat_changed`（飘字 + 数字刷新） | 仅订阅显性属性变化；不订阅 var / affinity（设计上不可见）|
| **Save / Load** | 调用：`to_dict() / from_dict(data) / reset_to_initial()` | 全量序列化；版本字段由 SaveManager 在外层 wrapper 添加，本系统不感知 save schema 版本 |

**反向规则（Forbidden）**：
- 任何系统不得绕过 `change_*` 接口直接写私有字段
- 任何系统不得在订阅信号回调里同步触发新的 `change_*`（防止信号风暴），如必要请用 `call_deferred`
- Dialogue 不允许直接调 `change_stat`；属性变更必须由 Cutscene Runner 执行（保证 cutscene 是"行为权威"）

## Formulas

### D.1 stat_clamp / var_clamp（显性属性、隐性变量共用）

```
# 数学定义（理想模型）
new_value = clampi(current_value + delta, min, max)

# 实装契约（Round-2 修订新增，溢出安全）：必须先把 delta 预收敛到安全区间再加，避免 INT64 wrap：
safe_delta  = clampi(delta, min - max, max - min)   # 任何 delta 在该区间内加到 current 都不会 wrap
new_value   = clampi(current_value + safe_delta, min, max)
```

| Variable | Symbol | Type | Range | Description |
|---|---|---|---|---|
| current_value | c | int | [min, max] | 该 ID 当前值（`_stats[id]` 或 `_vars[id]`） |
| delta | d | int | 调用方传入的原始增量 | 指南：[−3, +3]（demo 典型）；公式不强制 |
| safe_delta | d′ | int | [min−max, max−min] | clamp 修剪后用于加法的安全增量；保证 c + d′ 不溢出 |
| min / max | m / M | int | 显性 [0, 10]；xinjie / qianbao [0, 20]；kaguodu [0, 10] | 该 ID 在配置表里的上下限 |
| new_value | n | int | [min, max] | 最终 clamp 后值 |

**Output Range**：恒在 `[min, max]` 内（clamp 硬保证）。
**溢出安全说明**：朴素 `clampi(c + d, min, max)` 在 `d = INT64_MAX` 且 `c > 0`（或 `d = INT64_MIN` 且 `c < 0`）时，加法本身会 wrap 成相反符号的极端值，再 clamp 反而落到错误一端（min/max 颠倒）。预 clamp `safe_delta = clampi(d, m - M, M - m)` 把 d 收敛到任何 c 加上都不溢出的安全区间——effective_delta 与原 delta 在合法范围内（|d| ≤ M − m）时完全相同，只在病态超大 delta 时把绝对值吃到能安全计算的最大值。`requested_delta` 信号字段仍传**原始** d（不是 d′），由 §C.6 / §D.3 保证。
**Example**：koucai 初值 1，demo 内依次触发 4 次 +1（报全名 / 主动搭话王炎 / 蒸饭盒道谢 / 跳跳糖 C），每步 clamp 后值依次为 2, 3, 4, 5。

> Demo 内不会出现满值再 +1 的情况（最高目标值 ≤ 6），但公式必须在满值场景安全（见 Section E.1）。

### D.2 affinity_clamp（NPC 好感度，per-NPC 范围）

```
# 数学定义
new_affinity = clampi(current + delta, AFFINITY_CONFIG[npc_id].min, AFFINITY_CONFIG[npc_id].max)

# 实装契约（与 D.1 同构的溢出安全）：
safe_delta   = clampi(delta, npc.min - npc.max, npc.max - npc.min)
new_affinity = clampi(current + safe_delta, npc.min, npc.max)
```

| Variable | Symbol | Type | Range | Description |
|---|---|---|---|---|
| current | a | int | [npc.min, npc.max] | 该 NPC 当前好感（`_affinity[npc_id]`） |
| delta | d | int | 指南：[−3, +3]（demo 典型；超出 ±5 由 §E.10 push_warning 提示） | 调用方请求的好感增量 |
| AFFINITY_CONFIG[npc_id].min | npc.min | int | 默认 −10；jiejie/caozhengdong 等覆写见 §C.4 | 该 NPC 的下限 |
| AFFINITY_CONFIG[npc_id].max | npc.max | int | 默认 +10；jiejie 覆写为 +15 | 该 NPC 的上限 |
| new_affinity | n | int | [npc.min, npc.max] | clamp 后的最终值 |

**Output Range**：恒在 per-NPC `[min, max]` 内（clamp 硬保证）。
**Example 1（默认范围）**：曹正东初值 −3、范围 [−15, +10]，玩家"喊老师"使 `change_affinity("caozhengdong", -1)` → `clamp(-3 + (-1), -15, +10) = -4`。
**Example 2（jiejie 扩展范围）**：jiejie 初值 8、范围 [−10, +15]，连续 5 次 +1 暖意 → 8 → 9 → 10 → 11 → 12 → 13。第 6 次 +1 → 14；第 8 次到达 15 顶；第 9 次 +1 触发 `effective_delta = 0`，不广播（按 §D.3）。
**Example 3（fallback）**：若未来章节扩展引入 npc_id 不在 `AFFINITY_CONFIG` 中，使用 `AFFINITY_DEFAULT_MIN = -10` / `AFFINITY_DEFAULT_MAX = +10`；同时由 §E.2 修订规则触发 push_error。

### D.3 delta_broadcast_predicate（信号广播判定）

```
should_broadcast = (new_value != old_value)
```

| Variable | Symbol | Type | Range | Description |
|---|---|---|---|---|
| old_value | c | int | [min, max] | clamp 前的旧值快照 |
| new_value | n | int | [min, max] | D.1 / D.2 的输出 |
| should_broadcast | b | bool | {true, false} | 是否发出对应的 `*_changed` 信号 |

**Output Range**：true / false。
**Signal payload 语义**：当 `should_broadcast = true` 时，广播 `(id, old_value, new_value, requested_delta)`。订阅者可由 `effective_delta = new_value - old_value` 计算实际变化量；`requested_delta` 始终是调用方传入的原始值（**不被** clamp 修剪），允许 UI 在 `|requested| > |effective|` 时识别"player 试图但被吃掉"的边界场景。

**Example A（正常变化）**：胆量 = 1，`change_stat("danliang", +1)` → `old=1, new=2, requested=+1`，effective = +1 = requested。Stat Panel UI 弹标准 "+1" 飘字。
**Example B（底值完全吞掉）**：胆量 = 0（min），`change_stat("danliang", -1)` → `clamp(0+(-1), 0, 10) = 0`，`new == old` → `should_broadcast = false`，**不广播**。Stat Panel UI 不弹飘字；UI 可选择是否给"软"反馈（属于 [[stat-panel-ui]] 设计空间）。
**Example C（顶值半吃掉）**：jiejie 好感 = 14（max=15），`change_affinity("jiejie", +3)` → `clamp(14+3, -10, 15) = 15`，`new ≠ old` → 广播 `("jiejie", 14, 15, +3)`。effective = +1，requested = +3。Stat Panel UI 看到差异可降级显示。
**Example D（INT64 极端值，Round-2 修订）**：xuexi = 3，`change_stat("xuexi", -9223372036854775808)`（INT64_MIN）→ 经 D.1 实装契约的 `safe_delta = clampi(d, m-M, M-m) = clampi(-INT64_MIN, -10, 10) = -10`（注意：实装上 `clampi(INT64_MIN, -10, 10)` 直接收敛到 -10，避免后续 `abs()` 等操作触发二次溢出）→ `new_value = clampi(3 + (-10), 0, 10) = 0`，广播 `("xuexi", 3, 0, -9223372036854775808)`。requested 字段如实保留**原始** INT64_MIN 极端值（用于 push_warning 触发，见 §E.10——E.10 用符号比较而非 abs，避免 INT64_MIN 溢出绕过警告），UI 不应把 requested 直接渲染为飘字——UI 渲染应优先使用 `effective_delta = new − old = -3`。

**设计意图**：满值/底值反复 ±1 不应产生假"被看见"事件——acknowledgment fantasy 的反义保险，没有真变化就不假装"看见了"。但 effective ≠ requested 的"半吃掉"场景仍广播，让 UI 自行选择反馈强度。

### D.4 demo_increment_table（lookup table，**非公式**）

**判定**：demo 范围内 *事件到属性增量* 是 **lookup table**，不是公式。

理由：
- 项目是叙事驱动，每个事件的语义独一无二，没有可推导的曲线
- 设计师改一行 JSON / 资源就生效，不需要重平衡函数
- 符合 CLAUDE.md "gameplay 值数据驱动，不硬编码"硬约束
- Demo 规模可枚举（序章 + 第一章约 30–60 条）

**调用流**：当事件触发时，业务层（Cutscene Runner）查表取出 `stat_deltas / affinity_deltas`，对每个 entry 调一次 D.1 或 D.2，结果按 D.3 决定是否广播。

> Schema 定义、事件 ID 命名约定、表的存放位置均不属于本 GDD 范围，由 Event Flow / Cutscene Runner GDD 定义（[[event-flow]] / [[cutscene-runner]]）。本 GDD 仅承诺 D.1/D.2/D.3 在收到任何合法 (id, delta) 时的数学正确性。

### D.5 显性 / 隐性公用 clamp 的合理性

显性属性（4 项，0–10）与隐性变量（3 项，xinjie/qianbao 0–20、kaguodu 0–10）在数学结构上同构（int + 加性 delta + clamp），仅 range 配置与 UI 可见性不同。

合用同一份 clamp 公式（D.1）的收益：
- 单一代码路径 → 单一测试面（`_apply_clamped_delta(dict, id, delta, cfg)`）
- range 配置外置（`STATS_CONFIG / VARS_CONFIG`），改 max 不动公式
- "可见与否"是 UI 层（Stat Panel UI）关注，不渗入数学层

唯一例外：`_chapter`（String）与 `_triggered / _era_markers`（Set 语义的 Dict）不走 D.1，由独立路径处理（见 Section E.5 / E.6）。

## Edge Cases

格式：`If [condition]: [exact outcome]. [rationale if non-obvious]`

**E.1 — clamp 边界：满值再 +1 / 底值再 −1**

- **If `change_stat` / `change_var` / `change_affinity` 在已满值（=max）时收到 delta > 0**：clamp 后 `new_value == old_value`，**不**广播信号；getter 仍返回 max；调用方不能依赖 delta 实际生效。
- **If 在已底值（=min）时收到 delta < 0**：同上，静默吞掉，无飘字。
- **半吃掉场景**：若 clamp 仅吃掉部分 delta（例如 jiejie 好感=14、max=15、收到 +3，clamp 至 15），**广播会发**：payload 为 `("jiejie", 14, 15, +3)`，订阅者通过 `effective = new − old = +1` 与 `requested = +3` 的差识别"半吃掉"，UI 可降级显示。
- **理由**：满值时反复 +1 不应让 UI 弹假飘字（D.3 设计意图），且不应让某些数据驱动的 condition（"心结 ≥ 20"）被无 op 调用反复触发；但半吃掉场景仍是真变化（`effective_delta ≠ 0`），不能漏报。

**E.2 — 未知 ID（拼写错 / 未注册）**

- **If `change_stat("unknown_id", 1)`**：`STATS_CONFIG.has(id) == false` ⇒ `push_error("[GlobalState] unknown stat: %s")`，**不**修改任何集合，**不**广播。函数提前返回。
- **If `change_var("unknown_id", 1)`**：同上，路径独立。
- **If `change_affinity("unknown_npc", 1)`**（design-review 修订后规则）：`AFFINITY_CONFIG.has(npc_id) == false` ⇒ `push_error("[GlobalState] unknown npc: %s")`，**不**修改任何集合，**不**广播。函数提前返回。**（修订理由）**：旧"宽容"语义带来 typo 静默 + 序列化污染（H.10 round-trip 持久化拼错的 NPC ID）。现在三类 change_* 接口对未知 ID 行为对称——典型的"拼写错"由 push_error 在 dev console 立刻暴露。后续章节扩展 NPC 必须先在 §C.4 表中声明再开始调用。
- **If `get_stat("unknown_id")` / `get_var(...)` / `get_affinity(...)`**：返回 0（不报错）—— 容忍读路径，方便条件判定写成 `get_stat("xxx") >= 3` 而不必先 `has()`。读路径不变，与 v1 草案一致。

**E.10 — 调用方 delta 越界（typo safety，design-review 修订新增）**

**E.10 — 调用方 delta 越界（typo safety，design-review 修订新增；Round-2 修订：abs 溢出修复 + 阈值 5）**

- **If `change_stat / change_var / change_affinity` 收到 `delta > TYPO_WARN_DELTA or delta < -TYPO_WARN_DELTA`**（默认 `TYPO_WARN_DELTA = 5`，见 §G）：先按正常路径执行（clamp + 广播——若 effective_delta = 0 则按 §D.3 不广播），然后**仅当 effective_delta ≠ 0** 时 `push_warning("[GlobalState] large delta on %s: %d (typical range [-5, +5])" % [id, delta])`。**不**阻塞业务逻辑——只是给设计师一个 dev console 警示。
- **不用 `abs()` 的原因（Round-2 修订）**：GDScript int 是 64-bit 有符号；`abs(INT64_MIN)` 在二进制补码下溢出回到 `INT64_MIN`（无可表示的正数对应值），导致 `abs(d) > T` 在 d = INT64_MIN 时返回 `false`——最极端的 typo 反而被静默吞掉。改成 `delta > T or delta < -T` 用符号比较，在 d = INT64_MIN 时第二个条件成立，警告正常触发。
- **effective_delta = 0 时不警告（Round-2 修订）**：如果调用是 `change_affinity("caozhengdong", -20)` 但当前已在底值 -15 ⇒ effective_delta = 0，按 §D.3 不广播 stat_changed；同样不发 push_warning（避免一段被反复 replay 的 cutscene 在 dev console 刷屏空 warning）。typo 警告与信号广播在"是否真发生变化"上语义对齐。
- **理由**：demo 范围内单次事件给的属性变化都在 [−3, +3]（见 D.4 lookup table）；调高到 5 之后 `+10` / `+100` / 多打 0 类典型 typo 仍能被捕获，同时给"剧情高跳"事件（如 ch3 末一次给 +5 心结）留出不报警的合法空间。push_warning 比静默吞掉好，比 push_error 阻塞业务温和。
- **不在覆盖范围**：合法的"剧情高跳"（例如 ch3 终点一次给 +6 心结的事件，如果以后真有）应在事件设计阶段评审；GDD 不强阻拦，仅靠 warning 提示。如未来确实需要 ±6 的事件常态化，调高警告阈值或 ADR 调整。

**E.3 — 同帧多次 change_***

- **If 在同一帧依次调用 `change_stat("danliang", 1)` 三次（初值 1）**：每次都按 D.1 计算并按 D.3 广播；订阅者将收到 3 次 `stat_changed`：`("danliang", 1, 2, +1)` / `("danliang", 2, 3, +1)` / `("danliang", 3, 4, +1)`（顺序与调用顺序一致）。
- **理由**：信号是同步发出的；订阅者（Stat Panel UI）必须能处理同帧多次 +1 飘字（参考 UI Requirements）。
- **再入禁止（Round-2 修订强化）**：订阅者**不得**在 `*_changed` 回调里同步触发新的 `change_*`。这一条由两侧共同保证：
  - **实装侧**：每个 `change_*` 函数进入时检查 `_emit_depth`；若 > 0 则 `push_error("[GlobalState] re-entrant change_* during signal handler — use call_deferred")` 并 return（不修改集合、不发信号），见 §C.6 再入保护契约。
  - **订阅侧**：订阅 GDD 应使用 `connect(handler, Object.CONNECT_DEFERRED)`，由信号系统延迟到下一帧调度回调；若必须同步连接，handler 内若需调用 `change_*` 必须 `call_deferred("change_stat", ...)`。
  - **效果**：单次违规不会栈溢出（被实装侧 push_error 拦下），但会立即在 dev console 暴露；CONNECT_DEFERRED 是预防性的"零成本正确"。

**E.4 — 重复 mark_triggered / mark_era_marker**

- **If `mark_triggered("ch1/12_yuekao_ranking")` 被调用两次**：第二次静默忽略，**不**广播 `event_triggered`。
- **If `mark_era_marker("kaixue")` 被调用两次**：同上，**不**广播 `era_marker_added`。
- **理由**：保证 toast UI 与剧情分支的 idempotent 性 —— Cutscene Runner 重启同一段流程不会重弹"开学"标记 toast。

**E.5 — chapter 状态机非法跳转**

- **If `set_chapter("prologue")` 在当前 `_chapter == "ch1"` 时被业务代码调用**：实装上**会**写入并广播（不检查方向）。**但 GDD 规则**：业务代码（Cutscene Runner / Dialogue / 任何 gameplay 系统）**不允许**调用回退方向；只有 `from_dict` 可以"任意"写章节字段。违反此规则需在 code review 中拦截。
- **If `set_chapter` 收到 demo 范围之外的章节 ID（如 `"ch2"`）**：实装不校验，会接受。Demo 阶段的合法值仅 `prologue / ch1 / ch1_done`。
- **理由**：本 GDD 只锁 demo 范围；未来章节扩展时可在配置中追加合法值列表，但不属于 v1 接口冻结条款。

**E.6 — from_dict 容错（design-review 修订：自愈式）**

- **If `from_dict({})`（空 dict）**：先 `reset_to_initial()`，然后无任何键覆盖 ⇒ 状态等同于 `reset_to_initial()`，无信号广播（reset 路径不发信号）。
- **If `from_dict({"stats": {"unknown_id": 99}})`**：`STATS_CONFIG.has("unknown_id") == false` ⇒ 跳过该项；其它已知 ID 走自愈路径（见下条）。
- **If `from_dict({"stats": {"xuexi": 999}})`**（自愈式，design-review 修订）：
  1. 先把 raw 值 cast 为 int（防止 JSON 解析得到 `999.0` 这类浮点，`int(value)` 强制转换）
  2. 再用该 ID 的 `STATS_CONFIG[id].min/max` 走 `clampi(...)`
  3. 若 raw 值与 clamp 后值不一致，发 `push_warning("[GlobalState] from_dict: %s out-of-range %s, clamped to %d" % [id, raw, clamped])`
  4. 写入 `_stats[id] = clamped`
  5. **不**广播 `stat_changed`（reset 路径与加载路径设计为静默；UI 在 load_finished 后由 SaveManager 通知再 re-read 当前值）
- **If `from_dict({"vars": {"xinjie": 9999999}})`**：同上自愈路径，clamp 至 `VARS_CONFIG["xinjie"].max = 20`，写入 20，发 push_warning。
- **If `from_dict({"affinity": {"jiejie": 99}})`**：`AFFINITY_CONFIG.has("jiejie") == true` ⇒ 走自愈路径，clamp 至 `AFFINITY_CONFIG["jiejie"].max = 15`，写入 15，发 push_warning。
- **If `from_dict({"affinity": {"unknown_npc": 5}})`**：`AFFINITY_CONFIG.has("unknown_npc") == false` ⇒ 跳过该项 + push_warning（"unknown npc in save"）。与 §E.2 修订规则一致：未知 ID 不再静默接受。
- **If `from_dict({"chapter": "ch99"})`**（demo 范围外章节）：写入但 push_warning。Demo 阶段合法值仅 `prologue / ch1 / ch1_done`；后续章节扩展时把白名单扩大。
- **理由（自愈语义）**：旧 GDD 草案的"接受 raw 快照、不 clamp、blame SaveManager"语义在 SaveManager GDD 未写时留下高风险窗口（systems-designer + godot-specialist 共识）。改为自愈后：(a) 任何后续 change_* 的 broadcast 都不会"撒谎"（effective_delta 始终匹配 panel 数字）；(b) 拼写或腐败的存档自动收敛到合法范围，玩家不会被踢出系统；(c) push_warning 让 dev 在 console 看到自愈动作，便于调试。**SaveManager 仍可在外层做 schema 版本迁移**——本系统的自愈是兜底，不是替代。

**E.7 — 反复 reset_to_initial**

- **If `reset_to_initial()` 被多次调用**：每次完整覆盖所有集合到初值；**不**广播任何 `*_changed` 信号（reset 路径设计为静默，避免 UI 在新游戏时弹一堆 +0 飘字）。
- **理由**：Main Menu 选择"新游戏"时 SaveManager 调 reset；此时 UI 还没绑信号，广播也无意义。订阅者（Stat Panel UI）在 `load_finished` / scene_enter 时由 SaveManager 主动通知，再 re-read 全部 4 个显性属性的当前值（不依赖广播追平）。这一契约见 §F.5 cross-GDD invariant。

**E.8 — 序列化往返一致性（design-review 修订：to_dict 内部规范化）**

- **If `to_dict()` → `from_dict(d)` 来回一次**：数据值必须**完全相同**（深比 `d == d2`）。
- **实现契约**：`to_dict()` 必须对 `_triggered.keys()` 与 `_era_markers.keys()` 调用 `sort()` 后再写入返回字典——保证同一状态下 `to_dict()` 输出**字面**确定（同一 state 多次 dump 字节级相同）。Dictionary 在 Godot 4 中虽插入有序，但 sort 让存档对 git diff / 调试快照 / round-trip 比较都稳定。
- **`_stats / _vars / _affinity`** 通过 `Dictionary.duplicate(true)` 拷贝；它们的 key 顺序由 `STATS_CONFIG / VARS_CONFIG / AFFINITY_CONFIG` 的声明顺序决定（确定性，无需额外 sort）。
- **`_triggered` / `_era_markers` 的 Set-as-Dict 语义（Round-2 修订澄清）**：两者在内存中是 `Dictionary[String, bool]`，**值恒为 `true`**——只用 key 集合表达"是否触发过"，value 没有语义。`to_dict()` 序列化时**只输出 keys 数组**（已 sort），不输出值；`from_dict()` 反序列化时把数组 keys 重建到 `_triggered[k] = true`。
- **`from_dict` 异常容错（Round-2 修订）**：
  - 若 `data["triggered"]` 是 dict 而非 array（旧版本存档遗留）：取 `data["triggered"].keys()` 作为 keys 数组使用；丢弃 value。
  - 若 dict 内含 falsy value（`{"ev1": false}`）：仍把 `"ev1"` 视为已触发并写入 `_triggered`，同时 `push_warning("[GlobalState] from_dict: triggered key with non-true value, treating as triggered: ev1")`——保守解读为"曾经写过该 key"，避免老存档因不规范的 false 值丢失剧情进度；如果未来需要"撤销 trigger" 必须由独立 API 提供，不能借 falsy value。
  - 若类型完全不识别（数字 / 字符串顶层）：跳过该字段并 push_warning，使用 reset 后的空集合。
- **理由**：H.10 round-trip AC 用深比 d == d2，没有 sort 时一旦 Dictionary 插入顺序受非确定性的 from_dict 调用顺序影响（例如 ch99 加载老存档），AC 会"flaky 通过"。to_dict sort 是契约层稳定化，不是 AC 层兜底——存档可读性、git diff 可读性也受益。

**E.9 — 持久 NPC affinity 的范围超出（理论）**

- **If 某 cutscene 连续调 `change_affinity("jiejie", 1)` 八次**：jiejie 初值 8、max=15（C.4 修订），第 1–7 次正常变化（8 → 9 → ... → 15）；第 8 次 effective=0，**不**广播；同时因 effective_delta=0，按 §E.10 修订也**不**触发 push_warning（即使 delta 越过阈值也只在真发生变化时报警）。
- **理由**：N+1 测试驱动；demo 范围不会真正触发，但 GDD 写明确保下游不会假设"+1 总会生效"。design-review 修订后 jiejie 头室扩到 +15，"被托住" pillar 至少留 5 次暖意累积空间。

## Dependencies

### F.1 上游（Stat System depends on）

**无。**

Stat System 是 Foundation 层，零外部依赖。它只依赖 Godot 4.6 引擎本身的 `Node` autoload + `Dictionary` + `clamp`，这些不算业务依赖。

### F.2 下游（Depended on by）

按 systems-index.md 的依赖图，Stat System 是 **demo 范围内被依赖次数最高的系统**（≥ 9）。所有依赖关系均为"硬依赖"——下游系统的核心职能要么读 Stat System 的状态，要么写 Stat System 的状态。

| 下游系统 | GDD 路径 | 依赖类型 | 接口契约（详见 Section C 交互表） |
|---|---|---|---|
| Dialogue | [[dialogue]] | 硬（读） | `get_stat / get_var / get_affinity / has_triggered / has_era_marker / get_chapter` |
| Cutscene Runner | [[cutscene-runner]] | 硬（读 + 写） | 所有 `change_* / mark_* / set_chapter` |
| Event Flow | [[event-flow]] | 硬（读 + 写） | `has_triggered / mark_triggered / has_era_marker / mark_era_marker / get_chapter / set_chapter` |
| NPC System | [[npc-system]] | 硬（读 + 写） | `get_affinity / change_affinity` + 订阅 `affinity_changed` |
| Item System | [[item-system]] | 硬(写) | `change_stat / change_var / mark_triggered` |
| Era Marker | [[era-marker]] | 硬（读 + 写） | `mark_era_marker / has_era_marker` + 订阅 `era_marker_added` |
| Wallet & Credit | [[wallet-credit]] | 硬（写） | `change_var qianbao_xiuchi / change_affinity baosimu` |
| Combat Core | [[combat-core]] | 硬（读） | `get_stat danliang` + 订阅 `stat_changed` |
| Courage Resource | [[courage-resource]] | 硬（读） | `get_stat danliang` |
| Skill Tree | [[skill-tree]] | 硬（读） | `get_stat danliang / get_stat koucai` |
| Emotion State | [[emotion-state]] | 硬（读） | `get_var xinjie / get_var qianbao_xiuchi` + 订阅 `var_changed` |
| Stat Panel UI | [[stat-panel-ui]] | 硬（读 + 订阅） | 仅订阅 `stat_changed`（4 显性属性的飘字 + 数字） |
| Save / Load | [[save-load]] | 硬（读 + 写） | `to_dict / from_dict / reset_to_initial` |

> **双向一致性提醒**：上述每个下游 GDD 在它自己的 "Dependencies" 节里**必须**列出 "depends on Stat System"。如果某下游 GDD 完成时漏写，`/consistency-check` 会检测到单向依赖。

### F.3 软依赖 / 弱关联

无（demo 范围内）。

### F.4 不依赖（明确否定）

以下系统**与 Stat System 无任何交互**，禁止在它们的实现里出现 `GlobalState.*` 调用：

| 系统 | GDD 路径 | 理由 |
|---|---|---|
| Asset Loading | [[asset-loading]] | 资源 ID 与属性数据正交 |
| Scene Routing | [[scene-routing]] | 场景切换时序由 SaveManager 处理状态保存，Routing 本身不读属性 |
| Character Controller | [[character-controller]] | 横版控制器只读输入与物理；任何属性影响（如体力影响冲刺距离）由 Combat Core / Movement 上层注入 |
| Camera | [[camera]] | 跟随策略与属性无关 |
| Input Mapping | [[input-mapping]] | 抽象输入；属性不影响按键映射 |
| Combat VFX | [[combat-vfx]] | 仅播 VFX；属性变化的视觉反馈由 Stat Panel UI 与对应业务系统处理 |
| Chapter Title / Toast | [[chapter-title]] | 订阅 `chapter_changed` 是 Era Marker 的工作；Toast 不直接订阅 Stat System |
| Main Menu | [[main-menu]] | 通过 SaveManager 间接交互（new game 触发 reset），不直接调 Stat System |
| Audio Bus | [[audio-bus]] | 完全无关（Post-Demo） |

### F.5 双向一致性约定（cross-GDD invariant）

- **接口冻结**：任何下游 GDD 的 "Interactions with Other Systems" / "Dependencies" 节如果声称 "calls `GlobalState.foo()`"，则 `foo()` 必须出现在 Section C.5 的接口冻结表里。任何不在 C.5 表中的调用是 GDD 越界。
- **新 ID 必须先注册**：任何下游 GDD 引入新的 stat / var / affinity ID（章节扩展），必须**先**修订本 GDD 的 C.2 / C.3 / C.4 表，并更新 entity registry，再修改下游。
- **数值不得 hardcode**（design-review 修订新增）：下游 GDD / 代码 / 测试**禁止** hardcode `min` / `max` / `init` 数值（例如禁止写 `if get_var("xinjie") >= 20`），必须从 `STATS_CONFIG[id].max` / `VARS_CONFIG[id].max` / `AFFINITY_CONFIG[npc_id].max` 读取。理由：xinjie/qianbao max=20 等是 PROVISIONAL 数值（终章场景未设计前不冻结，见 §G），下游若 hardcode 会在数值调整时静默失效。
- **load 路径 UI 契约**（design-review 修订新增）：`reset_to_initial()` 与 `from_dict(...)` 都不广播 `*_changed`。订阅者（典型为 [[stat-panel-ui]]）必须在 `SaveManager.load_finished` 信号或场景 `_ready` 时主动 re-read 全部 4 个显性属性的当前值（`get_stat(id)`），不能依赖广播追平。这一契约必须由 [[stat-panel-ui]] / [[save-load]] GDD 在自己的 Dependencies 节复述。
- **tone 不得加 juice**（design-review 修订新增）：[[stat-panel-ui]] 渲染 `stat_changed` 飘字时，**禁止** SFX、彩色变换、缩放/抖动等"奖励感"特效。Section B 的 acknowledgment fantasy 是单色无音效整数飘字；该约束是 cross-GDD invariant，由 `/consistency-check` 在 stat-panel-ui GDD 完成后强制。
- **启动 config 校验**（Round-2 修订新增 / R-S6）：`GlobalState._ready()` 必须在初始化前对 `STATS_CONFIG / VARS_CONFIG / AFFINITY_CONFIG` 三表逐项校验：每个 entry 必须满足 `min ≤ init ≤ max` 且 `min ≤ max`。任一项违反 → `push_error("[GlobalState] config invariant violated: %s min=%d init=%d max=%d" % [...])` 并 `assert(false)` 阻断启动（不允许进入运行时状态）。理由：`clampi(x, min, max)` 在 `min > max` 时行为未定义（Godot 4.x 静默返回 `max` 或 `min`，取决于实现），一个 typo（`jiejie.min = 16, max = 15`）会让所有 `change_affinity("jiejie", ...)` 进入静默腰斩。配置校验**必须**在 fail-fast 时机捕获。该规则由 §H.19 AC 强制。
- **订阅者 CONNECT_DEFERRED 推荐**（Round-2 修订新增 / R-K1）：所有订阅 GDD（[[stat-panel-ui]] / [[combat-core]] / [[npc-system]] / [[era-marker]] / [[cutscene-runner]] / [[event-flow]] 等）在自己的 Dependencies 节里**必须**声明：连接 `*_changed / *_triggered / *_added` 信号时使用 `connect(handler, Object.CONNECT_DEFERRED)`。理由：搭配 §C.6 实装侧 `_emit_depth` 守卫，是"零成本正确"的双重保险——CONNECT_DEFERRED 把 handler 调度到下一帧，handler 内即使调用 `change_*` 也已经在新栈帧上运行，不会触发再入；实装侧守卫只在订阅 GDD 违反契约时兜底报错。该规则由 `/consistency-check` 在每个订阅 GDD 完成后扫描其 Dependencies 节强制。
- **affinity-changing event_id 默认 idempotent**（Round-2 修订新增 / R-G3）：[[event-flow]] / [[npc-system]] / [[cutscene-runner]] / [[dialogue]] GDD 在设计任何**改 affinity** 的事件时，事件实装**必须** gate on `has_triggered(event_id)`：若已触发则跳过该 affinity delta（仅显示对白）；这样防止"反复进出小卖部跟鲍师母讲同一段对话刷 affinity"类的退化策略。Stat System 不强制此规则在 `change_affinity` 入口检查（不是 stat-system 该担的责任），但通过本 invariant 把责任压到事件层。例外：如果设计明确"该事件可重复给好感"（如礼物系统）必须在事件 spec 里显式声明 `repeatable: true` 并解释设计动机。该规则由 `/consistency-check` 在 event-flow GDD 完成后扫描事件表强制。
- **Invariant enforcement 兜底说明**（Round-2 修订新增）：上述 7 条 invariant 中，**5 条**（接口冻结 / 新 ID 注册 / 不得 hardcode / load 路径 / event_id idempotent）属于"GDD 文档级规则"——`/consistency-check` 通过 grep + GDD 表交叉对照在每次跨 GDD 评审时强制；**1 条**（tone 不得加 juice）属于跨学科评审，由 ux-review + creative-director 在 stat-panel-ui GDD 评审时把关；**1 条**（启动 config 校验）属于运行时检查，已在本 GDD §H.19 AC 锁死。`/consistency-check` skill 尚未实装，过渡期由 PR review 兜底，落地后追加 ADR 记录。


## Tuning Knobs

> **PROVISIONAL 标记说明**（design-review 修订新增）：标记 `[PROVISIONAL]` 的数值是终章场景未设计前的占位值——契约**形状**（schema、字段名、单位）已冻结，但具体数字可在 [[chapter-finale]] / [[multi-ending]] GDD 写完后调整。下游系统按 §F.5 invariant **不得 hardcode** 这些数值，必须从配置读。

| Knob | Location | Default | Safe Range | 调高 → | 调低 → |
|---|---|---|---|---|---|
| 每个显性属性的 init | `STATS_CONFIG[id].init` | xuexi=3 / danliang=1 / koucai=1 / tili=3 | [0, max] | 玩家起步更"强"，序章 demo 节奏感弱 | 起步更弱，节奏更慢但 demo 体验更"被困住" |
| 每个显性属性的 max | `STATS_CONFIG[id].max` | 10 | [5, 99] | 后续章节扩展空间大；UI 飘字格式可能要变（双位数） | 顶 cap 更早，胆量解锁里程碑（≥3 / ≥4 / ≥5）需重排 |
| 每个显性属性的 min | `STATS_CONFIG[id].min` | 0 | [−99, init] | 允许负值（"负胆量"=逃避特化） — demo 不建议 | 不能再低 |
| 每个隐性变量的 max **[PROVISIONAL]** | `VARS_CONFIG[id].max` | xinjie=20 / kaguodu=10 / qianbao=20 | [5, 99] | 满值阈值变远，"心结 ≥ 20"分支更难触发 | 提前触发后期分支 |
| 每个隐性变量的 init | `VARS_CONFIG[id].init` | 全部 0 | [0, max] | 一开始就有"心理负债" | 不能再低 |
| 每位 NPC 的 affinity init | `AFFINITY_CONFIG[npc_id].init` | 见 C.4 表 | [npc.min, npc.max] | 该 NPC 起始更友好 | 起始更敌对（曹正东 −3 已是设计意图） |
| 每位 NPC 的 affinity min | `AFFINITY_CONFIG[npc_id].min` | 默认 −10；caozhengdong=−15 | [−99, init] | 允许更深的"宿敌"区间（曹正东 post-demo BOSS 战预留 −15）| 缩短下行空间 |
| 每位 NPC 的 affinity max | `AFFINITY_CONFIG[npc_id].max` | 默认 +10；jiejie=+15 | [init, +99] | 允许更深的"挚友"区间（jiejie "被托住" pillar 至少 5 次暖意空间） | 缩短上行空间 |
| AFFINITY_DEFAULT_MIN | 全局常量 | −10 | [−99, 0] | 仅作为未在 AFFINITY_CONFIG 显式声明 min 的 NPC fallback | 同上 |
| AFFINITY_DEFAULT_MAX | 全局常量 | +10 | [0, +99] | 仅作为未在 AFFINITY_CONFIG 显式声明 max 的 NPC fallback | 同上 |
| typo_warning_threshold（design-review 修订新增；Round-2 调整 3 → 5） | `TYPO_WARN_DELTA = 5` | 5 | [1, 10] | 调高 → push_warning 更宽容（设计师 typo 漏过率 ↑） | 调低 → 警告噪音 ↑（与 demo lookup 表上限 ±3 重合时会误报合法事件） |

**Knob 间的相互作用警告**：

- **`STATS_CONFIG[danliang].max` 与下游解锁阈值耦合**：Combat Core / Skill Tree GDD 里"胆量 ≥ 3 解锁推开他"等里程碑写死了 3 / 4 / 5。改 max 必须同步检查所有下游解锁阈值（`/consistency-check` 会报）。**注意 §F.5 invariant**：下游不得 hardcode 阈值数值——`3 / 4 / 5` 必须改为 `STATS_CONFIG[danliang].milestones[0..2]` 或在各下游 GDD 的 PROVISIONAL 节集中声明。
- **`STATS_CONFIG[*].init` 与对白条件耦合**：序章首场对白若假设"口才 = 1 时无法选 X"，调高 koucai.init 会越过条件。需 `/consistency-check`。
- **`VARS_CONFIG[xinjie].max = 20` [PROVISIONAL] 与终章独白分流耦合**：超出 demo 范围。**关键约束**：终章 GDD（[[chapter-finale]]，未写）的多结局公式不得 hardcode 20，否则调整 max 时分流会静默失效。本 GDD 在 §F.5 invariant 已约束。

**Knob 不在本 GDD 范围**：

- demo_increment_table 的具体增量值（每个事件 +1 还是 +2）→ 属于 Event Flow / Cutscene Runner GDD（[[event-flow]]）的 tuning knobs
- 满值时 UI 飘字是否变色 → 属于 Stat Panel UI GDD（[[stat-panel-ui]]）的 tuning，但**§F.5 已约束**：禁止 SFX/彩色/抖动等 juice 反馈，整数无装饰是 acknowledgment fantasy 的硬性 tone 契约

**Tuning 流程**：所有 knob 修改必须经 `/quick-design` 或 `/balance-check`，绕过会引入静默回归。

## Visual/Audio Requirements

**N/A — Stat System 是 infrastructure，不直接渲染或发声。**

属性变化的可视化（飘字、面板刷新）由 Stat Panel UI（[[stat-panel-ui]]）订阅 `stat_changed` 实现；toast（章节标题、时代切片）由 Chapter Title / Toast（[[chapter-title]]）订阅 `era_marker_added`、`chapter_changed` 实现。本系统不出 VFX 资产、不出 SFX 事件。

> 若后续设计需要"信号触发音效"（如 stat_changed 时播一段轻响），由 Audio Bus（[[audio-bus]]，Post-Demo）订阅信号，不修改本 GDD。

## UI Requirements

**N/A — Stat System 不直接渲染 UI。**

唯一可见的属性反馈通道是 Stat Panel UI（[[stat-panel-ui]]），它订阅 `stat_changed` 信号实现飘字与数字刷新；其布局、字号、颜色、动画曲线由 Stat Panel UI GDD 与对应 UX 规格（`design/ux/hud.md`）定义，不属于本 GDD 范围。

> 隐性变量（xinjie / kaguodu_xinli / qianbao_xiuchi）与 NPC 好感度按设计**不可见**，本系统不广播任何与之相关的 UI 事件。

## Acceptance Criteria

每条独立可测；GIVEN 已声明所需初始态，无前置依赖。所有 AC 均为 **Logic** 类型（gdunit4 自动化单元测试），覆盖 Section C 的 8 个核心接口、Section D 的 3 个公式、§E 的关键 edge cases。

**测试夹具契约（design-review 修订新增；Round-2 修订澄清，应用于 H.1–H.20 所有 AC）**：
1. **before_test 重置 + 断连**：每个测试 `before_test` 必须按以下顺序执行：
   1. 调用 `reset_to_initial()` 把 GlobalState 回到出厂态。
   2. 对 6 个信号（`stat_changed / var_changed / affinity_changed / event_triggered / era_marker_added / chapter_changed`）逐个调用 `get_signal_connection_list(signal_name)` 拿到该信号现存的所有连接 `Array[Dictionary]`（每个 entry 含 `signal / callable / flags`），逐条 `signal.disconnect(entry["callable"])` 直到列表空。**说明**：Godot 4.6 的 Signal 没有 `disconnect_all()`，必须手动遍历。
   3. 连接 *仅本测试需要* 的 mock subscriber（命名建议 `_test_mock_<signal_name>`，便于 after_test 断连）。
2. **正断言**："`stat_changed` 触发恰 1 次" = 在本测试夹具下、由本测试连接的唯一订阅者上、收到恰 1 次。无需在每条 AC 中复述本契约。
3. **负断言**："`stat_changed` **不**触发" 的判定标准：在 WHEN 触发后调用 `await get_tree().process_frame` 等 2 个 idle frame，然后断言 mock subscriber 的 `_call_count == 0`。**不**使用 `assert_signal(...).is_not_emitted(...)`（gdunit4 4.x 的负断言 API 在 headless 下行为依赖具体版本，不稳定）。
4. **Mock subscriber 模板**：
   ```gdscript
   class_name _StatTestMock
   extends RefCounted
   var _call_count := 0
   var _last_payload: Array = []
   func on_stat_changed(stat_id: String, old_v: int, new_v: int, req: int) -> void:
       _call_count += 1
       _last_payload = [stat_id, old_v, new_v, req]
   ```
   每条 AC 在测试代码里只需断言 `mock._call_count == N` 与 `mock._last_payload == [...]`。
5. **error/warning capture**：H.13 / H.15 / H.19 涉及 `push_error` / `push_warning` 验证。gdunit4 提供 `assert_error_count() / assert_warning_count()`（4.0+ 内置）；若版本不支持，回退方案是临时 hook 全局 `Logger`（待 [[test-helpers]] GDD 提供 `tests/helpers/log_capture.gd`）。本 AC 假设 gdunit4 内置可用，若不可用则 H.13/H.15/H.19 在 `/test-setup` 阶段单独追加 helper。

| # | Given-When-Then | Type |
|---|---|---|
| **H.1** 真变化广播（显性，4 元组 payload） | **GIVEN** `xuexi = 3` **WHEN** `change_stat("xuexi", +1)` **THEN** `get_stat("xuexi") == 4` 且 `stat_changed` 触发 1 次，payload `("xuexi", old=3, new=4, requested=+1)` 全部字段精确匹配 | Logic |
| **H.2** 底值完全吞掉不广播（D.3 + E.1） | **GIVEN** `danliang = 0`（min=0） **WHEN** `change_stat("danliang", -1)` **THEN** `get_stat("danliang") == 0`，`stat_changed` **不**触发；同帧 100ms 内无延迟广播 | Logic |
| **H.3** reset 静默（E.7） | **GIVEN** 显式构造已变更运行态：(a) 修改 2 个 stat — `change_stat("xuexi", +2)` / `change_stat("danliang", +1)`；(b) 修改 2 个 var — `change_var("xinjie", +1)` / `change_var("qianbao_xiuchi", +1)`；(c) 修改 2 个 affinity — `change_affinity("jiejie", +2)` / `change_affinity("caozhengdong", -2)`；(d) 加 2 条 triggered — `mark_triggered("ev1")` / `mark_triggered("ev2")`；(e) 加 2 条 era_markers — `mark_era_marker("kaixue")` / `mark_era_marker("shenzhou7")`；(f) `set_chapter("ch1")`；测试在 reset 调用前已绑定全部 6 个 mock subscribers **WHEN** `reset_to_initial()` **THEN** (1) 4 个显性属性全部回到 `STATS_CONFIG[id].init`；(2) 3 个隐性变量全部回到 `VARS_CONFIG[id].init`；(3) 12 个 NPC affinity 全部回到 `AFFINITY_CONFIG[npc_id].init`；(4) `has_triggered("ev1") == false` 且 `has_triggered("ev2") == false`；(5) `has_era_marker("kaixue") == false` 且 `has_era_marker("shenzhou7") == false`；(6) `get_chapter() == "prologue"`；(7) await 2 idle frames 后 6 个 mock subscribers 的 `_call_count == 0` 全部成立 | Logic |
| **H.4** change_var 广播（隐性，4 元组） | **GIVEN** `xinjie = 0` **WHEN** `change_var("xinjie", +2)` **THEN** `get_var("xinjie") == 2` 且 `var_changed` 触发 1 次，payload `("xinjie", old=0, new=2, requested=+2)` 精确匹配 | Logic |
| **H.5** change_affinity 广播（4 元组） | **GIVEN** `affinity["baoxianjin"] = 0` **WHEN** `change_affinity("baoxianjin", -3)` **THEN** `get_affinity("baoxianjin") == -3` 且 `affinity_changed` 触发 1 次，payload `("baoxianjin", old=0, new=-3, requested=-3)` 精确匹配 | Logic |
| **H.6** mark_triggered 首次 | **GIVEN** `has_triggered("ch1/12_yuekao_ranking") == false` **WHEN** `mark_triggered("ch1/12_yuekao_ranking")` **THEN** `has_triggered(...) == true` 且 `event_triggered("ch1/12_yuekao_ranking")` 触发 1 次 | Logic |
| **H.7** mark_triggered 重复静默（E.4） | **GIVEN** `has_triggered("ev1") == true` **WHEN** 再次 `mark_triggered("ev1")` **THEN** `event_triggered` **不**再触发，集合大小不变 | Logic |
| **H.8** mark_era_marker 重复静默（E.4） | **GIVEN** `has_era_marker("kaixue") == true` **WHEN** `mark_era_marker("kaixue")` **THEN** `era_marker_added` **不**触发 | Logic |
| **H.9** set_chapter 广播（Round-2 修订：2 参 payload） | **GIVEN** `get_chapter() == "prologue"` **WHEN** `set_chapter("ch1")` **THEN** `get_chapter() == "ch1"` 且 `chapter_changed` 触发 1 次，payload `(old_chapter="prologue", new_chapter="ch1")` 两字段精确匹配；同章节 set 静默：再次 `set_chapter("ch1")` → `chapter_changed` **不**触发（await 2 idle frames 后 mock `_call_count == 1`） | Logic |
| **H.10** to_dict ↔ from_dict round-trip + sort 显式验证（E.8；Round-2 修订加严） | **GIVEN** 显式构造运行态 S：`reset_to_initial()` 后依次执行 `change_stat("xuexi", +2)`（→5）、`change_var("xinjie", +3)`、`change_affinity("jiejie", +2)`（→10）、`mark_triggered("ev2")`、`mark_triggered("ev1")`（**逆字典序插入**）、`mark_era_marker("shenzhou7")`、`mark_era_marker("kaixue")`（**逆字典序插入**）、`set_chapter("ch1")` **WHEN** `var d = to_dict()`；然后 `reset_to_initial(); from_dict(d); var d2 = to_dict()` **THEN** (1) `d == d2` 深比完全相等；(2) `d["triggered"]` 是 Array 且 `d["triggered"] == ["ev1", "ev2"]`（**显式断言字典升序**，验证 `to_dict()` 内部 sort 契约真实生效，不是插入序碰巧匹配）；(3) `d["era_markers"]` 是 Array 且 `d["era_markers"] == ["kaixue", "shenzhou7"]`（**显式断言字典升序**）；(4) 重复调用 `var d3 = to_dict()` 得 `d == d3` 字面级相等（同 state 多次 dump 字节稳定） | Logic |
| **H.11** from_dict 自愈式 clamp + cast（E.6 修订后语义；Round-2 加严） | **GIVEN** 构造越界快照 `{"stats": {"xuexi": 999, "danliang": -50}, "vars": {"xinjie": -50, "qianbao_xiuchi": 9999.0}, "affinity": {"jiejie": 99, "caozhengdong": -99}}` **WHEN** `reset_to_initial(); from_dict(snap)` **THEN** (1) 6 个字段全部进入"自愈"路径：`get_stat("xuexi") == 10`、`get_stat("danliang") == 0`、`get_var("xinjie") == 0`、`get_var("qianbao_xiuchi") == 20`（同时 9999.0 浮点经 `int(v)` cast 为 9999 后再 clamp）、`get_affinity("jiejie") == 15`、`get_affinity("caozhengdong") == -15`；(2) 6 条均触发 push_warning（`assert_warning_count() == 6`）；(3) await 2 idle frames 后 `stat_changed / var_changed / affinity_changed` 三路 mock subscriber 的 `_call_count == 0`（load 路径静默契约，§F.5）| Logic |
| **H.12** 性能预算（Round-2 修订：< 5ms / headless release / 重复 3 次取最差） | **GIVEN** 任意状态 + 1 个挂在 `stat_changed` 上的 mock subscriber（回调仅 `_call_count += 1`，零分配，按夹具契约 #4 模板） **WHEN** 以下负载：外层循环 10 次（每次开始前 `reset_to_initial()`，不计入计时），内层循环 10 次连续调用 `change_stat("xuexi", +1)`（10 次后到达 max=10，第 10 次仍真广播）——总计 100 次有效 change + 100 次 mock 回调；用 `var t0 = Time.get_ticks_usec(); ...; var t = Time.get_ticks_usec() - t0` 测量纯负载耗时（不含 reset / 测试夹具开销） **THEN** (1) mock subscriber 累计收到 100 次 payload；(2) 单次测量 `t < 5000` µs（5 ms）；(3) 整个 AC 重复执行 3 次，**3 次最差值**仍 < 5 ms（防止 GC pause / OS 调度抖动 false-fail）；(4) **测试运行环境契约**：必须使用 `--headless --release` 构建；CI 在 GitHub-hosted runner 上跑，本地开发机 debug build 仅作参考不作 gate | Logic |
| **H.13** 未知 ID push_error（E.2 修订） | **GIVEN** 任意状态 **WHEN** `change_stat("unknown_id", 1)`、`change_var("unknown_id", 1)`、`change_affinity("unknown_npc", 1)` 各调用 1 次 **THEN** 三次调用均不修改任何集合（`_stats / _vars / _affinity` 大小不变、值不变）、不触发任何 `*_changed` 信号；三次调用各产生一次 push_error（用 gdunit4 error capture 或 stderr 截获）| Logic |
| **H.14** 半吃掉广播 4 元组（D.3 边界） | **GIVEN** `affinity["jiejie"] = 14`（max=15） **WHEN** `change_affinity("jiejie", +3)` **THEN** `get_affinity("jiejie") == 15` 且 `affinity_changed` 触发 1 次，payload `("jiejie", old=14, new=15, requested=+3)` 精确匹配——验证 requested 字段在 clamp 边界保留原值，订阅者可由 `effective = new − old = +1 ≠ requested` 检测"半吃掉" | Logic |
| **H.15** typo_warning 阈值与符号比较（E.10；Round-2 修订：阈值 5 + abs 溢出修复 + effective=0 静默） | **(case A)** GIVEN `xuexi = 3` WHEN `change_stat("xuexi", +6)` THEN `get_stat("xuexi") == 9`（正常路径执行）、`stat_changed` 触发 1 次（payload `("xuexi", 3, 9, +6)`）、`assert_warning_count() == 1`（msg 含 "large delta on xuexi"）；**(case B)** GIVEN `xuexi = 3` WHEN `change_stat("xuexi", +5)` THEN `assert_warning_count() == 0`（边界 \|delta\| ≤ 5 不警告）；**(case C 半吃掉仍报)** GIVEN `xuexi = 7` WHEN `change_stat("xuexi", +6)` THEN `get_stat == 10`、`stat_changed` 触发（payload `(7,10,+6)`）、`assert_warning_count() == 1`；**(case D effective=0 静默)** GIVEN `affinity["caozhengdong"] = -15`（min=-15）WHEN `change_affinity("caozhengdong", -20)` THEN `get_affinity == -15` 不变、`affinity_changed` **不**触发、`assert_warning_count() == 0`（effective=0 时不发 warning）；**(case E INT64_MIN 不绕过)** GIVEN `xuexi = 3` WHEN `change_stat("xuexi", -9223372036854775808)`（INT64_MIN）THEN `get_stat == 0`（D.1 safe_delta clamp 后到 -10 → clamp 到 0）、`stat_changed` 触发 payload requested 字段含 INT64_MIN 原值、`assert_warning_count() == 1`（符号比较 `delta < -T` 在 INT64_MIN 时仍为真，不被 abs 溢出绕过） | Logic |
| **H.16** C.5 负 API 表面 | **GIVEN** GlobalState 实例 **THEN** `has_method("set_stat") == false`、`has_method("set_var") == false`、`has_method("set_affinity") == false`——禁止未来 PR 静默引入绝对赋值接口 | Logic |
| **H.17** from_dict unknown ID 跳过 + push_warning（E.6 case 2/6；Round-2 新增） | **GIVEN** 构造快照 `{"stats": {"unknown_stat": 5, "xuexi": 4}, "vars": {"unknown_var": 7, "xinjie": 2}, "affinity": {"unknown_npc": 3, "jiejie": 9}}` **WHEN** `reset_to_initial(); from_dict(snap)` **THEN** (1) 已知 ID 正确写入：`get_stat("xuexi") == 4`、`get_var("xinjie") == 2`、`get_affinity("jiejie") == 9`；(2) unknown_stat / unknown_var / unknown_npc 全部被跳过——`_stats / _vars / _affinity` 大小不变（仅含 STATS_CONFIG / VARS_CONFIG / AFFINITY_CONFIG 注册的 ID）；(3) `assert_warning_count() == 3`（每个 unknown 一次，msg 含 "unknown" 字样） | Logic |
| **H.18** from_dict chapter 越界写入 + push_warning（E.6 case 7；Round-2 新增） | **GIVEN** 构造快照 `{"chapter": "ch99"}` **WHEN** `reset_to_initial(); from_dict(snap)` **THEN** (1) `get_chapter() == "ch99"`（实装按 §C.5 / §E.5 不校验，写入接受）；(2) `assert_warning_count() == 1`（msg 含 "out-of-range chapter" 或 "unknown chapter"）；(3) `chapter_changed` **不**触发（load 路径静默） | Logic |
| **H.19** 启动 config 校验（§F.5 新 invariant；Round-2 新增 / R-S6） | **GIVEN** 构造一个测试用的 GlobalState 子类或实例方法（`_validate_configs(stats_cfg, vars_cfg, affinity_cfg) -> bool`）专用于单元测试隔离不影响真实 _ready；构造 3 组非法 config：(a) `{"xuexi": {"init": 5, "min": 6, "max": 10}}`（init < min）；(b) `{"xuexi": {"init": 11, "min": 0, "max": 10}}`（init > max）；(c) `{"jiejie": {"init": 8, "min": 16, "max": 15}}`（min > max） **WHEN** 对每组 config 调用 `_validate_configs(...)` **THEN** (1) 三组均返回 `false`；(2) 每组各产生 1 次 push_error（`assert_error_count() == 3`，msg 各含相应 id 与 "config invariant violated"）；GIVEN 合法 config（默认 STATS_CONFIG / VARS_CONFIG / AFFINITY_CONFIG）WHEN `_validate_configs(...)` THEN 返回 `true` 且无 push_error/push_warning | Logic |
| **H.20** 同帧多次 change_* 多次广播（E.3；Round-2 新增） | **GIVEN** `danliang = 1` + mock subscriber 连接到 `stat_changed`（CONNECT_DEFERRED **不**使用，目的是验证同步路径同帧多次正确） **WHEN** 同一 test method 内同步连续调用 `change_stat("danliang", +1)` 三次（无 await） **THEN** await 1 idle frame 后 mock subscriber `_call_count == 3` 且按调用顺序收到 3 次 payload：`("danliang", 1, 2, +1)` / `("danliang", 2, 3, +1)` / `("danliang", 3, 4, +1)`；`get_stat("danliang") == 4` | Logic |

**覆盖率自检**（cross 对照 Section C/D/E；Round-2 修订后含 H.17–H.20）：

- **接口覆盖**：change_stat (H.1/H.2/H.13/H.15/H.20) ✓ change_var (H.4/H.13) ✓ change_affinity (H.5/H.13/H.14/H.15-D) ✓ mark_triggered (H.6/H.7) ✓ mark_era_marker (H.8) ✓ set_chapter (H.9 含 2 参 payload) ✓ to_dict / from_dict (H.10/H.11/H.17/H.18) ✓ reset_to_initial (H.3 含 6 集合校验) ✓ get_* （隐式覆盖 in 多条 THEN）✓ 负 API (H.16) ✓ config 校验 (H.19) ✓
- **公式覆盖**：D.1 clamp + 溢出安全（H.1/H.2/H.15-E）✓ D.2 affinity clamp per-NPC (H.5/H.14/H.11) ✓ D.3 broadcast 判定（4 元组 payload + effective ≠ requested 边界 + effective=0 静默，H.1/H.2/H.14/H.15-A/B/C/D）✓
- **Edge cases 覆盖**：E.1 底值/半吃掉 (H.2/H.14) ✓ E.2 未知 ID push_error (H.13) ✓ E.3 同帧多次（H.20）✓ E.4 重复 mark (H.7/H.8) ✓ E.6 from_dict 自愈 (H.11/H.17/H.18) ✓ E.7 reset 静默 (H.3) ✓ E.8 round-trip 确定性 + sort 显式断言 (H.10) ✓ E.10 typo warning + abs 溢出修复（H.15 全 5 case）✓
- **F.5 invariant 覆盖**：启动 config 校验（H.19）✓ 数值不得 hardcode / load 路径 UI / event_id idempotent / CONNECT_DEFERRED — 文档级规则由 `/consistency-check` 跨 GDD 评审强制（不在本节 AC 范围）

**未在 H 节直接覆盖（属于其他 GDD 的测试范围）**：

- E.5 chapter 非法回退 → 业务规则（"Cutscene Runner / Dialogue 不应反向跳"），由 Cutscene Runner GDD 测试覆盖；本 GDD 仅在 §C.5 / §E.5 锁住 set_chapter 接受任意字符串的契约
- E.9 jiejie 顶值 +1 静默吞掉 → 已被 H.2 + H.14 的组合覆盖（H.2 是底/顶完全吞掉，H.14 是半吃掉），不再单列

**预实现前提（design-review 修订）**：
- gdunit4 安装到 `addons/`（见 §I.3）
- `GlobalState` 注册为 autoload（见 §I.1 / §I.2）
- `global_state.gd` 实装侧补齐 Round-2 修订的契约（4 元组 signal payload / `clampi` / `_emit_depth` 再入守卫 / from_dict 自愈 / to_dict sort / per-NPC AFFINITY_CONFIG / `_validate_configs` 启动校验），由 ADR + godot-gdscript-specialist 落地（见 §I.1 / §I.4）
- 否则上述 20 条 AC 均无法运行——状态为"待实现"，不是"通过"

> **Review 历史**：
> - **Round-1（2026-05-31，lean → full）**：本节首版由作者会话内的 qa-lead 介入（lean mode）；同日由独立 qa-lead full-mode 审稿后大改，新增 H.13–H.16、重写 H.1–H.5/H.10/H.11/H.12、新增测试夹具契约。
> - **Round-2（2026-05-31，re-review）**：qa-lead + systems-designer + game-designer + godot-specialist + creative-director synthesis 共发现 16 项 BLOCKING（5 项 AC 规格、3 项公式溢出、8 项实装契约漂移由 §I 兜底）；本节相应：测试夹具契约从 3 条扩到 5 条（含 mock subscriber 模板与 error/warning capture 说明）；H.3 加严 pre-state；H.9 改 2 参 payload；H.10 显式 sort 断言；H.11 扩多字段+cast 浮点；H.12 < 1ms → < 5ms 并锁 build；H.15 改写为 5 case（含 INT64_MIN 不绕过 / effective=0 静默）；新增 H.17（unknown ID）/ H.18（chapter 越界）/ H.19（config 校验）/ H.20（同帧多次）。

## Pre-Conditions

> **新增于 design-review 修订（2026-05-31）**：本节列出 GDD **契约范围外** 但 **下游 GDD / 实现 / 测试 全部 BLOCKED-ON** 的部署前提。这些不属于 stat-system GDD 自身的"设计决策"，但在它们解决之前，本 GDD 的所有 AC 都不可验证、12 个下游 GDD 也不能进入实现阶段。

### I.1 Autoload 注册（BLOCKING）

**问题**：`scripts/autoload/global_state.gd` 已落盘，但 `project.godot` 的 `[autoload]` 节当前只声明了 `Sprites / Portraits / VFX / Atlas`。仓库内 12 个 .gd 文件已经按 `GlobalState.foo()` 形式调用，但 `GlobalState` 这个标识符在 GDScript parse 时是 **未声明** 的——任何尝试运行的脚本都会立刻报错。

**解决路径**：
1. 走 `/architecture-decision` 写 `ADR-XXXX-autoload-contract`，定义 4 个核心 autoload 的注册顺序（建议：`GlobalState` 排在最前，因为 SaveManager / SceneRouter / Dialogue / UIRoot 都可能在 `_ready` 中读它）。
2. ADR Accepted 后，由 godot-gdscript-specialist 修改 `project.godot` `[autoload]` 节，名字必须是 `GlobalState`（保持与现有 12 个调用点一致），路径 `*res://scripts/autoload/global_state.gd`。
3. 同步注册 `SaveManager / SceneRouter / Dialogue / UIRoot`——本 GDD 不锁这些，但同 ADR 一并处理避免反复改 project.godot。

**验证**：项目能在 Godot 4.6 编辑器里 launch 不报"Identifier 'GlobalState' not declared"。

### I.2 Autoload 加载顺序冻结（BLOCKING）

**问题**：本 GDD §F.5 的 load-path UI 契约（reset/from_dict 静默 + Stat Panel UI 在 `load_finished` 时 re-read）暗中假设 `GlobalState._ready()` 在 `SaveManager._ready()` 之前完成。如果顺序反过来，SaveManager 试图 `from_dict(...)` 时 GlobalState 的 `_stats / _vars / _affinity` 还没初始化，会 KeyError。

**解决路径**：在 §I.1 的 ADR 里**显式声明**加载顺序：`GlobalState → Sprites / Portraits / VFX / Atlas → SaveManager → SceneRouter → Dialogue → UIRoot`。任何打破顺序的提议必须经 ADR 修订。

**验证**：ADR Accepted；`project.godot` `[autoload]` 节按顺序排列。

**官方文档复核（Round-2 修订新增）**：godot-specialist Round-2 评审中曾指出"Godot autoload 是按字母序初始化"——这一论断**经官方文档复核为错误**：根据 Godot 4.x docs `tutorials/scripting/singletons_autoload.md` 原文 *"The order of these entries can be adjusted, and they are processed top-to-bottom in the global scene tree"*，autoload 是按 `project.godot` 的 `[autoload]` 节**声明顺序（top-to-bottom）**初始化，与 autoload 名字字母序无关。所以本 GDD §I.2 原契约（"GlobalState 排在最前 → Sprites → SaveManager"按声明顺序排列即可保证 SaveManager `_ready()` 时 GlobalState 已初始化）成立，**无需**用字母序前缀（如 `AGlobalState`）来强制顺序。该复核已 archived 于本节，避免后续评审重复争论。

### I.3 gdunit4 测试框架安装（BLOCKING）

**问题**：本 GDD §H 的 20 条 AC（H.1–H.20，Round-2 新增 H.17–H.20）全部是 `Logic` 类型（gdunit4 自动化单元测试），但 `addons/` 目前是空的（只有 `.gitkeep`）。在 gdunit4 安装之前，所有 AC 都是"待实现"状态——既无法跑、也无法证伪。

**解决路径**：走 `/test-setup` 安装 gdunit4 到 `addons/gdunit4/`；同时建立 `tests/unit/stat_system/` 目录骨架与命名规范（按 §H 测试夹具契约）。

**验证**：`addons/gdunit4/` 存在；能用 `--headless --script tests/...` 命令行跑通一个 trivial 的 sample 测试。

### I.4 类型化与 idiom 修订（IMPORTANT，可与 §I.1 同 ADR）

**问题**（design-review godot-specialist 提出；Round-2 加严：实装与 GDD 契约漂移）：当前 `scripts/autoload/global_state.gd` 与本 GDD §C.1 / §C.4 / §C.6 / §D.1 / §D.2 / §E.6 / §E.8 多处声明的契约不一致——上一轮只改 GDD 没碰代码。落地 ADR 必须把以下 8 项实装漂移一并修复（任一项不修，对应 AC 跑不通）：

1. **缺少 `class_name GlobalState`**：下游静态类型调用受限（autoload 名本身可作 identifier，但无法在测试 / 工具脚本里 `var gs: GlobalState = ...`）。修：文件首行加 `class_name GlobalState`。
2. **`Dictionary` 未声明 K/V 类型**：`var _stats: Dictionary` 应为 `var _stats: Dictionary[String, int]`（Godot 4.4+ 支持，本项目 Godot 4.6 完全可用——已通过 WebSearch 复核 4.4 升级笔记，typed Dictionary 是 4.4 的已发布特性，4.6 仍稳定）。同步改 `_vars / _affinity / _triggered / _era_markers`。
3. **`clamp(...)` → `clampi(...)`**：D.1 / D.2 已显式要求 `clampi`，避免被 float 污染返回类型（特别是 from_dict 路径加载 JSON 浮点时）。
4. **信号 payload 与 §C.6 不一致（Round-2 新发现）**：实装当前是 3 参 `(stat_id, delta, new_value)`，GDD §C.6 已锁 4 参 `(stat_id, old_value, new_value, requested_delta)`。修：捕获 clamp 前 `old_value` 快照，emit 时按 4 参顺序传递；同步 `var_changed / affinity_changed`；`chapter_changed` 改 2 参 `(old, new)`。
5. **AFFINITY 实装与 §C.4 schema 不一致（Round-2 新发现）**：当前 `AFFINITY_INIT` + 全局 `AFFINITY_MIN/MAX = ±10`；GDD 已 v1 升级为 per-NPC `AFFINITY_CONFIG[npc_id] = {init, min, max}` schema（jiejie.max=15、caozhengdong.min=-15 用于"被托住" / "宿敌"两条 pillar 承重）。修：合并为 `AFFINITY_CONFIG`，删除全局常量，change_affinity 用 `AFFINITY_CONFIG[npc_id].min/max` 走 D.2 公式。
6. **`from_dict()` 缺自愈式 cast + clampi（Round-2 新发现）**：实装当前是 raw 直写；§E.6 v1 契约要求 `int(value)` cast → `clampi(...)` clamp → `push_warning if raw != clamped`，覆盖 4 集合（stats / vars / affinity）。Round-2 进一步要求覆盖 unknown ID 跳过 + push_warning（H.17）、chapter 越界写入 + push_warning（H.18）、`_triggered` falsy / 错类型容错（§E.8）。
7. **`to_dict()` 缺 keys sort（Round-2 新发现）**：§E.8 契约要求对 `_triggered.keys()` 与 `_era_markers.keys()` 调 `sort()` 后再写返回字典，保证 H.10 round-trip 字面级稳定。修：`d["triggered"] = _triggered.keys(); d["triggered"].sort()`，同步 era_markers。
8. **`_emit_depth` 再入守卫缺失（Round-2 新增 / R-S4）**：§C.6 / §E.3 已锁定再入保护契约，实装侧需在每个 `change_*` 函数入口检查并 push_error；详见 §C.6"再入保护契约"段。同时 §F.5 invariant 要求订阅 GDD 用 `Object.CONNECT_DEFERRED`，是双重保险的另一半。

**额外（Round-2 新增 / R-S6）**：`_ready()` 必须先调 `_validate_configs(STATS_CONFIG, VARS_CONFIG, AFFINITY_CONFIG)` 验证 `min ≤ init ≤ max`，违反则 `push_error` + `assert(false)` 阻断启动；详见 §F.5 启动 config 校验 invariant 与 §H.19 AC。

**解决路径**：实装侧 8 + 1 项全部由同一 ADR（`ADR-XXXX-stat-system-contract`，与 §I.1 autoload contract ADR 平行或同 ADR 内分两节）锁定；godot-gdscript-specialist 改 `global_state.gd` 时按本节顺序逐项落实。

**验证**：
- §H.1–H.20 全部 20 条 AC 在 gdunit4 跑通
- 所有 Dictionary 字段已声明 typed K/V
- 信号 4 参 / 2 参 payload 正确
- AFFINITY_CONFIG per-NPC schema 落地
- from_dict 自愈 / to_dict sort 落地
- _emit_depth 再入守卫与 _validate_configs 启动校验落地
- 订阅 GDD 在自己的 Dependencies 节复述 `CONNECT_DEFERRED` 推荐

### I.5 后续 follow-up（NICE-TO-HAVE，不阻塞下游 GDD）

- **STATS_CONFIG / VARS_CONFIG / AFFINITY_CONFIG 外置为 .tres**：见 Open Questions Q4。当前以代码常量形式落地，扩展章节时需要改 .gd 文件而不是数据资源——可接受，但写 ADR 时一并讨论是否 v2 重构。
- **Stat Panel UI 的 effective ≠ requested 软反馈方案**：§C.6 的 4 元组 payload 已经把信息暴露出来；具体如何渲染（softer 飘字、灰色 dash、停顿）由 [[stat-panel-ui]] 与 UX 规格 `design/ux/hud.md` 设计，本 GDD 不强制。

**总结**：§I.1 / I.2 / I.3 是**真**前提，下游 GDD 与实现都 BLOCKS-ON。§I.4（Round-2 加严：实装侧 8 项契约漂移 + `_validate_configs` 启动校验）与 v1 设计契约一致性强相关，**必须**与 §I.1 同 ADR 处理。§I.5 是 v2 follow-up，不阻塞。

> **Round-2 评审复核备忘**：godot-specialist Round-2 提出的两条结构性疑问已经过 Web/Context7 官方文档复核：(1) `Dictionary[String, int]` 类型 — 在 Godot 4.4+ 已支持，本项目 Godot 4.6 完全可用，§C.1 / §I.4 typed Dictionary 声明正确；(2) autoload 加载顺序 — 按 `project.godot` 声明顺序（top-to-bottom），不是字母序，§I.2 原契约成立。两条已分别归档于 §I.4 第 2 项与 §I.2"官方文档复核"段，避免后续 round 重复争论。

## Open Questions

| # | Question | Owner | 目标解决路径 |
|---|---|---|---|
| Q1 | Stat System 是否需要"原子事务"接口（一次提交多个 delta，失败回滚）？ | game-designer | 若 Cutscene Runner 出现"5 个属性同帧变更，其中 1 个失败要回滚"需求，开 ADR；demo 范围内不需要 |
| Q2 | E.5 chapter 非法跳转是否要在代码层加白名单校验？ | godot-gdscript-specialist | 由 v1 ADR 决定；当前选择"GDD 规则约束 + code review 兜底"，但若代码评审发现违反成本高，应升级为运行时校验 |
| Q3 | from_dict 的 schema 版本字段如何处理？ | save-load GDD | 本 GDD 决定不感知版本；SaveManager 在外层做版本迁移再调 from_dict。具体 schema 由 Save/Load GDD 定义 |
| Q4 | 后续章节扩展时如何避免每次都改本 GDD 的 stat / var / affinity 表？ | game-designer | 提议把 STATS_CONFIG / VARS_CONFIG / AFFINITY_INIT 外置为 .tres 资源；提到 ADR 时一并讨论 |
| Q5 | demo_increment_table 的存放位置（per-event JSON vs 统一表 vs 内嵌 cutscene 指令）？ | event-flow / cutscene-runner GDD | 不属于本 GDD 范围，但本 GDD 在 D.4 已注明该选择不影响 Stat System 接口 |
| Q6 | 是否需要 ADR-XXXX-stat-system-contract 立刻撰写以冻结 v1 接口？ | technical-director | systems-index 高风险项 #2 强烈建议；本 GDD 完成后第一项 ADR 任务 |
