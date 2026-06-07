# Gemini Imagen 集成说明

更新时间：2026-06-06

## 已完成

✅ `GeminiImageGenerator` - Gemini Imagen 3.0 图像生成后端  
✅ `GeminiImagenFastGenerator` - Fast 模式（更快，质量稍低）  
✅ 透明背景后处理  
✅ Aspect ratio 自动映射  
✅ 测试套件

## 使用方法

### 1. 安装依赖

```bash
pip install google-generativeai
```

### 2. 获取 API Key

访问：https://aistudio.google.com/app/apikey

### 3. 设置环境变量

```bash
export GEMINI_API_KEY='your-api-key-here'
```

### 4. 替换生成器

#### 生成对象

```python
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.assets.object_generator import ObjectGenerator

gemini_gen = GeminiImageGenerator(output_dir=Path("output/mock"))
obj_gen = ObjectGenerator(gemini_gen, output_dir=Path("output/objects"))

# 正常使用
results = generate_standard_objects(obj_gen)
```

#### 生成角色

```python
from generator.characters import CharacterGenerator

char_gen = CharacterGenerator(gemini_gen, output_dir=Path("output/characters"))
results = generate_standard_characters(char_gen)
```

#### 生成 VFX

```python
from generator.vfx import VFXGenerator

vfx_gen = VFXGenerator(gemini_gen, output_dir=Path("output/vfx"))
results = generate_standard_vfx(vfx_gen)
```

## Gemini Imagen 特性

### 支持的 Aspect Ratios

- 1:1（正方形）
- 3:4（竖屏）
- 4:3（横屏）
- 9:16（手机竖屏）
- 16:9（宽屏）

### 模型选择

- `imagen-3.0-generate-001`：高质量，慢（~10-20 秒/张）
- `imagen-3.0-fast-generate-001`：快速，质量略低（~3-5 秒/张）

### 透明背景处理

Gemini 不保证生成透明背景，系统会自动后处理：
1. 检测四角主色调
2. 移除相似颜色
3. 生成 alpha 通道

高级场景建议使用 `rembg` 或 Segment Anything Model。

## 限制

1. **尺寸约束**：Gemini 只支持固定 aspect ratio，会自动映射到最接近的比例
2. **速度**：每张图 3-20 秒（取决于模型）
3. **透明背景**：不保证完美，复杂场景可能需要手动修正
4. **API 配额**：免费版有请求限制

## 与 MockGenerator 对比

| 特性 | MockGenerator | GeminiImageGenerator |
|------|---------------|----------------------|
| 速度 | 即时 | 3-20 秒/张 |
| 质量 | 纯色块 | 真实像素画 |
| 成本 | 免费 | API 收费 |
| 测试友好 | ✅ | ❌ |
| 生产可用 | ❌ | ✅ |

## 最佳实践

### 测试时用 Mock

```python
if os.getenv("CI") or not os.getenv("GEMINI_API_KEY"):
    generator = MockImageGenerator(output_dir)
else:
    generator = GeminiImageGenerator(output_dir)
```

### 批量生成时用 Fast 模型

```python
from generator.assets.gemini_generator import GeminiImagenFastGenerator

fast_gen = GeminiImagenFastGenerator(output_dir)
```

### 缓存结果

生成的图像自动保存到 `output_dir`，带时间戳和 seed，避免重复生成。

## 故障排查

### 错误：API key 无效

```
ValueError: GEMINI_API_KEY 环境变量未设置
```

**解决**：设置环境变量或传入 `api_key` 参数。

### 错误：google-generativeai 未安装

```
RuntimeError: google-generativeai 未安装
```

**解决**：`pip install google-generativeai`

### 错误：透明背景不完美

**原因**：Gemini 生成的图像可能有复杂背景。

**解决方案**：
1. 在 prompt 中强调 "solid white background" 然后移除白色
2. 使用 `rembg` 库后处理
3. 手动 Photoshop 修正

### 错误：生成速度慢

**解决**：
- 切换到 `GeminiImagenFastGenerator`
- 并行生成多张（注意 API 限流）
- 缓存已生成的图像

## 下一步

- 集成 DALL-E 3 作为备选后端
- 集成本地 Stable Diffusion
- 实现 batch 生成优化
- 添加生成质量评分和自动重试
