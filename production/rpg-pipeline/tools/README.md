# 角色 Prompt 生成器

自动读取角色配置文件，替换模板变量，生成可直接复制到 Liblib 的完整 prompt。

## 功能

- 读取角色配置 JSON（包含角色名、描述、发色、服装、武器等）
- 自动替换 prompts/ 下所有模板中的变量
- 生成 output/{角色名}/ 目录下的所有 prompt 文件
- 每个文件包含：正向 prompt、负向 prompt、Liblib 参数清单

## 使用方法

### 1. 创建角色配置文件

创建一个 JSON 文件（例如 `hero01-config.json`）：

```json
{
  "name": "hero01",
  "description": "1boy, short black hair, tan skin, lean build, determined expression",
  "outfit": "light leather armor, brown cloak, belt with pouches, leather boots",
  "weapon": "holding longsword in right hand, steel blade with leather grip"
}
```

**配置字段说明：**

- `name`: 角色名称（用于文件命名和 LoRA 标签）
- `description`: 角色基础描述（发色、发型、肤色、体型、表情等）
- `outfit`: 服装描述（具体装备组合）
- `weapon`: 武器描述（持剑/持弓/持杖等）

### 2. 运行脚本

```bash
python generate_prompts.py hero01-config.json
```

### 3. 查看生成结果

生成的文件位于 `output/{角色名}/` 目录：

```
output/hero01/
├── portrait.txt              # 立绘
├── walk.txt                  # 行走图
├── battle-attack.txt         # 战斗图 - 攻击
├── battle-charge.txt         # 战斗图 - 冲锋
├── battle-critical-hurt.txt  # 战斗图 - 重伤
├── battle-dead.txt           # 战斗图 - 死亡
├── battle-dodge.txt          # 战斗图 - 闪避
├── battle-guard.txt          # 战斗图 - 防御
├── battle-hurt.txt           # 战斗图 - 受伤
├── battle-idle.txt           # 战斗图 - 待机
├── battle-low-hp.txt         # 战斗图 - 低血量
├── battle-skill.txt          # 战斗图 - 技能
├── battle-victory.txt        # 战斗图 - 胜利
├── battle-walk-in.txt        # 战斗图 - 入场
├── expression.txt            # 表情差分
└── face-icon.txt             # 头像
```

## 变量替换规则

脚本会自动替换以下变量：

- `{base-style.txt 内容}` → 读取 base-style.txt 完整内容
- `{角色描述}` / `{角色描述：xxx}` → config.description
- `{服装描述}` / `{服装描述：xxx}` → config.outfit
- `{武器描述}` / `{武器描述：xxx}` → config.weapon
- `{角色名}` → config.name

**保持原样的变量（使用时手动替换）：**

- `{方向描述}` / `{步态描述}` / `{帧描述}` - 行走图和战斗图的帧变量
- `{表情描述}` - 表情差分的表情变量

## 输出文件格式

每个生成的文件包含三个部分：

```
# ========================================
# portrait.txt
# ========================================

## 正向 Prompt（可直接复制）

[完整的正向 prompt，已替换所有角色变量]

## 负向 Prompt

[从 negative-prompt.txt 读取的负向 prompt]

## Liblib 参数

# 底模: SDXL 1.0 / Pony V6
# 尺寸: 832x1216 或 1024x1536
# 采样器: DPM++ 2M Karras
# ...
```

## 示例

参考 `example-config.json` 查看完整的配置示例。

## 注意事项

1. 确保 `prompts/` 目录下的模板文件存在
2. 配置文件必须是有效的 JSON 格式
3. 生成的 prompt 可以直接复制到 Liblib 使用
4. 部分变量（如帧描述、表情描述）需要在使用时手动替换
