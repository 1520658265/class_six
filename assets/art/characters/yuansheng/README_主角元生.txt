主角元生资产说明

1. char_yuansheng_concept_v2.png
- 当前主角概念基准图
- 视觉设定：酷帅杀马特、小学六年级、要面子、爱装酷

2. char_yuansheng_portraits_v1.png
- 主角对话头像表第一版
- 模型生成了 8 格，不是严格 6 格，但角色一致性较好，可先用于对话系统选表情

3. char_yuansheng_walksheet_source_v1.png
- 当前可用的主角 4x4 行走表来源图
- 来源于旧生成结果，但比 v2/v3 行走表更接近可切片规范

4. walk/*.png
- 已切出的 16 帧 32x32 透明 PNG
- 可直接用于 Godot AnimatedSprite2D / SpriteFrames 测试
- 后续如果拿到更严格的手工 sheet，可整体替换

5. tools/ai/out/角色/主角元生_行走表_v2.png
6. tools/ai/out/角色/主角元生_行走表_v3.jpg
- 这两张保留为本轮失败尝试，不建议直接用于工程切片

7. battle/
- 主角横版战斗资产目录
- body/ 放战斗本体动作，不内嵌武器
- weapons/ 放可替换武器/校园物件层：空手、书包、扫帚、铝饭盒、悠悠球、黑板擦
- effects/ 放基础战斗特效：灰尘、挥击弧线、受击星星、闪避残影等
- 详细分层和 Godot 挂点设计见 battle/README_主角元生战斗资产.txt
