# Project Stage Analysis — 元生的六年级

**Date**: 2026-05-31
**Stage**: Systems Design（来自 `production/stage.txt`）
**Stage Confidence**: CONCERNS — 自动启发式与显式声明冲突，且现有产物属于 D2 子情况（先有代码 / 资源 / 遗留 spec，后回填模板规范文档）

---

## 一、项目盘点

| 维度 | 现状 |
|---|---|
| 引擎 | Godot 4.6 已锁定（`docs/engine-reference/godot/VERSION.md`）|
| 代码 | 26 个 `.gd`：autoload×10、character×4、level×4、ui×5、shared×3 |
| 场景 | 16 个 `.tscn`：levels×9、ui×5、characters×2、main×1 |
| 资源 | sprite_frames×13、portraits×12、atlas / vfx / asset_ids 已具备 |
| 数据 | `data/dialogue/`：`prologue.json`、`ch1.json`、`_format.md`（自家 JSON 对白格式）|
| 设计文档 | 8 份遗留 spec 全在 `docs/design/`（旧位置、`-spec.md` 命名、未按模板 8 节）|
| 架构 | `docs/architecture/` 不存在；ADR 0 份；无 control manifest；无 TR registry |
| production | `stage.txt`、`review-mode.txt` 已建；无 sprint / milestone / roadmap |
| 测试 | `tests/unit/` 空（仅 .gitkeep）；`tests/fixtures/` 有 3 张测试用 png |
| prototypes | 不存在 |

### 遗留 spec 列表（`docs/design/`）

- `属性变量定义-spec.md` — 4 项显性属性 + 3 项隐性变量 + 11 项 NPC 好感度
- `npc-data-spec.md` — Demo 范围全部 NPC 数据表
- `items-spec.md` — Demo 4 件道具
- `event-flow-prologue-ch1.md` — 序章 + 第一章事件流程图（Mermaid）
- `美术资产清单-spec.md` — 32×32 像素风全资产清单
- `游戏设计适配-横版格斗RPG-spec.md` — 横版格斗 RPG 适配 ⚠️ 与 CLAUDE.md "俯视 4 方向" 描述冲突
- `战斗特效动效实现-spec.md` — 8 个特效动效方案 ⚠️ 同上
- `README.md` — 索引页

---

## 二、Completeness Overview

- **Design**：约 30% — 8 份遗留 spec 内容详实，但格式不符模板（无 8 节结构、命名不符 `[system-slug].md`、位置不对、无 `systems-index.md`、无 `game-concept.md`）
- **Code**：约 50% — Demo 切片骨架已搭，autoload 体系成型，但无对应 GDD 与 ADR 锚定
- **Architecture**：0% — 无 ADR、无 control manifest、无 TR registry、无主架构文档
- **Production**：5% — 仅设阶段与审阅模式，工作流入口为空
- **Tests**：约 5% — 测试目录骨架在，无任何用例

---

## 三、缺漏与澄清问题

### Gap 1：设计文档形态不匹配模板
遗留 8 份 `-spec.md` 在 `docs/design/`，没有按 8 节结构（Overview / Player Fantasy / Detailed Rules / Formulas / Edge Cases / Dependencies / Tuning Knobs / Acceptance Criteria）。
**问**：保留旧 `-spec.md` + 用 `/adopt` 在 `design/gdd/` 建对应标准 GDD 引用过去，还是直接迁移并删旧文件？

### Gap 2：核心方向冲突
`CLAUDE.md` 写 "Demo 为俯视 4 方向；战斗系统后续讨论"，但 `游戏设计适配-横版格斗RPG-spec.md` 与 `战斗特效动效实现-spec.md` 是横版格斗整套方案。
**问**：这两份 spec 是已废弃的早期方向？还是仍计划在后续章节启用？要不要标 `Superseded` 或挪去 `docs/archive/`？

### Gap 3：无架构记录
`scripts/autoload/` 9 个全局单例的职责边界、`save_manager` / `scene_router` / `dialogue` / `cutscene_runner` 的协议都只存在于代码里。
**问**：用 `/reverse-document architecture` 反向输出 ADR + 架构总图？还是先 `/create-architecture` 主动设计目标架构后用 ADR 锁住？

### Gap 4：核心概念文档缺失
没有 `game-concept.md` / `game-pillars.md`。
**问**：要不要从遗留 spec + `docs/reference/` 故事线反向凝练一份 `game-concept.md`？

### Gap 5：测试空白
`tests/unit/` 仅有 `.gitkeep`，无 gdunit4 / GUT 工程。
**问**：Demo 阶段先放着、产品级再补；还是现在先 `/test-setup` 起 gdunit4 框架？

### Gap 6：production 全空
`production/sprints/`、`production/milestones/` 不存在。
**问**：目前用其它工具（飞书 / Notion / 自家清单）跟踪开发任务？还是接下来用 `/sprint-plan` 建首期 sprint？

---

## 四、推荐下一步（按优先级）

1. **`/adopt`** — 审计 8 份遗留 spec 的格式合规度，给出按章节缺失分级的迁移计划（纯只读，最关键）
2. 回答上面 6 个澄清问题，尤其是 Gap 2（横版格斗的去留）
3. **`/reverse-document concept`** — 凝练 `game-concept.md`
4. `/design-system retrofit [path]` — 按 `/adopt` 的结果逐份补齐缺失章节
5. `/create-architecture` — 出主架构蓝图 + Required ADR 清单
6. `/architecture-decision (×N)` — 按 Required ADR 清单补 ADR
7. `/architecture-review` — 校验 TR 覆盖
8. `/gate-check` — 进 Pre-Production 前的卡点
9. `/test-setup` — gdunit4 框架（可延后到 architecture 完成后）

---

## 五、Stage 校准建议

当前 `stage.txt = Systems Design` 与代码已成型的事实不一致。建议在完成 `/adopt` + GDD 回填 + `/create-architecture` 之后，让 `/gate-check` 显式裁定下一阶段，再调整 `stage.txt`。

模型可能的目标态：先把"补设计 + 补架构"作为 Systems Design 的回填扫尾，等 ADR + control manifest 成型后再进 Pre-Production。
