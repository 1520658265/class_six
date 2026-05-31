# Stat System — Review Log

> 按 `/design-review` skill Phase 5 契约维护；每次审稿追加一条记录在文件末尾。

## Review — 2026-05-31 — Verdict: NEEDS REVISION

Scope signal: L
Specialists: game-designer, systems-designer, qa-lead, godot-specialist, creative-director (synthesis)
Blocking items: 8 | Recommended: 9 | Nice-to-have: 4
Prior verdict resolved: First review（lean mode 自审稿被本次 full mode 独立审稿 supersede）

**关键发现汇总**：

1. **Broadcast delta 语义错误**（systems-designer + qa-lead + game-designer 共识）：原 signal 携带 user-passed delta，在 clamp 边界对 UI 撒谎。creative-director 裁定改成四元组 `(id, old_value, new_value, requested_delta)`，让订阅者可计算 effective_delta = new − old，并在 effective ≠ requested 时识别"半吃掉"做软反馈。
2. **`from_dict` 不 clamp + 不 cast**（systems-designer + godot-specialist）：JSON 解析得到 float、越界值直接落盘，未来 broadcast 全部撒谎。决定改成"自愈式"：load 路径 `clampi + int cast`，触发 push_warning。
3. **autoload 未注册 + gdunit4 未安装**（godot-specialist + qa-lead）：`GlobalState` 在 `project.godot` 没注册；12 个调用点 parse 即报错。`addons/` 是空的。这些 OUT-of-GDD-scope 但 BLOCKS 下游一切——新增 §I Pre-Conditions 列出。
4. **jiejie / caozhengdong headroom 不够**（game-designer，pillar 违背）：jiejie init=8/cap=10 只剩 2 格，"被托住" pillar 承重 NPC 2 次暖意就 saturate。决定升级 AFFINITY 为 per-NPC `{init, min, max}` schema；jiejie.max=15、caozhengdong.min=−15。
5. **隐藏变量上限 premature freeze**：xinjie/qianbao max=20 在终章场景设计前就冻结。决定数值打 PROVISIONAL 标签 + §F.5 加 cross-GDD invariant"下游禁止 hardcode max"。
6. **H.10 round-trip 脆弱**（qa-lead）：`_triggered.keys()` Array 等价比较对插入顺序敏感。决定 `to_dict()` 内部对 keys 做 sort，AC 保持深比 d == d2。
7. **H.11 是 tautology**（qa-lead）：`from_dict` 不走 `change_*`，signal 结构上不可能触发——验证无意义。改为验证自愈 clamp 语义。
8. **H.12 perf 预算无意义**（qa-lead + systems-designer）：16ms 是整个 60fps 帧预算。改为"stat-system 自身 + 1 个 mock subscriber 单帧 < 1ms"。

**Specialist 内部分歧**（creative-director 已裁定）：
- systems-designer 主张 broadcast 仅带 effective delta；game-designer 主张 carry both — creative-director 采用 game-designer。
- game-designer 主张 widen 隐藏变量 max 到 99 + tier gating；creative-director 拒绝过度设计，采用 PROVISIONAL + invariant。
- godot-specialist 主张 autoload load order 内嵌本 GDD；creative-director 移到独立的 §I Pre-Conditions（部署 ADR 责任）。

**作者修订决策**（同会话内拍板，4 个 design-decision 节点）：
- B2 from_dict 越界处理：选 (a) 自愈式 clamp + cast + push_warning
- B5 affinity schema：选 (a) 全量升级 `{init,min,max}`，jiejie.max=15、caozhengdong.min=−15
- B7 H.10 稳定化：选 (a) to_dict 内部 sort
- I1 typo safety：选 (a) 进 v1 — `|delta|>3` push_warning + H.13 unknown ID push_error AC

## Revision — 2026-05-31 — Status: 8 BLOCKING resolved, awaiting re-review

