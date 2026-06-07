# Gemini 集成快速开始

## 安装

```bash
pip install google-generativeai pillow numpy
```

## 获取 API Key

访问 https://aistudio.google.com/app/apikey 获取免费 API key。

## 使用示例

### 生成对象

```python
import os
from pathlib import Path
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects

# 设置 API key
os.environ["GEMINI_API_KEY"] = "your-api-key-here"

# 创建 Gemini 生成器
gemini_gen = GeminiImageGenerator(output_dir=Path("output/gemini"))

# 创建对象生成器
obj_gen = ObjectGenerator(gemini_gen, output_dir=Path("output/objects"))

# 生成 20 种标准对象
results = generate_standard_objects(obj_gen, seed_offset=5000)

# 查看结果
for r in results:
    if r.success:
        print(f"✓ {r.asset_id}: {r.sprite_path}")
    else:
        print(f"✗ {r.asset_id}: {r.error}")
```

### 生成角色

```python
from generator.characters import CharacterGenerator, generate_standard_characters

char_gen = CharacterGenerator(gemini_gen, output_dir=Path("output/characters"))
results = generate_standard_characters(char_gen, seed_offset=6000)
```

### 生成 VFX

```python
from generator.vfx import VFXGenerator, generate_standard_vfx

vfx_gen = VFXGenerator(gemini_gen, output_dir=Path("output/vfx"))
results = generate_standard_vfx(vfx_gen, seed_offset=7000)
```

## Fast 模式

快速迭代时使用 Fast 模型（3-5 秒/张）：

```python
from generator.assets.gemini_generator import GeminiImagenFastGenerator

fast_gen = GeminiImagenFastGenerator(output_dir=Path("output/gemini_fast"))
```

## 测试

```bash
# 设置 API key
export GEMINI_API_KEY='your-key'

# 运行测试
python tests/test_gemini_integration.py
```

## 注意事项

1. **API 配额**：免费版有请求限制，大批量生成建议付费或使用本地 Stable Diffusion
2. **生成速度**：每张图 3-20 秒，批量生成需要时间
3. **透明背景**：Gemini 不保证完美透明，复杂场景可能需要手动修正

## 故障排查

### 错误：google-generativeai 未安装

```bash
pip install google-generativeai
```

### 错误：API key 无效

检查 API key 是否正确设置：

```python
import os
print(os.getenv("GEMINI_API_KEY"))
```

### 速度太慢

使用 Fast 模型：

```python
from generator.assets.gemini_generator import GeminiImagenFastGenerator
```
