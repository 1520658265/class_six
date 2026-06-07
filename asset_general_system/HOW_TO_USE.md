# AI RPG 素材生成器 - 真实使用方式

## 核心理念

**输入一句描述，自动生成对应素材。**

不是预定义"20 种对象"让你挑，而是真正按你描述生成。

---

## 三种使用方式

### 方式 1：单次生成（最简单）

```bash
cd D:\AI\class_six\asset_general_system

# 一句描述，搞定
python generate.py "穿铠甲的兔子战士"
python generate.py "古老的金色宝箱"
python generate.py "火球术爆炸特效"
python generate.py "秋季森林村庄，中间有集市"
```

系统自动判断类型（角色/对象/特效/地图），生成对应素材。

---

### 方式 2：交互模式（连续生成）

```bash
python generate.py
```

进入交互式 prompt：

```
============================================================
交互模式 - 输入描述生成素材（输入 quit/q 退出）
============================================================

>>> 穿铠甲的兔子战士
[类型: character]
正在生成角色: 穿铠甲的兔子战士
  asset slug: warrior_rabbit
  ...
[成功] 角色生成完成

>>> 古老的金色宝箱
[类型: object]
正在生成对象: 古老的金色宝箱
  ...

>>> type:character
[已切换] 类型 -> character

>>> 蓝色史莱姆            # 现在强制作为角色生成
...

>>> q
[退出]
```

---

### 方式 3：批量生成（一次出多个）

创建 `assets.txt`：

```text
# 角色
character: 穿铠甲的兔子战士
character: 戴红帽的圣诞精灵
character: 邪恶的骷髅法师

# 对象
古老的金色宝箱
蓝色魔法水晶
发光的魔法蘑菇

# 特效
vfx: 火球术
vfx: 治疗光环

# 地图
map: 秋季森林村庄
```

运行：

```bash
python generate.py --batch assets.txt
```

输出：

```
读取批量文件: assets.txt
共 9 个任务

[1/9] 穿铠甲的兔子战士 (character)
...
[2/9] 戴红帽的圣诞精灵 (character)
...
============================================================
批量完成: 成功 9, 失败 0
============================================================
```

---

## 实际效果

输入：

```bash
python generate.py "穿铠甲的兔子战士"
```

输出：

```
正在生成角色: 穿铠甲的兔子战士
  asset slug: warrior_rabbit          ← 自动生成英文 slug
  提取标签: ['warrior', 'rabbit', 'armor']  ← 自动提取标签

[成功] 角色生成完成
  asset_id: warrior_rabbit_6135
  sprite sheet: output/generated/characters/warrior_rabbit_6135.png
  metadata: output/generated/characters/warrior_rabbit_6135.json
  动画数: 8                           ← 4方向 × 2动作
  方向: ['down', 'left', 'right', 'up']
```

生成的文件：

```
output/generated/characters/
├── warrior_rabbit_6135.png      # sprite sheet (128x384)
└── warrior_rabbit_6135.json     # 完整 metadata
```

JSON metadata：

```json
{
  "asset_id": "warrior_rabbit_6135",
  "frame_size": [32, 48],
  "directions": ["down", "left", "right", "up"],
  "animations": {
    "idle_down": {"row": 0, "frames": 4, "fps": 4, "loop": true},
    "walk_down": {"row": 4, "frames": 4, "fps": 8, "loop": true},
    ...
  },
  "anchor": "feet_center",
  "hitbox": [8, 32, 16, 16],
  "tags": ["warrior", "rabbit", "armor"]
}
```

---

## Slug 自动生成示例

系统会从中文描述自动提取英文 slug：

| 描述 | 自动生成的 slug |
|------|----------------|
| 穿铠甲的兔子战士 | `warrior_rabbit` |
| 戴红帽的圣诞精灵 | `christmas_elf` |
| 古老的金色宝箱 | `gold_chest` |
| 蓝色魔法水晶 | `blue_crystal` |
| 邪恶的骷髅法师 | `evil_mage_skeleton` |
| 魔法森林中的发光蘑菇 | `magic_mushroom` |
| 巨大的史莱姆怪 | `giant_slime` |

