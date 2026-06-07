---
title: RPG 素材生成 - Q 版角色包
date: 2026-06-02
status: 2026-06-03 重新生成，QA 通过
---

# Q 版角色素材包

## 任务目标

基于原始照片 `D:\证件照片\1.jpg`，生成 Q 版（2 头身 chibi）像素风 RPG 角色完整素材包。

**角色设定**：11-12 岁中国六年级男生（2008 年杀马特斜刘海风格）+ 蓝白校服 + 红领巾 + 书包 + 彩色多层光影

## 产出清单

**输出目录**：`D:\PersonalProject\class_six\tools\ai\out\hero01_q\`

**当前状态**：
- 立绘、表情、sprite、预览页已生成。
- 2026-06-02 QA 检查曾发现部分 sprite 存在边缘残留、帧锚点跳动、疑似重复角色/方向不稳问题。
- 2026-06-03 已重新生成立绘、7 张表情和全部 7 组 sprite；`audit_q_hero.py` 最终结果为 0 错误、0 警告。
- 生成流程已补充自动 QA 和返修入口，后续新增/重生成素材必须通过 `audit_q_hero.py` 后才能标记完成。

### 1. 立绘
- `portrait-q.png` (1024×1024)

### 2. 表情包（7 张）
- `face-q-neutral.png` - 中性
- `face-q-happy.png` - 开心
- `face-q-angry.png` - 愤怒
- `face-q-sad.png` - 悲伤
- `face-q-surprised.png` - 惊讶
- `face-q-shy.png` - 害羞
- `face-q-hurt.png` - 受伤

### 3. 行走 Sprite（16 帧）
**目录**：`sprites/`
- `walk-down-{1,2,3,4}.png` - 向下行走 4 帧
- `walk-up-{1,2,3,4}.png` - 向上行走 4 帧
- `walk-left-{1,2,3,4}.png` - 向左行走 4 帧
- `walk-right-{1,2,3,4}.png` - 向右行走 4 帧

### 4. 战斗 Sprite（12 帧）
**目录**：`sprites/`
- `battle-idle-{1,2,3,4}.png` - 待机 4 帧
- `battle-attack-{1,2,3,4}.png` - 攻击 4 帧
- `battle-hurt-{1,2,3,4}.png` - 受伤 4 帧

**规格**：所有 sprite 为 512×512 透明 PNG（洋红背景已抠除）

### 5. 预览页面
- `preview.html` - 动画预览（可调速度、全部播放/暂停）

## 生成脚本

### 立绘 + 表情
```powershell
cd D:\PersonalProject\class_six\tools\ai
python gen_q_hero.py --only all
```

**分步执行**：
- `--only portrait` - 仅生成立绘
- `--only faces` - 仅生成表情（需要先有立绘）
- `--ref <图片路径>` - 指定立绘参考图；默认优先 `D:\证件照片\1.jpg`，找不到时回退到旧 hero01 立绘
- `--force` - 即使目标 PNG 已存在也重新生成

### 行走 + 战斗 Sprite
```powershell
python gen_q_sprite_sheet.py --anim all --concurrency 2
```

**单独生成某组**：
- `--anim walk-down` - 仅生成向下行走
- `--anim battle-idle` - 仅生成战斗待机
- `--max-attempts 1` - 只用现有 sheet 重新切片/抠图/标准化，不触发新模型调用
- `--max-attempts 2` - 默认；现有 sheet 修复失败后，再重新生成 sheet
- `--force` - 忽略已通过 QA 的最终 PNG，强制重新处理已有 sheet/最终帧
- `--regenerate-sheet` - 立即调用模型生成新 sheet，不先复用已有 sheet
- `--edge-clean-pixels 2` - 抠图后清掉外圈像素，减少网格/边缘残留

### 自动 QA
```powershell
python audit_q_hero.py
```

QA 检查项：
- 文件数量、尺寸、alpha 通道
- sprite 四边不透明残留
- 同组帧 bbox 中心点跳动
- 同组 bbox 宽高/不透明面积异常，用于拦截疑似重复角色或坏裁切

## 技术细节

### 生成流程
1. Gemini 生成 1024×1024 雪碧图（2×2 网格，4 帧）
2. 程序切片为 4 张 512×512 PNG（不再经过 JPG 中间文件）
3. `jpg_to_png_alpha.py` 洋红抠图 → 透明 PNG
4. 自动清理边缘残留、按 alpha bbox 重锚定同组帧
5. `audit_q_hero.py` 审计通过后才可进入游戏导入

### 关键参数
- **模型**：`gemini-3.1-flash-image-preview` (via bobdong.cn)
- **参考图**：立绘默认用原始照片，sprite 用 Q 版透明立绘 `portrait-q.png`
- **抠图**：`--mode auto --tolerance 25 --halo-passes 4`

### 配置文件
- `config.local.json` - Gemini API Key
- `gen_q_hero.py` - 立绘/表情生成脚本
- `gen_q_sprite_sheet.py` - Sprite sheet 批量生成脚本
- `audit_q_hero.py` - Q 版角色包 QA 审计脚本

## 使用方式

### 游戏引擎导入
1. 导入 PNG 序列：`walk-down-{1..4}.png` 为一组动画
2. 帧率建议：行走 5fps (200ms/帧)，战斗 8fps (120ms/帧)
3. 尺寸：保持 512×512 原尺寸或在引擎内缩放（推荐用 NEAREST 插值保留像素风）

### 预览效果
双击 `preview.html` 在浏览器中查看所有动画

### 返修流程
1. 先跑 `python audit_q_hero.py`，确认失败组。
2. 对失败组优先跑 `python gen_q_sprite_sheet.py --anim <组名> --max-attempts 1`，只用现有 sheet 本地重处理。
3. 如果仍失败，再跑 `python gen_q_sprite_sheet.py --anim <组名> --max-attempts 2`，脚本会在现有 sheet 修复失败后触发新 sheet。
4. 如需跳过本地复用、直接新生成，使用 `python gen_q_sprite_sheet.py --anim <组名> --regenerate-sheet --force`。
5. 重跑 `python audit_q_hero.py`，通过后再更新本文档状态。

## 后续扩展

如需新增角色/NPC：
1. 通过 `gen_q_hero.py --ref <图片路径>` 替换参考图
2. 调整 prompt 中的角色描述
3. 修改输出目录 `OUT_DIR`
4. 跑完整 QA，不通过不进入游戏导入
