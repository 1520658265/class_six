# 属性 + 隐藏变量定义表（Demo 范围）

> 创建日期：2026-05-30
> 范围：序章 + 第一章 demo 切片所需的变量定义。后续章节扩展时新增项加在对应表末尾，不重排序。
> 关联：[化名映射表](../../tools/private/化名映射表.md)（私有）、[元生六年级故事线](../reference/元生六年级故事线.md)

## 一、显性属性（4 项，UI 可见）

显性属性出现在属性面板上。每项整数，初值 1，上限 10，下限 0。变化时 GlobalState 发出 `stat_changed(name, delta, new_value)` 信号，属性面板订阅刷新并播放 +/- 飘字。

| ID | 名称 | 初值 | 上下限 | 含义 |
|---|---|---|---|---|
| `xuexi` | 学习 | 3 | 0–10 | 课业能力，影响月考排名飘字、解锁部分对白选项 |
| `danliang` | 胆量 | 1 | 0–10 | 面对冲突时的承受度，影响曹正东遭遇的可选项 |
| `koucai` | 口才 | 1 | 0–10 | 表达能力，影响主动搭话相关选项 |
| `tili` | 体力 | 3 | 0–10 | 体能，demo 范围内不影响选项（埋点供后续章节使用）|

### Demo 范围内的变更来源

| 事件 | 触发位置 | 变更 |
|---|---|---|
| 序章班会"你叫元生？" 主动报全名 | 序章 · 二班教室 | 口才 +1 |
| 序章宿舍主动跟王炎说话 | 序章 · 男生宿舍 | 口才 +1 |
| 第一章 1.1 蒸饭盒事件得到王炎帮助后说"谢谢" | 第一章 · 食堂蒸饭间 | 口才 +1 |
| 第一章 1.2 月考排名宣布（元生在二班中游） | 第一章 · 走廊 | 学习 +1（事件固定增量）|
| 第一章 1.3 小卖部 选项 C "买 2 毛跳跳糖" | 第一章 · 小卖部 | 口才 +1 |
| 第一章 1.4 曹正东抢钱 选项 A "不吭声" | 第一章 · 楼梯口 | 胆量 -1 |
| 第一章 1.4 曹正东抢钱 选项 B "喊老师" | 第一章 · 楼梯口 | 胆量 +1 |
| 第一章 1.4 曹正东抢钱 选项 C "推回去"（需 胆量 ≥ 3）| 第一章 · 楼梯口 | 胆量 +2（隐藏路线）|

## 二、隐性变量（3 项，UI 不可见）

隐性变量不出现在属性面板上，但参与对白条件判定。整数，可正可负，每项初值 0。变化时 GlobalState 发出 `var_changed(name, delta, new_value)`。

| ID | 名称 | 初值 | 上下限 | 含义 |
|---|---|---|---|---|
| `xinjie` | 心结 | 0 | 0–20 | 元生作为"卡过渡届最后一届"的整体心理压力，多次累积后影响对白基调 |
| `kaguodu_xinli` | 卡过渡届心理度 | 0 | 0–10 | 对"丁埠最后一届六年级"身份的明确感知，序章走廊埋点初始化 +1 |
| `qianbao_xiuchi` | 钱包羞耻度 | 0 | 0–20 | 路过/进入小卖部时摸口袋的羞耻感累积 |

### Demo 范围内的变更来源

| 事件 | 变更 |
|---|---|
| 序章走廊听见老师说"明年六年级都到中心小学" | 卡过渡届心理度 +1 |
| 序章首次路过小卖部，王炎买辣条而元生没进去 | 钱包羞耻度 +1 |
| 第一章 1.2 月考排名走廊看胡晓东他们围着排名笑闹后转身离开 | 心结 +1 |
| 第一章 1.3 小卖部 选项 A "摇头说不要" | 钱包羞耻度 +1 |
| 第一章 1.3 小卖部 选项 B "赊账 5 毛辣条" | 心结 +1 |
| 第一章 1.4 曹正东抢钱后，回宿舍躺下 | 钱包羞耻度 +2 / 心结 +2 |

## 三、NPC 好感度

每个出场 NPC 一个独立整数变量，命名 `affinity_<asset_id>`，初值 0，范围 -10 到 +10。NPC 数据表会列出每个 NPC 的初始值与触发条件。Demo 范围内出现：

| 变量 | 初值 |
|---|---|
| `affinity_baoxianjin` | 0 |
| `affinity_baosimu` | 1 |
| `affinity_wangyan` | 1 |
| `affinity_zengjianming` | 1 |
| `affinity_caozhengdong` | -3 |
| `affinity_huxiaodong` | 0 |
| `affinity_zhanglei` | 0 |
| `affinity_lijing` | 0 |
| `affinity_menwei_daye` | 0 |
| `affinity_fuqin` | 5 |
| `affinity_muqin` | 5 |
| `affinity_jiejie` | 8 |

具体增量见 [NPC 数据表](npc-data-spec.md)（task #8 产出）。

## 四、章节进度与已触发事件

| 变量 | 类型 | 含义 |
|---|---|---|
| `current_chapter` | String | 当前章节 ID（`prologue` / `ch1` / `ch1_done`）|
| `triggered_events` | Array[String] | 已触发的关键事件 ID 列表，避免重复触发 |
| `era_markers` | Array[String] | 已点亮的时代切片标记（demo 范围内有 `kaixue` / `shenzhou7` / `sanlu`）|

`triggered_events` 在 demo 范围内的事件 ID 命名约定：

```
prologue/01_father_send_off
prologue/02_classroom_arrival
prologue/03_corridor_overhear
prologue/04_xiaomaibu_first_pass
prologue/05_dorm_assigned
ch1/11_zhengfanhe_help
ch1/12_yuekao_ranking
ch1/13_xiaomaibu_first_buy
ch1/14_caozhengdong_robbery
ch1/15_shenzhou7_evening
ch1/16_sanlu_classmeeting
```

## 五、GlobalState API 形状（任务 #13 实现参考）

```gdscript
# scripts/autoload/global_state.gd
extends Node

signal stat_changed(stat_id: String, delta: int, new_value: int)
signal var_changed(var_id: String, delta: int, new_value: int)
signal affinity_changed(npc_id: String, delta: int, new_value: int)
signal event_triggered(event_id: String)
signal chapter_changed(new_chapter: String)

# 4 stats / 3 hidden vars / N affinities / chapter / triggered_events / era_markers

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

func set_chapter(chapter_id: String) -> void

# 序列化
func to_dict() -> Dictionary
func from_dict(data: Dictionary) -> void
func reset_to_initial() -> void
```

存档系统（task #15）调用 `to_dict()` / `from_dict()` 完整序列化全部状态。

## 六、范围排除

以下变量在 demo 不实现，留作后续章节预留位：

- 物品库存（饭盒、姐姐的信、化肥袋、玻璃罐）— 道具表 [items-spec.md](items-spec.md) 定义，但 demo 内不开放使用，仅作为剧情触发标记
- 战斗相关属性（HP / 勇气槽）— demo 不含战斗
- 时间系统（一周内的"周一-周五"循环）— 序章/第一章用线性事件流，不引入时间钟
