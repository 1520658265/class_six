# Adoption Plan

> **Generated**: 2026-05-31
> **Project phase**: Systems Design（来自 production/stage.txt）
> **Engine**: Godot 4.6（VERSION.md 已锁定，但 technical-preferences.md 字段未填）
> **Template version**: v1.0+

按顺序处理。每完成一项打勾。任何时候可重跑 `/adopt` 复盘剩余缺口。

> ⚠️ **特别说明**：本项目属于"先有代码与遗留 spec、后回填模板规范"的 D2 子情况。现有 26 个 `.gd`、16 个 `.tscn`、12 套 portraits / sprite_frames、`data/dialogue/{prologue,ch1}.json` 都已落地。迁移计划目标是**让模板技能能识别并复用这些产物**，而不是推翻重做。

---

## Step 1: Fix Blocking Gaps

### 1.1 填充 `.claude/docs/technical-preferences.md`

**问题**：所有字段是 `[TO BE CONFIGURED]`。`/architecture-decision`、`/create-architecture`、`/architecture-review` 都会读这份文件，全空会导致 ADR 引擎兼容性检查、命名规范检查、性能预算检查全部失效。

**修复**：手动编辑，至少填入：
- Engine: `Godot 4.6`
- Language: `GDScript`
- Rendering: `GL Compatibility`
- Physics: `Godot Physics 2D`
- 命名约定（`scripts/` 下已成型，按既有惯例落字）
- Engine Specialists: 主 = godot-specialist；语言 = godot-gdscript-specialist；shader = godot-shader-specialist
- 性能预算（Demo 范围给个保守值即可，例如目标 60 fps、内存上限 512 MB）

**Time**: 30 min
- [ ] technical-preferences.md 字段填齐

### 1.2 创建至少一份 `design/gdd/*.md` 模板合规 GDD

**问题**：`design/gdd/` 下 0 份 GDD。所有下游技能（`/create-stories`、`/architecture-review`、`/gate-check`、`/review-all-gdds`）依赖至少存在一份合规 GDD。遗留 8 份 `-spec.md` 在旧位置且不符 8 节结构。

**修复方案**（待方向裁定后再决定迁移策略，见 Step 2.1）：
两种迁移路径，**先回答 Step 2.1 的方向问题再选**：
- 路径 A（推荐）：保留旧 `-spec.md`，在 `design/gdd/` 用 `/design-system retrofit [path]` 逐份建对应标准 GDD（旧文件作为"详细附录"链接过去）
- 路径 B：直接迁移并删旧文件（重构性更强，时间成本更高）

**Time**: 1 session（每份 GDD 约 30–60 min）
- [ ] 至少建好 `design/gdd/game-concept.md`
- [ ] 至少建好 `design/gdd/systems-index.md`

---

## Step 2: Fix High-Priority Gaps

### 2.1 裁定核心方向冲突 ⚠️ 阻断 Step 1.2

**问题**：CLAUDE.md 描述 "Demo 为俯视 4 方向；战斗系统后续讨论"，但 `游戏设计适配-横版格斗RPG-spec.md` 与 `战斗特效动效实现-spec.md` 是横版格斗整套方案。两者不可能都是 demo 的真实方向。

**需要决定**：
- (a) 横版格斗是已废弃的早期方向 → 把这两份 spec 移到 `docs/archive/` 并在头部标 `Status: Superseded`
- (b) 横版格斗仍计划在某个章节启用 → 标 `Status: Deferred` 注明启用时机
- (c) 当前 demo 就是俯视、横版格斗只是脑暴 → 先 `Superseded` 然后视后续需求再开

**Time**: 5 min（人工决定）
- [ ] 决定方向并标注两份 spec 状态

### 2.2 创建 `design/gdd/game-concept.md`

**问题**：核心定位文档不存在。`/map-systems`、`/design-system`、`/gate-check` 都需要它作为"游戏是什么"的锚。

**修复**：`/reverse-document concept` 从 `docs/reference/` 故事线 + 遗留 spec 凝练。

**Time**: 1 session
- [ ] game-concept.md 落地

### 2.3 创建 `design/gdd/systems-index.md`

**问题**：systems-index 缺失。`/gate-check`、`/create-stories`、`/architecture-review` 都按它来判断系统设计完成度。

**修复**：`/map-systems` 把 demo 范围分解为系统（如：dialogue / cutscene-runner / scene-routing / save-system / stat-system / npc-interaction / asset-loading 等）。

**Time**: 1 session
- [ ] systems-index.md 落地，覆盖 demo 范围所有系统

### 2.4 retrofit 8 份遗留 spec 到 `design/gdd/`

**问题**：每份遗留 spec 都至少缺 4 节（普遍缺 Player Fantasy / Edge Cases / Tuning Knobs / Acceptance Criteria；部分缺 Formulas / Dependencies）。

**修复**：每份各跑一次 `/design-system retrofit docs/design/[file].md` 生成 `design/gdd/` 下对应标准 GDD：

