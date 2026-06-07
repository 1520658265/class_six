# Gemini 集成说明（复用上级工具）

更新时间：2026-06-06

## 说明

本系统复用了上级 `tools/ai/gen_with_gemini.py` 的实现，使用：
- **模型**：gemini-3.1-flash-image-preview
- **代理**：bobdong.cn（国内可访问）
- **配置**：tools/ai/config.local.json

## 配置步骤

### 1. 创建配置文件

```bash
cd D:\AI\class_six\tools\ai
cp config.example.json config.local.json
```

### 2. 编辑 config.local.json

```json
{
  "services": {
    "gemini_image": {
      "api_host": "bobdong.cn",
      "api_key": "your-gemini-api-key-here",
      "model": "gemini-3.1-flash-image-preview"
    }
  }
}
```

### 3. 获取 API Key

访问：https://aistudio.google.com/app/apikey

### 4. 环境变量方式（可选）

也可以不用配置文件，直接设置环境变量：

```bash
export GEMINI_IMAGE_API_KEY='your-key'
export GEMINI_IMAGE_API_HOST='bobdong.cn'  # 可选
export GEMINI_IMAGE_MODEL='gemini-3.1-flash-image-preview'  # 可选
```

## 使用方法

### 生成对象

```python
from pathlib import Path
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects

# 创建 Gemini 生成器（自动读取配置）
gemini_gen = GeminiImageGenerator(output_dir=Path("output/gemini"))

# 创建对象生成器
obj_gen = ObjectGenerator(gemini_gen, output_dir=Path("output/objects"))

# 生成 20 种标准对象
results = generate_standard_objects(obj_gen, seed_offset=5000)

# 查看结果
for r in results:
    if r.success:
        print(f"✓ {r.asset_id}: {r.sprite_path}")
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

## 与原 gen_with_gemini.py 的区别

| 特性 | gen_with_gemini.py | GeminiImageGenerator |
|------|-------------------|---------------------|
| 用途 | CLI 工具，手动调用 | Python API，程序化调用 |
| 输入 | prompt 文件 | ImageGenerationRequest 对象 |
| 配置 | config.local.json | 相同 |
| 后处理 | 无 | 自动透明背景、尺寸调整 |
| 重试机制 | ✅ | ✅ |
| 参考图 | 支持 --ref | 暂不支持（可扩展） |

## 特性

### 支持的 Aspect Ratios

gemini-3.1-flash-image-preview 支持：
- 1:1（正方形）
- 3:2（横屏）
- 7:2（宽屏）
- 16:9（超宽）
- 2:3（竖屏）

系统会自动映射请求的尺寸到最接近的 aspect ratio。

### 自动后处理

1. **透明背景**：检测四角主色调并移除
2. **尺寸调整**：缩放到请求的精确尺寸
3. **格式统一**：输出 PNG RGBA

### 重试机制

- 默认最多 4 次尝试
- 失败后指数退避（2s, 4s, 6s, 8s）
- 超时时间：300 秒

## 性能

- **速度**：3-8 秒/张（取决于网络和服务器负载）
- **质量**：适合像素画风格
- **成本**：通过 bobdong.cn 代理，价格较低

## 故障排查

### 错误：Missing API key

```
RuntimeError: Missing API key for 'gemini_image'. Create ...
```

**解决**：
1. 确认 `tools/ai/config.local.json` 存在
2. 确认 `services.gemini_image.api_key` 字段已填写
3. 或设置 `GEMINI_IMAGE_API_KEY` 环境变量

### 错误：ai_config 模块未找到

**解决**：GeminiImageGenerator 会自动添加 `tools/ai/` 到 Python path，如果还是失败：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("D:/AI/class_six/tools/ai")))
```

### 网络超时

bobdong.cn 代理偶尔会超时。**解决**：
- 重试几次（系统自动重试 4 次）
- 或切换到官方 API（需要科学上网）：
  ```json
  "api_host": "generativelanguage.googleapis.com"
  ```

## 测试

```bash
# 运行集成测试（需要配置 API key）
cd D:\AI\class_six\asset_general_system
python tests/test_gemini_integration.py
```

## 对比：官方 SDK vs bobdong.cn

| 方式 | 优势 | 劣势 |
|------|------|------|
| 官方 SDK | 官方支持，稳定 | 需要科学上网 |
| bobdong.cn | 国内直连 | 第三方代理，可能不稳定 |

本系统默认使用 bobdong.cn，如果你有稳定的科学上网环境，可以改用官方 API。