---

## 自动类型判断

| 描述包含 | 判为 |
|---------|------|
| 战士、骑士、兔子、村民等 | character |
| 火球术、特效、爆炸 | vfx |
| 村庄、地图、城市、场景 | map |
| 其他静态物品（蘑菇、宝箱、水晶...） | object |

如果判断错了，可以手动指定：

```bash
python generate.py "魔法蘑菇" --type object
python generate.py "蓝色光球" --type vfx
```

---

## 切换到真实 AI（Gemini）

### 1. 配置 API key

编辑 `D:\AI\class_six\tools\ai\config.local.json`：

```json
{
  "services": {
    "gemini_image": {
      "api_host": "bobdong.cn",
      "api_key": "你的-Gemini-API-key",
      "model": "gemini-3.1-flash-image-preview"
    }
  }
}
```

获取 API key：https://aistudio.google.com/app/apikey

### 2. 加 `--gemini` 参数

```bash
python generate.py "穿铠甲的兔子战士" --gemini
```

预期时间：
- 对象：5-10 秒
- 特效：1-2 分钟（8 帧）
- 角色：2-5 分钟（32 帧）
- 地图：几秒（不依赖图像生成）

### 3. 配置缺失时自动降级

没配 API key 时，系统会自动 fallback 到 Mock 模式：

```
[警告] Gemini 初始化失败: Missing API key for 'gemini_image'.
[警告] 自动切换到 Mock 模式
```

---

## 完整命令参数

```bash
python generate.py [描述] [选项]
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `描述` | 素材描述（不传时进入交互模式） | - |
| `--type, -t` | object / character / vfx / map / auto | auto |
| `--gemini, -g` | 使用 Gemini AI 真实生成 | False (Mock) |
| `--output, -o` | 输出目录 | output/generated |
| `--seed, -s` | 随机种子（用于复现） | 自动 |
| `--interactive, -i` | 交互模式 | False |
| `--batch, -b` | 批量模式（从文件读取） | - |

---

## 实战流程：做一个完整 RPG

### 1. 准备 `my_game_assets.txt`：

```text
# 主角
character: 金发少年勇者，绿色斗篷

# NPC
character: 白胡子村长
character: 肌肉壮汉铁匠
character: 魔法商店老板娘

# 怪物
character: 森林狼怪
character: 巨型蜘蛛
character: 暗影法师 boss

# 装饰
村庄路标
魔法水晶
古老石碑

# 特效
vfx: 火球术
vfx: 治疗光环
vfx: 暴击特效

# 地图
map: 起始村庄，中央广场，周围有商店
```

### 2. 一键生成所有素材：

```bash
python generate.py --batch my_game_assets.txt --gemini
```

### 3. 完成！查看 `output/generated/`：

```
output/generated/
├── characters/         # 7 个角色 sprite sheets
├── objects/           # 3 个装饰对象
├── vfx/              # 3 个特效
├── godot/            # Godot 场景
├── preview.png       # 地图预览
└── ...
```

---

## 常见问题

### Q: 生成的图像看起来是色块？

A: 默认 Mock 模式生成纯色块占位图。要真实图像，加 `--gemini` 并配置 API key。

### Q: 类型判断错了？

A: 用 `--type` 参数手动指定，或在交互模式中用 `type:character` 切换。

### Q: 想要相同种子复现？

A: 加 `--seed` 参数：
```bash
python generate.py "兔子战士" --seed 42
```

### Q: 批量文件支持注释吗？

A: 支持。以 `#` 开头的行被跳过，空行也跳过。

### Q: 怎么强制指定批量中某行的类型？

A: 用 `type: 描述` 格式：
```text
character: 兔子战士
vfx: 火球术
map: 秋季村庄
```

---

## 总结

**最常用的命令**：

```bash
# 单次生成
python generate.py "你的描述"

# 交互模式
python generate.py

# 批量生成
python generate.py --batch assets.txt

# 切换真实 AI
python generate.py "你的描述" --gemini
```

就这四种用法，搞定所有素材生成需求。

---

更详细的示例见 `examples/batch_assets.txt`。
