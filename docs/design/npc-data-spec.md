# NPC 数据表（Demo 范围）

> 创建日期：2026-05-30
> 范围：序章 + 第一章 demo 出场全部 NPC。每个 NPC 列：化名 / 资产 ID / 初始好感 / 出场场景 / 触发条件 / 互动行为。
> 关联：[化名映射表（私有）](../../tools/private/化名映射表.md)、[属性变量定义-spec.md](属性变量定义-spec.md)、[元生六年级故事线](../reference/元生六年级故事线.md)

## 一、表头说明

| 字段 | 含义 |
|---|---|
| 化名 | 游戏内显示名 |
| 资产 ID | 资源 ID（snake_case，walksheet 文件名、portrait 文件名、affinity 变量名都用它）|
| 初始好感 | `affinity_<asset_id>` 初值，与 [属性变量定义-spec.md](属性变量定义-spec.md) §三 一致 |
| 出场场景 | demo 中首次出现的场景 ID |
| 持续场景 | demo 中常驻或多场出现的场景 ID 列表 |
| 触发条件 | 主动靠近 + interact 键 / 自动 cutscene / 走廊路过事件 |
| 是否可对话 | demo 内是否对玩家开放 interact 互动 |

## 二、Demo NPC 主表

| 化名 | 资产 ID | 初始好感 | 出场场景 | 持续场景 | 触发条件 | 可对话 |
|---|---|---|---|---|---|---|
| 父亲 | `fuqin` | 5 | `home` | `mountain_road_autumn` | 序章开场自动 cutscene（送行）| 是（仅序章首日）|
| 母亲 | `muqin` | 5 | `home` | `home` | 序章开场自动 cutscene（收拾行李）| 是（仅序章首日）|
| 鲍先进 | `baoxianjin` | 0 | `classroom_2b` | `classroom_2b` / `corridor_stairs` | 序章班会自动 cutscene；第一章 1.2 月考 cutscene | 是 |
| 鲍师母 | `baosimu` | 1 | `xiaomaibu` | `xiaomaibu` | 序章首次进店自动；第一章 1.3 选项触发 | 是 |
| 王炎 | `wangyan` | 1 | `classroom_2b` | `classroom_2b` / `dorm` / `xiaomaibu` / `cafeteria_steam` | 序章宿舍分铺；第一章 1.1 / 1.3 / 1.5 自动；空闲时可对话 | 是 |
| 曾建明 | `zengjianming` | 1 | `classroom_2b` | `classroom_2b` / `dorm` / `corridor_stairs` | 序章班会自动；第一章 1.2 走廊路过 cutscene；空闲时可对话 | 是 |
| 曹正东 | `caozhengdong` | -3 | `dorm` | `dorm` / `corridor_stairs` | 序章宿舍分铺自动；第一章 1.4 楼梯口拦截 cutscene | 否（demo 内只走 cutscene）|
| 胡晓东 | `huxiaodong` | 0 | `corridor_stairs` | `corridor_stairs` | 序章走廊远景路过；第一章 1.2 走廊围着排名表 | 否（demo 内只远景）|
| 张磊 | `zhanglei` | 0 | `corridor_stairs` | `corridor_stairs` | 同 `huxiaodong`，作为一班群像 | 否 |
| 李静 | `lijing` | 0 | `corridor_stairs` | `corridor_stairs` | 同 `huxiaodong`，作为一班群像 | 否 |
| 门卫大爷 | `menwei_daye` | 0 | `school_gate` | `school_gate` | 第一章 1.6 三鹿事件晚自习后路过校门自动 cutscene | 是 |
| 姐姐 | `jiejie` | 8 | （仅信件）| — | 序章 home 桌上信件触发；空闲时宿舍存档点重读 | 否（仅文本，不出现立绘走动）|

## 三、群众同学（demo 范围）

需要 3-5 个换色板的"群众"NPC，仅作为教室/走廊背景密度，不参与对话。

| 资产 ID | 用途 |
|---|---|
| `npc_classmate_a` | 二班教室前排女生 |
| `npc_classmate_b` | 二班教室后排男生 |
| `npc_classmate_c` | 一楼走廊路过 |
| `npc_classmate_d` | 食堂蒸饭间排队 |
| `npc_classmate_e` | 宿舍楼道 |

群众 NPC 复用现有同学/混混 walk 资源换色（task #14 处理时再决定具体换色方案）。Demo 内不互动，靠近也不弹提示。

## 四、好感度变化触发清单（demo 范围）

| 事件 | 影响 NPC | 变更 |
|---|---|---|
| 序章 home 主动跟母亲说"我会自己回来" | `muqin` | +1 |
| 序章山路对父亲说"周五我自己走" | `fuqin` | +1 |
| 序章宿舍主动跟王炎打招呼 | `wangyan` | +1 |
| 序章班会专心听鲍先进讲话（不分心选项）| `baoxianjin` | +1 |
| 第一章 1.1 蒸饭盒事件接受王炎帮助后说谢谢 | `wangyan` | +1 |
| 第一章 1.3 选项 C "买 2 毛跳跳糖" | `baosimu` | +1 |
| 第一章 1.3 选项 B "赊账 5 毛辣条" | `baosimu` | -0（中性，但触发"心结"+1）|
| 第一章 1.4 选项 A "不吭声" | `caozhengdong` | -1（认定你软）|
| 第一章 1.4 选项 B "喊老师" | `baoxianjin` | +1 / `caozhengdong` | -2（更敌对）|
| 第一章 1.5 神舟七号曾建明回头说话后元生回应 | `zengjianming` | +1 |
| 第一章 1.6 三鹿事件门卫大爷讲话后元生留下来听完 | `menwei_daye` | +1 |
| 支线 · 曾建明的橡皮 · 元生说"谢谢" | `zengjianming` | +1 |

## 五、Demo 内 NPC 行为（基类需要支持的能力）

按 [task #26] NPC 基类需要支持的能力分类：

- **静态站桩 NPC**：母亲（在家中桌边）、鲍师母（小卖部柜台后）、门卫大爷（校门口）— 不动，仅 idle 帧（可用 walk_down 0 帧）
- **可触发 cutscene 的 NPC**：父亲（送行 cutscene 中走动）、鲍先进（班会 cutscene、月考宣讲 cutscene）、曾建明（走廊路过 cutscene）、曹正东（楼梯口拦截 cutscene）— 平时静止 idle，cutscene 中由 CutsceneRunner 接管移动
- **跟随主角的 NPC**：王炎（蒸饭盒、小卖部段落跟随）— Demo 内简化为"瞬移到附近坐标"，不做寻路
- **远景群像 NPC**：胡晓东 / 张磊 / 李静 / 群众同学 — 静止站桩，仅靠近时弹"看一眼"飘字（不打开对话框）

## 六、范围排除

- 第二章及以后引入的 NPC（伊利酸奶事件、长江七号、悠悠球同学等）
- 战斗 NPC 数据（HP / 技能） — demo 不含战斗
- NPC 寻路（NavigationAgent2D）— Demo 用脚本路径点
- NPC 日程系统（不同时段不同位置）— Demo 用线性事件流
