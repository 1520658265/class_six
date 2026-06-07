# RPG 素材生成工作流-spec

> 输入一张真实人物照片，在 Liblib（基于 SD）平台批量产出 HD 像素风（《八方旅人》HD-2D 风）的完整 RPG 素材包，用于 Unity / Godot 项目。
>
> 本文档独立于《元生的六年级》项目自身的 32×32 美术资产清单，定位为「通用素材生产管线」规格。

---

## 1. 目标与适用范围

### 1.1 目标

- 输入：单张真实人物照片
- 输出：HD 像素风（高分辨率像素艺术，非 16-bit 复古颗粒）完整 RPG 素材包，可直接用于 Unity / Godot
- 平台：Liblib（基于 Stable Diffusion）

### 1.2 适用范围

- **风格定位**：HD pixel art / HD-2D 风（参考《Octopath Traveler》《Triangle Strategy》），不是 SNES 那种粗颗粒
- **生产规模**：主角团（≤5 人）精调 + 批量 NPC（数十至上百）模板化
- **使用引擎**：Unity / Godot，输出格式服从两者通用规范（PNG + JSON 元数据）

---

## 2. 输出素材清单

| 类型 | 单帧规格 | 帧数/张数 | 生产方式 |
|---|---|---|---|
| 立绘 Portrait | 1024×1536 | 每套武器组合 1 张 | 预渲染组合 |
| 头像 Face | 256×256 | 每角色 1 张 | 立绘裁切 + 精修 |
| 表情差分 Expression | 256×256 | 每角色 6–8 种 | 与头像同构图，仅替换面部 |
| 行走图 Walk | 128×128 | 4 方向 × 4 帧 = 16 帧 | 分图层（基础 + 装备） |
| 战斗图 Battle | 256×256 | 12 动作 × 共 57 帧 | 分图层（基础 + 武器） |
| 装备图层 Equipment | 与目标素材同尺寸 | 每件装备 1 套 | 透明底，锚点对齐 |

### 2.1 表情差分清单（6–8 种）

平静 / 高兴 / 愤怒 / 悲伤 / 惊讶 / 害羞 / 受伤 / 闭眼

### 2.2 战斗动作清单（12 组 / 57 帧）

| 动作 | 帧数 | 说明 |
|---|---|---|
| 待机 idle | 4 | 呼吸循环 |
| 走入 walk-in | 4 | 上场 / 接近敌人 |
| 普通攻击 attack | 6 | 起手 → 挥击 → 收招 |
| 重攻击 / 蓄力 charge | 6 | 蓄力技 |
| 技能释放 skill | 8 | 法术 / 必杀，动作幅度大 |
| 防御 guard | 3 | 举盾 / 格挡 |
| 闪避 dodge | 4 | 侧身 / 翻滚 |
| 受伤 hurt | 3 | 被击退 |
| 暴击受伤 critical-hurt | 4 | 大幅后仰 |
| 濒死 low-hp | 4 | 弯腰喘气，循环 |
| 死亡 dead | 5 | 倒地 |
| 胜利 victory | 6 | 胜利姿势 |

---

## 3. 双产线架构

```
                    ┌─────────────────────┐
                    │   真实照片输入       │
                    └──────────┬──────────┘
                               ↓
              ┌────────────────┴────────────────┐
              ↓                                 ↓
        【主角产线·精调】                  【NPC 产线·模板化】
              ↓                                 ↓
   1. IP-Adapter 扩样本（20-30 张）      仅 IP-Adapter Face 一次性迁移
   2. 训练角色 LoRA（触发词 char_xxx）         + 固定 seed
   3. 角色 LoRA + 像素 LoRA 出全套素材        + 模板 prompt
              ↓                                 ↓
              └────────────────┬────────────────┘
                               ↓
                    分图层输出 + 锚点对齐
                               ↓
                    Unity / Godot 运行时组装
```

### 3.1 两条产线对比

| | 主角产线（精调） | NPC 产线（模板化） |
|---|---|---|
| 特征来源 | 训练专属角色 LoRA（20–30 张扩样本） | 仅用 IP-Adapter Face 一次性迁移 |
| 立绘 | 每套武器单独出图，对话精修 | 模板 prompt + 换脸，批量出 |
| 行走图 | 分图层：裸模 + 多套装备层 | 固定 2–3 套模板，换色换脸 |
| 战斗图 | 分图层：基础 + 武器层，每动作精调 | 共用骨架模板，换皮 |
| 表情 | 完整差分（6–8 种） | 2–3 种基础表情 |
| 一致性保障 | LoRA 锁死 | IP-Adapter + seed 锁定 |

---

## 4. Liblib 平台配置

### 4.1 通用底模与 LoRA

| 项目 | 选择 | 权重 |
|---|---|---|
| 底模 | SDXL 1.0 / Pony Diffusion V6 XL | — |
| 风格 LoRA | HD Pixel Art / Octopath Traveler 风 LoRA | 0.8–1.0 |
| 角色 LoRA（主角） | 自训 | 0.7–0.9 |
| 人脸迁移（NPC） | IP-Adapter Plus Face / InstantID | 0.6–0.7 |
| 姿态控制 | ControlNet OpenPose / Canny | 0.8 |

### 4.2 关键参数锁定

- **Seed**：同一角色全程锁定一个 seed
- **采样器**：DPM++ 2M Karras / Euler a
- **CFG**：6–7
- **步数**：30–35
- **风格 base prompt**：固定一段（HD pixel art, 16-bit detailed style, octopath traveler style, limited palette, crisp pixels, no anti-aliasing, cel shading, bold outline），所有素材共用，只改主体描述

### 4.3 通用负向 prompt

