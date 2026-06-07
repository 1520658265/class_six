# Adoption Plan

> **Generated**: 2026-06-01
> **Project phase**: Systems Design
> **Engine**: Godot 4.6 (GL Compatibility, GDScript)
> **Template version**: v1.0+
> **Review mode**: lean
> **Prior plan**: [docs/adoption-plan-2026-05-31.md](adoption-plan-2026-05-31.md)（视角范式决策前的旧计划，仅作历史参考）

Work through these steps in order. Check off each item as you complete it.
Re-run `/adopt` anytime to check remaining gaps.

---

## 上下文摘要

- **2026-06-01 决策**：视角范式定为 **俯视 4 方向**（以代码为准），早期"横版格斗 RPG"两份 spec 已归档于 [docs/archive/横版格斗-archive/](archive/横版格斗-archive/README.md)。
- **战斗 5 系统**（Combat Core / Courage / Skill / Emotion / VFX）保留，但 GDD 需按俯视范式新写或 retrofit。
- **`game-concept.md` / `systems-index.md` 已就地修订**（2026-06-01），不再列入本 plan 工作项。
- **stat-system.md** 已 Approved（2026-05-31，Round-2 修订），是 demo 范围内唯一一份完整合规的 GDD。

## Adoption Audit Summary

```
Phase detected:  Systems Design
Engine:          configured (Godot 4.6)
GDDs audited:    1 (1 fully compliant: stat-system.md)
ADRs audited:    0
Stories audited: 0

Gap counts:
  BLOCKING: 0
  HIGH:     3 — bootstrapping incomplete
  MEDIUM:   3
  LOW:      8
```

---

## Step 1: Fix Blocking Gaps

无 BLOCKING gap。

---

## Step 2: Fix High-Priority Gaps

### 2.1 — `docs/architecture/control-manifest.md` 不存在

**Problem**：模板各类 stories 与 `/story-done` 都依赖 control-manifest 的 Required / Forbidden / Guardrails 规则与 `Manifest Version:` 戳。当前文件不存在，所有引用都会回退到"无规则"状态。

**Fix**：`/create-control-manifest`

**Time**: 30 min

- [ ] `docs/architecture/control-manifest.md` 已创建并带 `Manifest Version:` 字段

### 2.2 — `docs/architecture/` 0 个 ADR（stat-system.md §I 已锁 BLOCKING-ON）

**Problem**：stat-system GDD §I.1 / §I.4 已经把 2 份 ADR 标为下游与实装都 BLOCKED-ON：

- `ADR-XXXX-stat-system-contract` — 冻结 v1 接口（getter/setter/signal payload/clamp 公式/serialization 契约）+ 实装侧 8+1 项契约漂移修复（4 元组 signal、`AFFINITY_CONFIG` per-NPC、`from_dict` 自愈 cast、`to_dict` keys sort、`_emit_depth` 再入守卫、`_validate_configs` 启动校验、`Dictionary[K,V]` 类型化、`clampi`、`class_name GlobalState`）
- `ADR-XXXX-autoload-contract` — 注册 `GlobalState / SaveManager / SceneRouter / Dialogue / UIRoot` 到 `project.godot [autoload]`，按声明顺序冻结加载顺序（Godot 4.x 是 top-to-bottom，不是字母序）

**Fix**：
1. `/architecture-decision` 写 `ADR-0001-stat-system-contract`
2. `/architecture-decision` 写 `ADR-0002-autoload-contract`
3. ADR 必须含全部 6 节：Status / Context / Decision / Consequences / ADR Dependencies / Engine Compatibility / GDD Requirements Addressed（缺 Status 会让 `/story-readiness` 静默通过 ADR 检查 — BLOCKING）

**Time**: 1 session（两份 ADR 紧密耦合，建议同会话写完）

- [ ] `docs/architecture/adr-0001-stat-system-contract.md` 已创建并 Status=Accepted
- [ ] `docs/architecture/adr-0002-autoload-contract.md` 已创建并 Status=Accepted

### 2.3 — `tr-registry.yaml` 仅占位（`requirements: []`）

