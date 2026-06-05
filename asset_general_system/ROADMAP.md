# AI RPG 资产生成系统阶段规划

更新时间：2026-06-05

## 1. 总体路线

系统按“地图闭环优先，资产能力逐步扩展”的方式建设。

推荐主线：

```text
阶段 0：协议和工程骨架
阶段 1：文本生成 RPG tilemap MVP
阶段 2：地图校验、预览和 Tiled JSON 稳定导出
阶段 3：编辑器和局部重生成
阶段 4：地图元素生成和素材库
阶段 5：角色 sprite sheet 生成
阶段 6：特效动画帧生成
阶段 7：Godot / Unity / Phaser 深度导出
```

## 2. 阶段 0：协议和工程骨架

目标：定义系统基础协议和项目结构，让后续模块可以并行开发。

周期建议：1-2 周。

交付物：

- `RPGMapSpec` 初版 JSON schema。
- `AssetMetadata` 初版 JSON schema。
- `SpriteSheetMetadata` 初版 JSON schema。
- 示例 prompt 和示例 spec。
- 项目目录结构。
- 第一版技术架构文档。

验收标准：

- 可以用 schema 校验一份地图规格。
- 至少有 5 条典型 prompt 样例。
- 每条 prompt 都能手工对应到一份 `RPGMapSpec`。
- 明确第一版 tileset、tile 尺寸、地图尺寸、导出格式。

主要风险：

- 协议过早绑定某个引擎。
- 地图 spec 过于自由，导致生成器难以实现。
- spec 缺少碰撞、事件、导航等游戏逻辑信息。

## 3. 阶段 1：文本生成 RPG Tilemap MVP

目标：跑通 `Prompt -> RPGMapSpec -> Tilemap`。

周期建议：3-4 周。

能力范围：

- 支持 2D top-down orthogonal tilemap。
- 支持固定 32x32 tile。
- 支持 64x64 地图。
- 支持固定 tileset。
- 支持森林、村庄、地牢 3 类主题。
- 支持地形层、道路层、装饰层、碰撞层、事件层。

核心模块：

- Prompt parser：自然语言到 `RPGMapSpec`。
- Map generator：根据 spec 生成多层 tilemap。
- Rule validator：检查基础合法性。
- Preview renderer：生成 PNG 预览。

验收标准：

- 输入一段描述后可以生成地图。
- 地图包含至少 3 个结构区域，例如河流、村庄、森林。
- 出生点可行走。
- 关键区域之间有道路或可达路径。
- 生成结果稳定记录 prompt、spec、seed。

建议样例：

```text
生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙。
```

```text
生成一个小型地下城，入口在左下角，中心有大厅，右上角有 boss 房间。
```

```text
生成一个雪地营地，四周是松树，中间有篝火和三间木屋。
```

## 4. 阶段 2：校验、预览和 Tiled JSON 导出

目标：让地图从“能生成”变成“能进工具链”。

周期建议：3-4 周。

能力范围：

- 稳定导出 Tiled JSON。
- 输出 PNG 预览图。
- 输出地图生成报告。
- 输出校验错误报告。
- 支持碰撞层和事件层。

校验项：

- 出生点可行走。
- 关键区域可达。
- 建筑入口无遮挡。
- NPC 和对象放置合法。
- 交互对象旁边至少有一个可行走 tile。
- 地图边界无越界对象。
- Tiled JSON 能被 Tiled 打开。

验收标准：

- 至少 20 条 prompt 自动生成并全部导出成功。
- Tiled 能正常打开导出的 JSON。
- 碰撞层、对象层、事件层可见。
- 失败生成会给出明确错误报告，而不是静默失败。

## 5. 阶段 3：编辑器和局部重生成

目标：从一次性生成升级为可迭代制作流程。

周期建议：4-6 周。

能力范围：

- Web 地图预览。
- 显示和隐藏不同层级。
- 框选区域。
- 局部 prompt，例如“把这里改成集市”。
- 锁定区域。
- seed 复现。
- 撤销和重做。
- 导入已有 Tiled JSON 后继续编辑。

验收标准：

- 用户可以对局部区域重新生成，而不破坏锁定区域。
- 局部生成后仍通过可达性和碰撞校验。
- 至少支持 10 次编辑历史回退。
- 同一 seed 下可复现局部生成结果。

主要风险：

- 局部重生成破坏全局连通性。
- 锁定区域和新区域边界拼接不自然。
- 重新生成导致对象 id 和事件引用丢失。

## 6. 阶段 4：地图元素生成和素材库

目标：让系统在固定 tileset 之外，能生成缺失的地图对象和装饰元素。

周期建议：4-8 周。

能力范围：

- 单个 object sprite 生成。
- 简单建筑组件生成。
- 素材自动 metadata 标注。
- 素材库标签检索。
- 缺失素材自动生成并回填到对象库。

输出要求：

- PNG 透明背景。
- 统一 tile 网格尺寸。
- metadata 包含标签、footprint、anchor、collision。
- 对象可被地图生成器自动放置。