- [ ] `属性变量定义-spec.md` → `design/gdd/stat-system.md`
- [ ] `npc-data-spec.md` → `design/gdd/npc-system.md`
- [ ] `items-spec.md` → `design/gdd/item-system.md`
- [ ] `event-flow-prologue-ch1.md` → `design/gdd/event-flow.md`（或保留为 narrative 引用）
- [ ] `美术资产清单-spec.md` → 移到 `art-bible.md` 或保留为美术清单引用
- [ ] `游戏设计适配-横版格斗RPG-spec.md` → 视 Step 2.1 决定，可能归档
- [ ] `战斗特效动效实现-spec.md` → 同上
- [ ] `README.md` → 更新索引指向新路径

**Time**: 8 sessions（每份 30–60 min）

### 2.5 创建 Required ADR 列表

**问题**：尚无 ADR。`scripts/autoload/` 9 个全局单例的职责边界、`save_manager` / `scene_router` / `dialogue` / `cutscene_runner` 的协议都只在代码里。

**修复**：先 `/create-architecture` 出主架构蓝图与 Required ADR 清单；再用 `/reverse-document architecture` 把现有架构反向吐成 ADR 草稿。

**Time**: 1 session 设计 + 每份 ADR 约 20–30 min
- [ ] 主架构蓝图落地
- [ ] Required ADR 清单生成
- [ ] 至少 5 份核心 ADR（autoload 体系、scene routing、save format、dialogue data 协议、cutscene runner）

### 2.6 创建 `docs/architecture/control-manifest.md`

**问题**：无 layer 规则表。stories 没有可遵循的 Required / Forbidden / Guardrails。

**修复**：`/create-control-manifest`（前置：至少 3 份 Accepted ADR）

**Time**: 30 min
- [ ] control-manifest.md 落地，含 `Manifest Version:` 头部

### 2.7 创建 `docs/architecture/architecture-traceability.md`

**问题**：无 GDD ↔ ADR ↔ TR ↔ Story 的映射矩阵。

**修复**：由 `/architecture-review` 自动产出。

**Time**: 由 2.5/3.1 顺带生成
- [ ] 由 `/architecture-review` 写入

### 2.8 注册 entities / TR-IDs

**问题**：`design/registry/entities.yaml` 与 `docs/architecture/tr-registry.yaml` 都是空骨架（仅注释和示例）。

**修复**：在 `/design-system retrofit` 与 `/architecture-review` 流程中自然填充。

**Time**: 由 2.4 / 3.1 顺带生成
- [ ] entities.yaml 至少含 demo NPC / 道具 / 属性 / 隐性变量
- [ ] tr-registry.yaml 至少含核心 TR

---

## Step 3: Bootstrap Infrastructure

### 3a. Register existing requirements (creates tr-registry.yaml entries)
Run `/architecture-review` —— 即使 ADR 已存在，本次运行从 GDD + ADR 引导写入 TR registry。
**Time**: 1 session
- [ ] tr-registry.yaml 写入条目

### 3b. Create control manifest
Run `/create-control-manifest`
**Time**: 30 min
- [ ] docs/architecture/control-manifest.md 写入

### 3c. Create sprint tracking file
Run `/sprint-plan update`
**Time**: 5 min（若已有 markdown sprint plan；本项目无）
- [ ] production/sprint-status.yaml 写入

### 3d. Set authoritative project stage
Run `/gate-check [current-phase]`
**Time**: 5 min
- [ ] production/stage.txt 由 gate-check 校准（当前为 Systems Design 手填）

---

## Step 4: Medium-Priority Gaps

### 4.1 创建 `production/epics/`
**问题**：epics 目录不存在，无 sprint 入口。
**修复**：`/create-epics`（前置：架构 + control manifest 完成）
**Time**: 1 session
- [ ] 至少一个 epic 落地

### 4.2 把 `data/dialogue/_format.md` 链接到 dialogue GDD
**问题**：自家 JSON 对白格式约定散在 data 目录里，未被 GDD 引用。
**Time**: 5 min
- [ ] dialogue GDD 引用 `_format.md`

---

## Step 5: Optional Improvements

### 5.1 起 gdunit4 测试框架
Run `/test-setup`（可延后到 architecture 完成后）
**Time**: 30 min
- [ ] tests/ 框架成型 + 至少 1 条 smoke test

### 5.2 创建 `design/quick-specs/` 与 `design/ux/`
仅在有具体调整 / UX 工作时再建。
- [ ] 按需

### 5.3 建立美术资产清单与 art-bible 的映射
若 Step 2.1 裁定保留 `美术资产清单-spec.md`，可考虑跑 `/art-bible` 把它升级为正式 art bible。
- [ ] 按需

---

## What to Expect from Existing Stories

本项目当前**没有 stories**。所有现有代码与场景是 demo 切片产物，未经过 `/dev-story` 流程。后续若要追溯改造，建议在架构与 GDD 回填完成后，从下一批新增功能开始走 `/create-epics` → `/create-stories` → `/dev-story` 正规流程，**不要回头拿现有代码塞进 stories**。

---

## Re-run

完成 Step 3 后重跑 `/adopt` 验证 BLOCKING / HIGH 是否清零。新一轮会反映项目当前真实状态。