**修订涉及节**：
- 顶部元数据：Status 改为 "Revised (pending re-review)"；Review Mode 改为 full
- §C.4 affinity 表：升级为 per-NPC `{init,min,max}` schema；jiejie.max=15、caozhengdong.min=−15
- §C.6 信号契约：4 元组 payload；新增"为什么是四元组"设计 rationale
- §D.2 affinity_clamp：改为 per-NPC clamp，使用 `AFFINITY_CONFIG[npc_id].min/max`
- §D.3 broadcast 判定：重写边界示例，覆盖正常/底值吞掉/半吃掉/INT 极端值四种场景
- §E.1 边界：新增半吃掉场景说明
- §E.2 未知 ID：affinity 改为对称 push_error 行为（不再"宽容"）
- §E.6 from_dict：改为自愈式（clamp + cast + push_warning）
- §E.7 reset 不广播：补充"load_finished 后 UI 主动 re-read"契约
- §E.8 序列化往返：实现契约新增"to_dict 内部 sort keys"要求
- §E.9 jiejie 顶值：例子从 5 次更新为 8 次（max 升到 15）
- §E.10（新增）：designer typo safety — `|delta|>3` push_warning
- §F.5 cross-GDD invariant：新增 4 条（数值不得 hardcode、load 路径 UI 契约、tone 不得加 juice、新 ID 必须先注册）
- §G Tuning Knobs：affinity init/min/max 全部 per-NPC；xinjie/qianbao max 打 PROVISIONAL；新增 `TYPO_WARN_DELTA` knob
- §H Acceptance Criteria：测试夹具契约新增；H.1/H.4/H.5 改 4 元组 payload；H.2 改"底值完全吞掉"；H.10 重写为显式状态构造；H.11 改自愈 clamp 验证（不再是 tautology）；H.12 改 < 1ms / 含 mock subscriber；新增 H.13 (push_error) / H.14 (半吃掉) / H.15 (typo warning) / H.16 (负 API 表面)；覆盖率自检节同步重写
- §I（新增）Pre-Conditions：autoload 注册、load 顺序冻结、gdunit4 安装、类型化 idiom 修订、follow-up

**修订未涉及（保持不变）**：
- Section A Overview / Section B Player Fantasy / States and Transitions / F.1–F.4 / Visual+Audio / UI / Open Questions（Q2/Q4 部分由 §I 与 §F.5 部分回答，但 OQ 表保留作为 follow-up 提示）
- Implementation file `scripts/autoload/global_state.gd` —— 修订是 GDD-only；落实到代码由 ADR + godot-gdscript-specialist 在 §I.1 / §I.4 处理

**下一步**：
1. （强烈建议）`/clear` 后 `/design-review design/gdd/stat-system.md` 跑 re-review，验证 8 项 BLOCKING 全部 close
2. `/architecture-decision`：写 ADR-XXXX-stat-system-contract（冻结 v1 接口） + ADR-XXXX-autoload-contract（注册 + 加载顺序）
3. `/test-setup`：装 gdunit4 到 `addons/`
4. `/design-system asset-loading`：继续设计顺序 #2

## Review — 2026-05-31 — Verdict: NEEDS REVISION (Round-2)

Scope signal: L
Specialists: qa-lead, godot-specialist, game-designer, systems-designer, creative-director (synthesis)
Blocking items: 16 | Recommended: 11 | Nice-to-have: 4
Prior verdict resolved: Yes — Round-1 8 项 BLOCKING 全部确认 close（4 元组 payload / per-NPC affinity schema / PROVISIONAL invariant / 自愈 from_dict / to_dict sort + AC 夹具契约）

**Round-2 关键发现汇总**（按 specialist 分类）：

1. **qa-lead（5 BLOCKING）**：H.12 < 1ms / 100 调用在 gdunit4 headless 下不可靠（GC pause 抖动 false-fail）；H.11 没覆盖 §E.6 的 unknown stat / unknown npc / chapter 越界三个 case；测试夹具契约对"断开 6 个信号现存连接"语义模糊（`disconnect_all()` 不存在）；H.10 没显式 assert sort 实际生效（只测 d == d2 在插入序碰巧匹配时 false-pass）；H.3 reset 静默 AC 没要求 verify 全部 6 个集合都回到 init。
2. **systems-designer（3 BLOCKING）**：D.1 / D.2 `current + delta` 可在 clamp 之前 INT64 溢出（INT64_MAX wrap → 负数 → clamp 到 0，违反硬保证）；E.10 `abs(INT64_MIN)` 在二补码下溢出回 INT64_MIN，最极端 typo 反而绕过警告；D.3 Example D 用 INT32 边界 `-2147483648` 说明 64-bit 系统，暴露作者心智模型差 32 bit。
3. **godot-specialist（8 BLOCKING）**：8 项实装契约漂移——`global_state.gd` 当前与 GDD §C.6 4 元组 / §C.4 per-NPC AFFINITY_CONFIG / §D.1 clampi / §E.6 自愈 from_dict / §E.8 to_dict sort / §C.6 _emit_depth 守卫均不一致；同时 godot-specialist 提出"Dictionary[String, int] 不存在"与"autoload 按字母序"两条结构性疑问，**经 Web/Context7 官方文档复核两条均为误判**：typed Dictionary 在 4.4+ 支持（4.6 可用），autoload 按 project.godot 声明顺序（top-to-bottom）初始化。两条复核已分别归档于 §I.4 第 2 项与 §I.2"官方文档复核"段。
4. **game-designer（2 BLOCKING + 5 RECOMMENDED）**：质疑 4 元组 payload 是否服务 acknowledgment fantasy（creative-director 裁定保留：fantasy 由 §F.5 "no juice" 在 UI 层守住，不靠数据层藏信息）；质疑 PROVISIONAL 标记是否阻塞下游（creative-director 裁定保留：通过 `VARS_CONFIG[id].max` 动态读是标准 data-driven，比提前冻结错的 max 更稳）。其余 5 项 RECOMMENDED 部分纳入修订（R-G3 affinity-changing event_id idempotent invariant）。
5. **creative-director synthesis**：14 项 BLOCKING 真改 GDD（除 godot-specialist 两条已复核为误判的不入），4 项 R 项纳入（R-S4 再入保护 / R-S6 启动 config 校验 / R-K1 CONNECT_DEFERRED invariant / R-G3 event_id idempotent invariant）。