**Problem**：stat-system GDD 的 H.1–H.20 共 20 条 AC 还未注册到任何 TR-ID。`/create-stories` 没有稳定的 requirement ID 可以引用。

**Fix**：`/architecture-review` — Phase 8 会从 stat-system GDD 与 ADR-0001 的接口冻结条款里提取 requirements，append 到 `tr-registry.yaml` 末尾（永不 renumber）。

**Time**: 1 session（review 本身扫一遍 GDD + ADR）

**Sequencing**：必须等 Step 2.2 的两份 ADR 落地后再跑（registry 依赖读 ADR Status 字段）。

- [ ] `docs/architecture/tr-registry.yaml` 含 stat-system 的 TR-stat-NNN 系列条目

---

## Step 3: Bootstrap Infrastructure

### 3a. `tr-registry.yaml` 已在 Step 2.3 处理

跳过：与 Step 2.3 同一动作。

### 3b. 创建 control manifest

已在 Step 2.1 处理。

### 3c. 创建 sprint tracking file

`production/sprint-status.yaml` 不存在；当前没有 sprint markdown 也无 milestone 文件。

**Fix**：`/sprint-plan update`

**Time**: 5 min

- [ ] `production/sprint-status.yaml` 创建

### 3d. 设定权威 project stage

`production/stage.txt` 现为 `Systems Design`，但项目已有 26 份代码、9 份 levels、stat-system Approved。Step 2 落地后实际已经具备进入 Pre-Production 的格式条件。

**Fix**：等 Step 2 完成 + Step 3c 创建 sprint-status 后跑 `/gate-check pre-production`

**Time**: 5 min（gate-check 本身），命题门可能让进度回退到补漏

- [ ] `production/stage.txt` 写入权威 phase（保持 Systems Design 或前进 Pre-Production）

---

## Step 4: Medium-Priority Gaps

### 4.1 — `docs/architecture/architecture-traceability.md` 不存在

**Problem**：跨系统的 GDD ↔ ADR ↔ Story 追溯矩阵无持久化文件。`/architecture-review` 跑出的关系只在该 session 输出。

**Fix**：`/architecture-review` Phase 9 会写这份矩阵 — 与 Step 2.3 同一命令一并产出。

**Time**: 与 Step 2.3 复用

- [ ] `docs/architecture/architecture-traceability.md` 创建

### 4.2 — `美术资产清单-spec.md` 标题与归档方向冲突

**Problem**：标题写 "32×32 像素 · 横版格斗 RPG"，正文是资产清单本身。视角范式既然定为俯视，标题需修订。

**Fix**：人工编辑 1 行
- 文件：`docs/design/美术资产清单-spec.md` 第 1 行
- 改：`# 美术资产清单（32×32 像素 · 横版格斗 RPG）`
- 为：`# 美术资产清单（32×32 像素 · 俯视 4 方向 RPG）`

**Time**: 5 min

- [ ] `美术资产清单-spec.md` 标题已修订

### 4.3 — 5 份遗留 spec 缺 `**Status**:` header

**Problem**：`属性变量定义-spec.md` / `npc-data-spec.md` / `items-spec.md` / `event-flow-prologue-ch1.md` / `美术资产清单-spec.md` 都没有 Status 字段。它们不是模板规范的 GDD（在 `docs/design/` 而非 `design/gdd/`），但作为 stat-system "事实源"被引用，缺 Status 让评审看不出"是否已经被超越"。

**Fix**：每份文件 header 加一行（建议值 `Approved` 或 `Reference`）
- 5 份文件、各加 1 行

**Time**: 15 min

- [ ] 5 份 legacy spec 已补 Status

---

## Step 5: Optional Improvements

### 5.1 — 6 份 legacy spec 留在 `docs/design/`，未对应到 `design/gdd/[system-slug].md`

**Problem**：模板期望 GDD 在 `design/gdd/`，但 5 份 spec（`属性变量定义` / `npc-data` / `items` / `event-flow` / `美术资产清单`）+ README 留在 `docs/design/`。stat-system GDD 已经在内容上把它们 retrofit 进 `design/gdd/stat-system.md`，但 NPC / Item / Event Flow / Asset Loading 几个系统还没有对应 GDD。

