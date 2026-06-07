# Systems Index

> **Project**: 《元生的六年级》— 2D 俯视 4 方向 RPG
> **Scope**: Demo 切片（序章 + 第一章）
> **Last Updated**: 2026-06-01（视角范式从横版改为俯视 4 方向，stat-system 已 Approved，等待 lean re-review）

本文档列出 demo 范围内所有系统、依赖关系、优先级、设计顺序与当前状态。

---

## 一、系统枚举（按层级）

### Foundation 层（无依赖）

| # | 系统 | 描述 | 来源 | 优先级 | 状态 |
|---|---|---|---|---|---|
| 1 | **Stat System** | 4 项显性属性 + 3 项隐性变量的存储、变更、信号广播 | 显式（属性变量定义-spec.md）| MVP | Approved → [GDD](stat-system.md) · [Review Log](reviews/stat-system-review-log.md) |
| 2 | **Asset Loading** | 角色/立绘/atlas/vfx 通过统一 ID 加载 | 显式（asset_ids.gd / sprites / portraits / atlas / vfx）| MVP | Not Started |
| 3 | **Save / Load** | 状态持久化、存档点触发、加载恢复 | 显式（save_manager.gd / 存档点）| MVP | Not Started |
| 17 | **Input Mapping** | 输入抽象层（键盘 + 手柄 Full），UI 与战斗都需要 | 隐式（technical-preferences）| MVP | Not Started |

### Core 层（依赖 Foundation）

| # | 系统 | 描述 | 依赖 | 优先级 | 状态 |
|---|---|---|---|---|---|
| 4 | **Scene Routing** | 场景间切换、保持持久化 NPC / 状态、过场过渡 | Asset Loading | MVP | Not Started |
| 7 | **Character Controller（俯视 4 方向）** | 4 方向移动、面向、动画状态机；攻击/受伤/闪避能力扩展 | Asset Loading, Input Mapping | MVP | In Progress |
| 18 | **Camera** | 跟随主角、关卡边界、cutscene 锁定 | Character Controller | MVP | Not Started |
| 5 | **Dialogue** | JSON 驱动对白、立绘切换、选项分支 | Asset Loading, Stat System | MVP | Not Started |
| 6 | **Cutscene Runner** | 事件流程图驱动的脚本化序列（NPC 移动、对白、属性变更）| Dialogue, Scene Routing, Stat System | MVP | Not Started |
| 6a | **Event Flow** | 按 event-flow-prologue-ch1.md 的 mermaid 图驱动顺序与分支 | Cutscene Runner, Save/Load | MVP | Not Started |
| 8 | **NPC System** | NPC 数据载入、初始好感度、出场触发条件、对话开关 | Character Controller, Dialogue, Stat System | MVP | Not Started |

### Feature 层（依赖 Core）

| # | 系统 | 描述 | 依赖 | 优先级 | 状态 |
|---|---|---|---|---|---|
| 9 | **Interaction** | 玩家靠近 NPC / 道具 / 触发器后按 interact 键 | Character Controller, NPC System | MVP | Not Started |
| 10 | **Item System** | 4 件道具自动获得、触发标记、消耗规则（demo 内无背包 UI）| Stat System, Save/Load | MVP | Not Started |
| 11 | **Era Marker** | 触发时弹 toast、累积到全局变量供后续解锁判定 | Stat System, Event Flow | MVP | Not Started |
| 11a | **Wallet & Credit** | 货币持有、鲍师母赊账、心结/钱包羞耻度联动 | Stat System, Dialogue, NPC System | MVP | Not Started |
| 12a | **Combat Core** | HP / Hurt / 攻击判定 / 受伤 frame | Character Controller, Stat System | MVP | Not Started |
| 12b | **Courage Resource** | 勇气槽 / 消耗 / 回复 / 与胆量属性的换算 | Combat Core, Stat System | MVP | Not Started |
| 12c | **Skill Tree** | 按胆量 + 剧情解锁招式：忍着 / 推开他 / 书包砸 / 跑 / 顶回去 / 爆发 / 那你来啊 | Combat Core, Courage Resource, Stat System | MVP | Not Started |
| 12d | **Emotion State** | 自卑 / 护短爆发 / 被记住了 / 地震那天 / 姐姐在底 | Combat Core, Stat System | MVP | Not Started |
| 13 | **Combat VFX** | 8 个单帧特效通过 Tween/Particles/Shader 实现 | Combat Core, Asset Loading | MVP | Not Started |