**作者修订决策**（同会话内拍板，4 个 design-decision 节点）：
- H.12 perf 预算：选 < 5ms + headless release + 重复 3 次取最差
- TYPO_WARN_DELTA：选 5（避开 demo lookup 表上限 ±3 重合）
- chapter_changed：选 2 参 (old, new) 与其他信号对称
- R 项纳入：4 项全收（R-S4 / R-S6 / R-K1 / R-G3）

## Revision — 2026-05-31 — Status: 16 BLOCKING resolved (Round-2 GDD-only)

**修订涉及节**（按 GDD 自上而下顺序）：
- 顶部元数据：Status 改为 "Revised v2 (pending lean re-review)"；Review Mode 改 full × 2；Creative Director Review 标 Round-2 完成
- §C.6 信号契约：`chapter_changed` 改 2 参 `(old_chapter, new_chapter)`；新增"再入保护契约"段（`_emit_depth` 守卫 + 订阅侧 CONNECT_DEFERRED）；广播规则同步更新 chapter_changed 条目
- §D.1 / §D.2：在公式节追加"实装契约（溢出安全）"——`safe_delta = clampi(delta, min-max, max-min)` 预收敛，避免 INT64 wrap；同步 D.2 affinity 公式
- §D.3 Example D：从 INT32_MIN（-2147483648）改为 INT64_MIN（-9223372036854775808），并说明 effective_delta = -3、requested 字段保留原值
- §E.3：再入禁止段从"调用方负担"升级为双侧契约（实装侧 push_error + 订阅侧 CONNECT_DEFERRED），同帧多次广播示例改 4 元组
- §E.8：新增"`_triggered` / `_era_markers` Set-as-Dict 语义"段；新增"`from_dict` 异常容错"段（dict-as-array / falsy value / 错类型三种 case）
- §E.9：jiejie 顶值场景的 push_warning 行为按 §E.10 effective=0 静默契约更新
- §E.10：阈值 3 → 5；`|delta| > T` 改成符号比较 `delta > T or delta < -T`（避免 `abs(INT64_MIN)` 溢出）；effective_delta = 0 时不发 warning（与广播规则对齐）
- §F.5 cross-GDD invariant：从 5 条扩到 7 条（新增"启动 config 校验" R-S6、"订阅者 CONNECT_DEFERRED 推荐" R-K1、"affinity-changing event_id 默认 idempotent" R-G3）+ 1 条 enforcement 兜底说明
- §G Tuning Knobs：TYPO_WARN_DELTA 默认 3 → 5，Safe Range 同步说明
- §H 测试夹具契约：从 3 条扩到 5 条（含 mock subscriber 模板代码 + error/warning capture 说明 + idle frame 负断言模式）
- §H.3 reset 静默：pre-state 从"≥1 个"改成显式 2 个 stat / 2 var / 2 affinity / 2 triggered / 2 era_markers / 1 chapter；THEN 验证全部 6 集合回到 init + await 2 idle frames + 6 mock 全部 _call_count=0
- §H.9 set_chapter 广播：payload 改 `(old="prologue", new="ch1")`；新增同章节 set 静默 sub-case
- §H.10 round-trip：显式断言 `d["triggered"] == ["ev1", "ev2"]`、`d["era_markers"] == ["kaixue", "shenzhou7"]`；新增 d3 == d 字面级稳定 sub-case
- §H.11 自愈 clamp：覆盖 6 字段（包含浮点 9999.0 cast 用例）；assert_warning_count==6；await 2 idle frames 后 3 路 mock _call_count=0
- §H.12 perf：< 1ms → < 5ms；锁定 `--headless --release`；重复 3 次取最差；外/内层循环明确写出
- §H.15 typo_warning：从 1 case 扩到 5 case（A/B 阈值 / C 半吃掉仍报 / D effective=0 静默 / E INT64_MIN 不绕过）
- §H.17（新增）：from_dict unknown stat / var / npc 跳过 + 3 次 push_warning
- §H.18（新增）：from_dict chapter "ch99" 越界写入 + push_warning + 信号不广播
- §H.19（新增）：`_validate_configs` 启动 config 校验（init < min / init > max / min > max 三组 + 合法 config 共 4 case）
- §H.20（新增）：同帧连续 3 次 change_stat("danliang", +1) 验证 mock _call_count=3 + 3 次 payload 顺序正确
- 覆盖率自检节：同步更新到 H.20，新增"§F.5 invariant 覆盖"行
- §H 节末"预实现前提"：从 16 → 20 AC；补充实装漂移项；review 历史扩为 Round-1 / Round-2 两段
- §I.2 autoload 加载顺序：保留原契约不变（按 project.godot 声明顺序），追加"官方文档复核"段记录 godot-specialist 字母序误判已 archived
- §I.3 gdunit4：AC 数量 16 → 20
- §I.4 typed Dictionary / clampi：从 4 条扩为 8 + 1 项的实装漂移列表（含信号 4 元组、AFFINITY_CONFIG schema、from_dict 自愈、to_dict sort、_emit_depth、_validate_configs），明确"必须与 §I.1 同 ADR 处理"
- §I.5 总结：新增 Round-2 评审复核备忘段，archive typed Dictionary + autoload 顺序两条 godot-specialist 误判