**Fix**：按 `systems-index.md` 第三节"设计顺序"逐个 retrofit
- `/design-system retrofit design/gdd/asset-loading.md` （source: 5 个 autoload + technical-preferences）
- `/design-system retrofit design/gdd/save-load.md` （source: `save_manager.gd`）
- `/design-system retrofit design/gdd/dialogue.md` （source: `dialogue.gd` + `data/dialogue/_format.md`）
- `/design-system retrofit design/gdd/cutscene-runner.md` （source: `cutscene_runner.gd`）
- `/design-system retrofit design/gdd/event-flow.md` （source: `event-flow-prologue-ch1.md`）
- `/design-system retrofit design/gdd/npc-system.md` （source: `npc-data-spec.md` + `npc_controller.gd`）
- `/design-system retrofit design/gdd/item-system.md` （source: `items-spec.md`）
- `/design-system retrofit design/gdd/scene-routing.md` （source: `scene_router.gd` + `scene_door.gd`）
- `/design-system retrofit design/gdd/interaction.md` （source: `interact_zone.gd`）
- `/design-system retrofit design/gdd/era-marker.md` （source: `era_marker_toast.gd`）
- `/design-system retrofit design/gdd/stat-panel-ui.md` （source: `stat_panel.gd`）
- `/design-system retrofit design/gdd/chapter-title.md` （source: `chapter_title.gd`）
- `/design-system retrofit design/gdd/main-menu.md` （source: `main_menu.gd`）

**留为新写**（无对应 spec）：
- `/design-system input-mapping`
- `/design-system character-controller-topdown`
- `/design-system camera`
- `/design-system wallet-credit`
- `/design-system combat-core`（俯视版，可参考 `docs/archive/横版格斗-archive/` 复用情绪与胆量解锁）
- `/design-system courage-resource`
- `/design-system skill-tree`
- `/design-system combat-vfx`

**Time**: 每份 retrofit 1 session（按优先级排，不必一次做完）

- [ ] 13 份 retrofit GDD 全部完成（或推到下一轮 `/adopt`）
- [ ] 8 份新写 GDD 全部完成（或推到下一轮 `/adopt`）

### 5.2 — `美术资产清单-spec.md` 不符合 8 节 GDD 模板（不阻塞）

**Problem**：是个素材清单文档而非 system GDD。技术上不应套 GDD 8 节模板。

**Fix**：保持现状，不强制 retrofit。在 `docs/design/README.md` 注明它是清单类而非 spec 类即可（已在 README 索引中显示）。

**Time**: 0（已合理）

- [x] 已识别，不动

---

## What to Expect from Existing Stories

`production/epics/` 不存在，stories 数为 0。Demo 阶段还没有进入 story-driven 实现期，本节暂不适用。

到达 Pre-Production 后由 `/create-epics` + `/create-stories` 生成首批 stories；新建的 stories 会自动满足 TR-ID + Manifest Version + ADR 引用三个 MEDIUM 检查。

---

## 推荐执行顺序

```
Step 2.2 (写 2 份 ADR)
  └─> Step 2.3 + Step 4.1 (/architecture-review 一并产出 tr-registry + traceability)
        └─> Step 2.1 (/create-control-manifest)
              └─> Step 3c (/sprint-plan update)
                    └─> Step 3d (/gate-check pre-production)
                          ├─> Step 4.2 + Step 4.3 (5 + 1 行人工编辑)
                          └─> Step 5.1 (按 systems-index 第三节逐个 retrofit)
```

**关键**：Step 2.2 是所有下游基础设施 bootstrap 的根 — `/architecture-review` 依赖读 ADR Status 字段才能注册 TR；`tr-registry` 不就位则后续 `/create-stories` 没有稳定 ID 引用。

---

## Re-run

完成 Step 2 + Step 3 之后跑 `/adopt`，新 plan 会反映：
- HIGH 应清零（control-manifest + 2 份 ADR + tr-registry 都到位）
- MEDIUM 看 Step 4 推进多少
- LOW 看 Step 5 retrofit 推进多少
- 可能新增 BLOCKING：如果新写的 ADR 缺 `## Status` 或 `## ADR Dependencies`，下次 `/adopt` 会标 BLOCKING。
