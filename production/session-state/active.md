# Session State

**Task**: stat-system GDD — design-review 修订完成，等待 **re-review**
**Status**: Revised (8 BLOCKING items addressed, awaiting independent re-review)
**File**: design/gdd/stat-system.md
**Last Updated**: 2026-05-31

## 立刻在新会话里跑

```
/design-review design/gdd/stat-system.md
```

会再跑 4 个 specialist 平行审稿 + creative-director 综合，验证 8 项 BLOCKING 是否全部 close。

## 本次 session 干了什么（2026-05-31 design-review）

1. **跑了 full mode design-review**：4 个 specialist（game-designer / systems-designer / qa-lead / godot-specialist）平行审稿 + creative-director 综合 → Verdict: NEEDS REVISION（8 项 BLOCKING + 9 项 Recommended + 4 项 Nice-to-have）
2. **同会话内修订**了 stat-system.md 的 8 项 BLOCKING + 多项 IMPORTANT
3. **写入文件**：
   - `design/gdd/stat-system.md` — 大量节修订，详见 review log
   - `design/gdd/reviews/stat-system-review-log.md` — 新建，含审稿条目 + 修订条目
   - `design/gdd/systems-index.md` — stat-system 状态 `Designed → In Review (revised)`；下一步指引重写

## 8 项 BLOCKING 修订定位

| # | 原 BLOCKING | 修订位置 |
|---|---|---|
| 1 | broadcast delta 在 clamp 边界撒谎 | §C.6 + §D.3 + H.1/H.4/H.5/H.14 — signal 改 4 元组 `(id, old, new, requested)` |
| 2 | from_dict 不 clamp + 不 cast | §E.6 + §H.11 — 自愈式 clamp + int cast + push_warning |
| 3 | autoload 未注册 + 加载顺序未冻结 | 新增 §I.1 / §I.2 — 列入 ADR（待 `/architecture-decision`） |
| 4 | jiejie headroom 不够 | §C.4 + §D.2 + §G — per-NPC `{init,min,max}` schema；jiejie.max=15 / caozhengdong.min=−15 |
| 5 | 隐藏变量 max premature freeze | §G + §F.5 — xinjie/qianbao max 打 PROVISIONAL；invariant 禁止 hardcode |
| 6 | H.12 perf 预算无意义 | §H — 改 < 1ms / 含 mock subscriber |
| 7 | H.10 round-trip 脆弱 | §E.8 + §H.10 — to_dict 内部 sort keys |
| 8 | H.11 是 tautology | §H.11 — 改为验证自愈 clamp 语义 |

## 同会话 4 个设计决策（design-decision pinned）

- **B2 from_dict 越界处理** = (a) **自愈式**：clamp + cast + push_warning
- **B5 affinity schema** = (a) **全量升级 `{init,min,max}`**：jiejie.max=15、caozhengdong.min=−15
- **B7 H.10 稳定化** = (a) **to_dict 内部 sort**
- **I1 typo safety** = (a) **进 v1**：`|delta|>3` push_warning + H.13 unknown ID push_error AC

这 4 项 re-review 时如果 specialist 提出不同方案，需要重新评估。

## 实现层未触碰

`scripts/autoload/global_state.gd` 保留原状（GDD-only 修订）。落实到代码由后续 ADR + godot-gdscript-specialist 处理（参见 stat-system §I.1 / §I.4）。

## Re-review 后的预期下一步

1. 验证 NEEDS REVISION 的 8 项 BLOCKING 全部 close → Verdict: APPROVED 或剩余 minor revisions
2. APPROVED 后：
   - `/architecture-decision` 写 **ADR-XXXX-stat-system-contract**（冻结 v1 接口）
   - `/architecture-decision` 写 **ADR-XXXX-autoload-contract**（注册 + 加载顺序，§I.1 / §I.2）
   - `/test-setup` 装 gdunit4 到 `addons/`（§I.3）
   - `/design-system asset-loading` 继续 retrofit 顺序 #2

## High-Risk Items（仍生效）

- Character Controller 横版改造（影响 5 个下游系统）— Order #6
- Stat System 接口冻结 — **GDD 已交付 v1+revised；等 re-review 通过 → ADR 冻结**
- Combat 4 子系统耦合（Order #16–19，必须按顺序设计）

## Open Questions（GDD §Open Questions 仍有效）

Q1 原子事务 / Q2 chapter 白名单（部分被 §C.5 + §E.5 + §I 回答）/ Q3 schema 版本 / Q4 配置外置（§I.5 follow-up）/ Q5 lookup table 存放 / Q6 ADR 时机