**修订未涉及（保持不变）**：
- Section A Overview / Section B Player Fantasy（creative-director 复核：4 元组与 PROVISIONAL 不违背 fantasy）
- §C.1 / §C.2 / §C.3 / §C.4 / §C.5 数据集合与表（schema 已在 Round-1 v1 冻结）
- States and Transitions（chapter state machine 表不变；但 `chapter_changed` 信号 payload 已在 §C.6 / §H.9 同步）
- §D.4 lookup table（数值不变；TYPO 阈值改 5 后仍兼容）
- F.1–F.4（依赖图与上下游列表不变）
- Visual + Audio / UI Requirements（未触及）
- Open Questions（Q2 由 §F.5 启动 config 校验局部回答；其余仍 follow-up）
- 实装文件 `scripts/autoload/global_state.gd`：本轮仍是 GDD-only 修订；落实到代码由 ADR + godot-gdscript-specialist 在 §I.1 / §I.4（合并 8+1 项）处理

**下一步**：
1. ~~lean re-review~~ ✅ APPROVED (2026-05-31)
2. `/architecture-decision`：写 ADR-XXXX-stat-system-contract（冻结 v1 接口 + 实装侧 8+1 项契约） + ADR-XXXX-autoload-contract（注册 + 加载顺序按 project.godot 声明序）
3. `/test-setup`：装 gdunit4 到 `addons/`，建 `tests/unit/stat_system/` 骨架
4. `/design-system asset-loading`：继续 retrofit 设计顺序 #2

## Review — 2026-05-31 — Verdict: APPROVED (Lean Re-review)

Scope signal: L
Specialists: 无（lean mode，单会话分析）
Blocking items: 0 | Recommended: 0
Prior verdict resolved: Yes — Round-2 16 项 BLOCKING 全部确认 close

**验证摘要**：

本次 lean re-review 逐项核对 Round-2 的 16 项 BLOCKING：
- qa-lead 5 项（H.12 改 <5ms / H.11 扩覆盖+H.17/H.18 / 夹具契约 5 条含 mock 模板 / H.10 显式 sort 断言 / H.3 全集合校验）— 全部在 GDD 文本中落实 ✓
- systems-designer 3 项（D.1/D.2 safe_delta 溢出保护 / E.10 符号比较替代 abs / D.3 改 INT64_MIN）— 全部落实 ✓
- godot-specialist 8 项（6 项实装漂移归入 §I.4 由 ADR 处理 / 2 项误判已归档官方文档复核）— 全部落实 ✓
- game-designer 2 项（creative-director 裁定保留 4 元组 + PROVISIONAL，§F.5 守住）— 全部落实 ✓
- 4 项 R-item（R-S4 / R-S6 / R-K1 / R-G3）纳入 §C.6 / §F.5 / §H.19 ✓

**结论**：设计内部一致、数学健全（含 INT64 溢出保护）、接口精确可实现。§F.5 跨 GDD invariant 为下游一致性提供稳固框架。无新阻塞项。

**下一步**：
1. `/architecture-decision` 写 ADR-XXXX-stat-system-contract + ADR-XXXX-autoload-contract
2. `/test-setup` 装 gdunit4
3. `/design-system asset-loading` 继续设计顺序 #2
