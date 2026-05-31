# 对白脚本 JSON 格式说明

> 所有 demo 对白脚本统一格式。对话系统（task #9）按本文档解析，cutscene runner（task #12）调用对话系统播放。

## 一、文件组织

```
data/dialogue/
├── prologue.json        # 序章
├── chapter1.json        # 第一章
└── _format.md           # 本文件
```

每个文件是一个 JSON 对象，顶层 `lines` 是字典：`line_id → line_object`。脚本不假设 line 顺序，靠 `next` 字段串联。

## 二、Line 对象 schema

```jsonc
{
  "id": "ch1/12_yuekao/01",          // 唯一 ID，按 'chapter/event_id/序号' 命名
  "speaker": "鲍先进",                // 说话人化名（与化名映射表一致）；旁白用 ""
  "speaker_id": "baoxianjin",         // 说话人 asset_id，对应 Portraits 中的 character_id
  "expression": "angry",              // 立绘表情 key（PortraitSet.expressions），缺省 "neutral"
  "text": "二班的，名次都念给我听好了。",  // 正文（普通话）
  "next": "ch1/12_yuekao/02",         // 下一条 line ID。null 表示对话块结束
  "choices": [                        // 可选；存在时 next 字段被忽略
    {
      "label": "走过去看",
      "next": "ch1/12_yuekao/03_close",
      "preconditions": {              // 可选；不满足则该选项不可见
        "stat": {"danliang": {"min": 2}},
        "var": {"xinjie": {"max": 5}},
        "affinity": {"baoxianjin": {"min": 0}},
        "triggered": ["prologue/02_classroom_arrival"],  // 必须已触发
        "not_triggered": ["ch1/12_yuekao/closed"]        // 必须未触发
      },
      "postconditions": {             // 可选；选中后立刻执行的副作用
        "stat": {"danliang": 1},      // delta
        "var": {"xinjie": 1},
        "affinity": {"baoxianjin": -1},
        "trigger": ["ch1/12_yuekao/closed"],
        "era_marker": ["shenzhou7"],
        "set_chapter": "ch1_done",
        "give_item": ["lvfanhe"]      // 占位；demo 内不实现背包
      }
    }
  ],
  "preconditions": {  /* 同 choices.preconditions，整条 line 是否可达 */ },
  "postconditions": { /* 进入此 line 时立刻执行（在 text 显示之前）*/ }
}
```

### 字段约定

- `id`：一律 ASCII，按 `<chapter>/<event_id>/<序号>` 形式（`event_id` 与 [事件流程图](../docs/design/event-flow-prologue-ch1.md) 一致）。
- `speaker` / `speaker_id`：旁白时两者都填空字符串，对话框显示无姓名条样式。
- `expression`：必须是 PortraitSet 已有的 key；缺省 `neutral`。
- `next`：line 结束后跳转的 line ID。`null` 表示当前对话块结束（关闭对话框，控制权回到玩家）。
- `choices`：选项列表。每个选项有自己的 `label`、`next`、`preconditions`、`postconditions`。如果 `choices` 存在，line 自身的 `next` 字段会被忽略。
- `preconditions` / `postconditions`：所有可用条件类型见下表。

## 三、preconditions / postconditions 完整字段

| 字段 | precondition 含义 | postcondition 含义 |
|---|---|---|
| `stat` | `{stat_id: {"min": int, "max": int}}` 范围检查 | `{stat_id: int}` delta 增减 |
| `var` | 同上 | 同上 |
| `affinity` | 同上 | 同上 |
| `triggered` | `[event_id...]` 全部已触发才通过 | `[event_id...]` 全部标记触发 |
| `not_triggered` | `[event_id...]` 全部未触发才通过 | — |
| `era_marker` | `[marker_id...]` 全部已点亮才通过 | `[marker_id...]` 全部点亮 |
| `chapter` | `[chapter_id...]` 当前章节是其中之一 | — |
| `set_chapter` | — | 字符串，立刻切章节 |
| `trigger` | — | `[event_id...]` 触发标记（同 triggered 但是 post 用）|
| `give_item` | — | `[item_id...]` 占位字段，demo 内仅写 log |

## 四、对话播放流程（task #9 实现参考）

1. CutsceneRunner 或互动 NPC 调用 `Dialogue.play(start_line_id)`
2. 对话系统读 `data/dialogue/<chapter_id>.json`（缓存）
3. 跳到 `start_line_id`：
   1. 检查 `preconditions`，不满足则报错
   2. 执行 `postconditions`（前置副作用）
   3. 显示立绘 + 姓名条 + 文本（打字机效果）
   4. 若有 `choices`：等玩家选 → 检查选项 preconditions（不满足则该项变灰）→ 执行选项 postconditions → 跳到 `next`
   5. 若无 `choices`：等玩家按 interact/Z 推进 → 跳到 `next`
   6. 若 `next` 为 `null`：关闭对话框，发出信号 `dialogue_finished(start_line_id)`

## 五、特殊约定

- 旁白行：`speaker` 与 `speaker_id` 都为 `""`，对话框显示无头像、无姓名条样式（仅居中文本，灰色背景半透明）
- 内心独白：`speaker` 为 `"元生（内心）"`，`speaker_id` 为 `"yuansheng"`，`expression` 用 `"thoughtful"` 等内向表情
- 选项后会跳到不同分支再合流：约定一个 `<event_id>/end` line 作合流点，所有分支 `next` 指到它
- 一段对话块跨 cutscene 段：在 line 的 `postconditions` 里加 `trigger: [event_id]` 让 CutsceneRunner 监听后续动作

## 六、严格性

- 任何字段拼错（如 `stat` 写成 `state`）解析时抛错并打印 line ID
- 引用不存在的 stat/var/affinity ID 抛错
- 引用不存在的 next line ID 抛错
- 缺失 expression 时回退到 `neutral` 不抛错