```
realistic, photorealistic, photo, 3d, octane, unreal engine, cgi,
blurry, anti-aliasing, smooth shading, soft lighting, depth of field,
nsfw, lowres, bad anatomy, bad hands, missing fingers, extra fingers,
watermark, signature, text, logo, jpeg artifacts,
multiple characters, duplicate, frame inconsistency,
oil painting, watercolor, sketch
```

---

## 5. 六阶段生产流程

### Stage 1：扩样本（仅主角）

- 输入原始照片 + IP-Adapter，生成 20–30 张同人物不同角度 / 光照 / 表情样本
- 用途：为 LoRA 训练准备样本集

### Stage 2：训练角色 LoRA（仅主角）

- 工具：Liblib 在线训练
- 底模：与最终生图一致（SDXL 或 Pony V6）
- 触发词：`char_<角色名>`，例如 `char_hero01`

### Stage 3：立绘（预渲染组合）

- 主角：底模 + 角色 LoRA + 像素风 LoRA
- 列出每个角色的武器组合清单（例：剑+轻甲、剑+重甲、弓+轻甲）
- 每个组合单独出一张
- NPC：仅 IP-Adapter Face，不训 LoRA

### Stage 4：行走图（分图层）

- ControlNet 灌行走图骨架模板（4 方向 × 4 帧标准 sprite 排布图）
- **基础层**：裸模 / 内衣，单独 16 帧
- **装备层**：每套装备（头 / 身 / 手 / 脚 / 武器）单独 16 帧，透明底
- 严格锁 seed + ControlNet 权重 0.8–1.0 保证帧间一致

### Stage 5：战斗图（分图层）

- 12 个动作分别灌不同的 OpenPose 动作序列模板
- 基础层 + 武器层分别出图
- 每个动作单独一组 sprite sheet，便于 Unity Animator / Godot AnimationPlayer 调用

### Stage 6：表情差分 + 头像

- 头像：从立绘裁切上半身 + 微调
- 表情：用 Inpainting 蒙版只重绘脸部区域，固定其他参数
- 6–8 种表情按 §2.1 清单生产

---

## 6. 分图层与锚点系统

为了「运行时装备组装」成立，必须保证：

- **统一画布尺寸**：基础层和装备层尺寸完全一致
- **统一锚点**：人物脚底中心点在每帧固定像素坐标
- **透明底**：装备层除装备本体外全透明
- **命名规范**：`<角色>_<动作>_<方向>_<帧号>_<层>.png`
  - 例：`hero01_attack_down_03_weapon-sword.png`
  - 例：`hero01_walk_left_02_armor-light.png`
- **基础层命名约定**：`<角色>_<动作>_<方向>_<帧号>_base.png`

---

## 7. 一致性保障策略

| 风险 | 应对 |
|---|---|
| 多帧间人物长得不一样 | 角色 LoRA + seed 锁定 + ControlNet |
| 风格漂移（突然变写实/3D） | 强力负向 prompt + 风格 LoRA 高权重 |
| 装备层和基础层错位 | ControlNet 用同一张骨架，禁止改 seed |
| 表情差分构图变了 | Inpainting 蒙版精确到面部，不重绘整图 |

---

## 8. 目录结构

```
<工作流根目录>/
├── docs/
│   └── design/
│       └── rpg素材生成工作流-spec.md         ← 本文档
├── prompts/                                  ← 各阶段 prompt 模板
│   ├── base-style.txt                        ← 通用风格 base prompt
│   ├── negative-prompt.txt                   ← 通用负向 prompt
│   ├── hero-prompts/                         ← 主角各场景 prompt
│   │   ├── portrait.txt
│   │   ├── walk.txt
│   │   └── battle-<动作>.txt
│   └── controlnet-templates/                 ← ControlNet 骨架模板图
│       ├── walk-4dir-4frame.png
│       ├── battle-idle.png
│       ├── battle-attack.png
│       └── ...
└── assets/                                   ← 生成的素材
    └── characters/
        └── <角色>/
            ├── source-photo/                 ← 原始参考照片
            ├── lora-samples/                 ← 扩样本（仅主角）
            ├── lora-model/                   ← 训练好的 LoRA 文件（仅主角）
            ├── portraits/                    ← 立绘（按武器组合分子目录）
            ├── face/                         ← 头像
            ├── expressions/                  ← 表情差分
            ├── walk/                         ← 行走图
            │   ├── base/                     ← 基础层
            │   └── equipment/                ← 装备层（按装备分子目录）
            └── battle/                       ← 战斗图（按动作分子目录）
                ├── idle/
                │   ├── base/
                │   └── equipment/
                ├── attack/
                └── ...
```

---

## 9. 已知风险与缓解

1. **SD 系单次 grid 出图易崩**：行走图 / 战斗图分单帧出，不一次出 grid，后期脚本拼接
2. **Liblib LoRA 训练有上限**：先用 IP-Adapter 验证人物相似度可接受，再决定是否训 LoRA（避免无效训练）
3. **HD 像素风 LoRA 稀缺**：如果找不到合适的 HD 像素 LoRA，回退方案为普通像素 LoRA + 后期超分
4. **武器层与人物手部错位**：ControlNet 骨架里手部要单独标注，作为锚点
5. **批量 NPC 风格漂移**：批量出图时每 5–10 张换 seed 检查一次，发现风格漂移立即停产并重新锁参数

---

## 10. 后续工作

- 编写各阶段 prompt 模板（`prompts/` 目录）
- 收集 / 制作 ControlNet 骨架模板图（行走图 + 12 战斗动作）
- 编写命名规范校验脚本（可选，建议放 `tools/` 目录）
- 编写 Unity / Godot 运行时分图层组装示例代码（可选）

---

## 变更历史

| 日期 | 变更 | 备注 |
|---|---|---|
| 2026-06-01 | 初版 | 经 brainstorming 流程产出 |