验收标准：

- 可以根据描述生成至少 20 种地图对象。
- 生成对象能自动放入 object layer。
- 对象碰撞和占地信息正确。
- 同一主题下生成物风格基本一致。

主要风险：

- AI 生成素材风格不稳定。
- 透明背景和边缘清理质量不足。
- 生成对象难以自动计算准确碰撞盒。

## 7. 阶段 5：角色 Sprite Sheet 生成

目标：生成 RPG 可用的 NPC、怪物和主角基础动画。

周期建议：6-10 周。

第一版能力：

- 4 方向：down、left、right、up。
- 2 个动作：idle、walk。
- 每动作 4 帧或 6 帧。
- PNG sprite sheet。
- JSON metadata。
- feet anchor 和基础 hitbox。

后续扩展：

- run。
- attack。
- cast。
- hurt。
- death。
- weapon socket。
- portrait。

验收标准：

- 至少 10 个角色可以生成完整 idle/walk 表。
- 动画播放时不明显跳帧。
- 同一角色跨方向、跨动作外观一致。
- 导出的 metadata 能被测试播放器读取。

主要风险：

- 多方向一致性难。
- 动作帧连贯性难。
- 武器、衣服、发型在不同帧中容易漂移。

## 8. 阶段 6：特效动画帧生成

目标：生成可挂载到技能、交互和环境事件上的 VFX sprite sheet。

周期建议：4-6 周。

第一版能力：

- fireball。
- slash。
- heal。
- explosion。
- teleport。
- sparkle。
- rain / snow / falling leaves。

输出要求：

- PNG sprite sheet。
- JSON metadata。
- fps。
- loop 标记。
- blend mode。
- anchor。

验收标准：

- 至少 10 种特效可以生成。
- 特效在测试播放器中能按 metadata 正确播放。
- 一次性特效和循环特效区分清楚。
- 特效中心点、锚点和缩放合理。

## 9. 阶段 7：引擎导出和插件化

目标：从通用导出升级为引擎可直接使用。

周期建议：6-10 周。

优先级：

1. Tiled JSON 稳定导出。
2. Godot TileMap / TileSet 导出。
3. Unity Tilemap 导出。
4. Phaser tilemap 导出。

能力范围：

- Tiled JSON / TMX。
- Godot 工程资源适配。
- Unity importer 或导入脚本。
- Phaser JSON 和加载示例。
- 运行时 collision、object、event 读取示例。

验收标准：

- 同一地图可在 Tiled 中打开。
- 同一地图可导入 Godot 并显示正确。
- Unity/Phaser 至少提供可运行 sample。
- 碰撞、出生点、对象层在目标引擎中可读取。

## 10. 六个月建议排期

| 月份 | 重点 | 主要结果 |
| --- | --- | --- |
| 第 1 月 | 协议、地图 MVP | 文本生成基础 RPG 地图 |
| 第 2 月 | 校验、预览、Tiled 导出 | 地图能进入 Tiled 工具链 |
| 第 3 月 | Web 预览、局部重生成 | 用户可以迭代修改地图 |
| 第 4 月 | 地图元素生成、素材库 | 缺失对象可自动生成和放置 |
| 第 5 月 | 角色 sprite sheet | NPC/怪物 idle/walk 可用 |
| 第 6 月 | 特效动画、引擎导出 | VFX 和 Godot/Unity/Phaser 雏形 |

## 11. 推荐优先级

必须先完成：

- `RPGMapSpec`。
- 固定 tileset 的地图生成。
- 可达性和碰撞校验。
- Tiled JSON 导出。
- PNG 预览。

完成后再做：

- 局部重生成。
- 自定义地图元素生成。
- 角色和特效生成。
- 多引擎导出。

最后考虑：

- 多人协作。
- 资产市场。
- 大规模风格训练。
- 自动剧情和任务生成。

## 12. 风险验证清单

早期必须验证的问题：

- LLM 是否能稳定产出可校验的 `RPGMapSpec`。
- 地图生成算法是否能满足可达性和美观度。
- Tiled JSON 导出是否足够稳定。
- 固定 tileset 是否能覆盖第一批 demo 场景。
- 局部重生成是否能保持边界自然。
- AI 生成 object 是否能保持透明背景和风格一致。
- 角色多方向、多动作一致性是否可接受。

## 13. 第一批 Demo 建议

建议准备 5 个 demo 场景作为验收样例：

1. 秋季森林村庄：河流、集市、神庙、村民。
2. 小型地下城：入口、大厅、boss 房、宝箱、陷阱。
3. 雪地营地：松树、木屋、篝火、巡逻 NPC。
4. 沙漠遗迹：断墙、神坛、仙人掌、隐藏入口。
5. 海边渔村：码头、船、鱼市、灯塔。

每个 demo 都需要保存：

- 原始 prompt。
- `RPGMapSpec`。
- seed。
- 导出的 Tiled JSON。
- PNG 预览。
- 校验报告。