### Presentation 层

| # | 系统 | 描述 | 依赖 | 优先级 | 状态 |
|---|---|---|---|---|---|
| 14 | **Stat Panel UI** | 显性属性面板 + 飘字 | Stat System | MVP | Not Started |
| 15 | **Chapter Title / Toast** | 章节标题卡、切片标记 toast | Era Marker, Event Flow | MVP | Not Started |
| 16 | **Main Menu** | 主菜单、新游戏、读档 | Save/Load, Scene Routing | MVP | Not Started |

### Polish / Meta

| # | 系统 | 描述 | 依赖 | 优先级 | 状态 |
|---|---|---|---|---|---|
| 19 | **Audio Bus** | BGM / SFX / 对白音 bus 占位，避免后期重构 | (弱耦合) | Post-Demo | Not Started |

---

## 二、依赖图（高风险节点）

**被多个系统依赖的瓶颈**（接口冻结优先级）：

| 系统 | 被依赖次数 | 风险 |
|---|---|---|
| **Stat System** | 9 | 数据契约一旦改动牵一发动全身 — **最高优先级冻结接口** |
| **Asset Loading** | 4 | ID 命名约定必须 v1 就锁，否则资产名拆迁麻烦 |
| **Character Controller** | 5 | 已有俯视 4 方向 base_character_controller.gd，需扩展攻击/受伤/闪避，影响 Camera / NPC / Combat / Interaction |
| **Combat Core** | 4 | 战斗 4 子系统的根，必须先于 Courage / Skill / Emotion |

**无循环依赖** ✅

---

## 三、设计顺序（GDD 写作顺序）

按"Foundation → Core → Feature → Presentation"展开，结合 retrofit 已有 spec 的便利性：

| 顺序 | 系统 | 来源 spec / 代码 | 操作 |
|---|---|---|---|
| 1 | **Stat System** | `属性变量定义-spec.md` | `/design-system retrofit` |
| 2 | **Asset Loading** | `asset_ids.gd` / `sprites.gd` / `portraits.gd` / `atlas.gd` / `vfx.gd` | `/design-system retrofit` |
| 3 | **Save / Load** | `save_manager.gd` | `/design-system retrofit` |
| 4 | **Input Mapping** | 无 spec | `/design-system` 新写 |
| 5 | **Scene Routing** | `scene_router.gd` / `scene_door.gd` | `/design-system retrofit` |
| 6 | **Character Controller（俯视 4 方向）** | `base_character_controller.gd`（已实装俯视 4 方向）| `/design-system retrofit` — 在已有控制器上扩展攻击/受伤/闪避，**关键：不重写**，新增能力叠加 |
| 7 | **Camera** | 无 spec | `/design-system` 新写 |
| 8 | **Dialogue** | `dialogue.gd` / `data/dialogue/_format.md` | `/design-system retrofit` |
| 9 | **Cutscene Runner** | `cutscene_runner.gd` | `/design-system retrofit` |
| 10 | **Event Flow** | `event-flow-prologue-ch1.md` | `/design-system retrofit` |
| 11 | **NPC System** | `npc-data-spec.md` / `npc_controller.gd` | `/design-system retrofit` |
| 12 | **Interaction** | `interact_zone.gd` | `/design-system retrofit` |
| 13 | **Item System** | `items-spec.md` | `/design-system retrofit` |
| 14 | **Era Marker** | `era_marker_toast.gd` | `/design-system retrofit` |
| 15 | **Wallet & Credit** | 无 spec | `/design-system` 新写 |
| 16 | **Combat Core** | `docs/archive/横版格斗-archive/游戏设计适配-横版格斗RPG-spec.md` | `/design-system` 新写俯视战斗 GDD（情绪/胆量解锁机制可从 archive 复用） |
| 17 | **Courage Resource** | 同上 archive | `/design-system` 新写俯视版 |
| 18 | **Skill Tree** | 同上 archive | `/design-system` 新写俯视版（4 方向出招判定盒） |
| 19 | **Emotion State** | 同上 archive | `/design-system retrofit` — archive spec 中的情绪机制与视角无关，可直接 retrofit |
| 20 | **Combat VFX** | `docs/archive/横版格斗-archive/战斗特效动效实现-spec.md` | `/design-system` 新写俯视版（特效类型不变，触发与朝向逻辑改俯视） |
| 21 | **Stat Panel UI** | `stat_panel.gd` | `/design-system retrofit` |
| 22 | **Chapter Title / Toast** | `chapter_title.gd` / `era_marker_toast.gd` | `/design-system retrofit` |
| 23 | **Main Menu** | `main_menu.gd` | `/design-system retrofit` |

