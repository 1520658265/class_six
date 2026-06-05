# RPG 素材生产操作手册

## 前置准备

### 环境
- Liblib 账号（在线生图权限）
- Python 3.10+（辅助脚本）
- Pillow 库：`pip install Pillow`

### 素材准备
- 角色参考照片（正面清晰，光线均匀）
- ControlNet 骨架模板图（见 prompts/controlnet/README.md）
- 确认 Liblib 上可用的 LoRA：搜索 "pixel art"、"HD-2D"、"octopath"

---

## 主角生产流程（6 阶段）

### Stage 1：扩样本

1. 进入 Liblib → 在线生图 → img2img 模式
2. 上传角色照片
3. 挂载 IP-Adapter Plus Face，权重 0.7
4. 正向 prompt：使用 `prompts/base-style.txt` + 角度描述
5. 生成 20-30 张不同角度/光照/表情的同一人物图
6. 保存到 `assets/characters/{角色}/lora-samples/`

**验收标准**：20+ 张图，人物五官一致，角度覆盖正/侧/背/3-4

### Stage 2：训练角色 LoRA

1. 进入 Liblib → LoRA 训练
2. 上传 Stage 1 的扩样本
3. 底模选择：与最终生图一致（SDXL / Pony V6）
4. 触发词设为：`char_{角色名}`
5. 训练完成后下载/记录 LoRA ID
6. 保存到 `assets/characters/{角色}/lora-model/`

**验收标准**：用触发词 + 简单 prompt 生成 3 张测试图，确认人物一致

### Stage 3：立绘

1. 打开 `prompts/hero/portrait.txt`
2. 替换变量：角色描述、服装、武器
3. 拼接 base-style.txt 内容到正向 prompt 开头
4. 设置 Liblib 参数（见模板内说明）
5. 每套武器组合生成 3-5 张，选最佳
6. 保存到 `assets/characters/{角色}/portraits/`

**验收标准**：风格为 HD 像素风，人物与照片相似度 > 70%

### Stage 4：行走图

1. 打开 `prompts/hero/walk.txt`
2. 挂载 ControlNet OpenPose + 对应骨架模板图
3. 按 4 方向 × 4 帧 = 16 次生成
4. 基础层和装备层分别生成（见模板内图层说明）
5. 保存到 `assets/characters/{角色}/walk/base/` 和 `walk/equipment/`
6. 运行命名校验：
   `python tools/validate_naming.py assets/characters/{角色}/walk/`
7. 拼接 sprite sheet：
   `python tools/assemble_spritesheet.py assets/characters/{角色}/walk/base/ output/walk-base.png --cols 4 --rows 4`

**验收标准**：16 帧人物一致，帧间无明显跳变，装备层与基础层对齐

### Stage 5：战斗图

1. 打开 `prompts/hero/battle-{动作}.txt`
2. 挂载 ControlNet OpenPose + 对应动作骨架模板
3. 按每个动作的帧数逐帧生成
4. 基础层和武器层分别生成
5. 保存到 `assets/characters/{角色}/battle/{动作}/base/` 和 `battle/{动作}/equipment/`
6. 运行命名校验
7. 每个动作单独拼接 sprite sheet

**验收标准**：动作流畅，武器层与手部对齐

### Stage 6：表情差分 + 头像

1. 从立绘裁切上半身作为头像底图
2. 用 img2img 微调为 256×256 正方形头像
3. 用 Inpainting 模式 + `prompts/hero/expression.txt` 生成表情差分
4. 保存到 `assets/characters/{角色}/face/` 和 `expressions/`

**验收标准**：表情差分仅面部变化，轮廓/发型/服装不变

---

## NPC 批量生产流程

1. 准备 NPC 照片
2. 选择模板类型（普通/持物/老人儿童）
3. 使用 `prompts/npc/` 下对应模板
4. IP-Adapter Face 权重 0.6，无需训 LoRA
5. 每 5-10 个 NPC 检查一次风格一致性
6. 发现漂移立即停产排查

---

## 常见问题排查

| 现象 | 原因 | 解决 |
|---|---|---|
| 出来还是真人脸 | IP-Adapter 权重太高 | 降到 0.4-0.5 |
| 完全不像本人 | LoRA 权重太低或未加载 | 检查触发词，权重提到 0.8 |
| 不是像素风 | 像素 LoRA 权重不够 | 提到 1.0，检查底模 |
| 帧间人物不一致 | seed 未锁定 | 全程同一 seed |
| 装备层错位 | ControlNet 骨架不同 | 确认所有帧用同一骨架 |
| 风格突然变 3D | 负向 prompt 缺失 | 检查 negative-prompt.txt 是否完整 |