> **Audio Bus** 留 Post-Demo，不进设计顺序。

---

## 四、进度追踪

| 状态 | 系统数 |
|---|---|
| Not Started | 20 |
| In Progress | 1 |
| In Review | 0 |
| Designed | 0 |
| Approved | 1 |

> Character Controller 起点：`base_character_controller.gd` 已实装俯视 4 方向 walk/idle，retrofit 阶段在其基础上加战斗能力。

**下一步**：（推荐顺序）
1. ~~`/design-review design/gdd/stat-system.md --depth lean` — lean re-review~~ ✅ APPROVED (2026-05-31)
2. `/architecture-decision` 写 ADR-XXXX-stat-system-contract（冻结 v1 接口 + 实装侧 8+1 项契约漂移修复） + ADR-XXXX-autoload-contract（注册 + 加载顺序，参见 stat-system §I）
3. `/test-setup` 装 gdunit4 到 `addons/`（参见 stat-system §I.3）
4. `/design-system asset-loading` 继续 retrofit 顺序 #2

---

## 五、高风险项

1. **Character Controller 能力扩展（俯视）**：现有 `base_character_controller.gd`（俯视 4 方向 walk/idle）已成型，需在其上扩展攻击/受伤/闪避状态。**不重写**，叠加新能力。视角范式 2026-06-01 决策定为俯视，横版方向已归档于 [docs/archive/横版格斗-archive/](../../docs/archive/横版格斗-archive/README.md)。建议先 ADR 锁定俯视战斗的状态机协议（idle/walk/attack/hurt/dodge 5 态切换），再并行加能力。
2. **Stat System 接口冻结**：被 9 个系统依赖。GDD 完成后立刻 `/architecture-decision` 锁定数据契约（属性名、信号名、变更接口），避免后续牵一发动全身。
3. **Combat 4 子系统耦合**：Core / Courage / Skill / Emotion 必须按顺序设计，不能并行。Skill Tree 全招点亮意味着 Emotion State 也必须 MVP（"爆发"与"那你来啊"依赖情绪状态）。
4. **Event Flow 与 Cutscene Runner 边界**：Event Flow 是"叫什么顺序这个个 cutscene"的中层，Cutscene Runner 是"脚本化指令"运行。两者接口必须在 GDD 阶段明确，避免实现时反复重构。

---

## 六、Acceptance Criteria（index-level）

- [ ] 所有 22 个 MVP 系统的 GDD 完成并通过 `/design-review`
- [ ] 高风险节点（Stat System / Character Controller / Combat Core）的 ADR 完成
- [ ] `/review-all-gdds` 通过（跨 GDD 一致性检查）
- [ ] `/gate-check systems-design` 通过（CD-SYSTEMS / TD-SYSTEM-BOUNDARY / PR-SCOPE 三门）
- [ ] 每个系统的 retrofit 路径明确（哪份 spec 对应哪个 GDD、缺哪几节）

---

> 本 systems-index 作为后续 GDD 写作的路线图。每完成一份 GDD，`/design-system` 会自动更新本文档的进度追踪。任何系统增删改，必须先更新本文档再动 GDD。
