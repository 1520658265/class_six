# 依赖安装说明

## 核心依赖

```bash
pip install pillow numpy
```

## Gemini 后端依赖

```bash
pip install requests
```

## 完整安装

```bash
pip install pillow numpy requests
```

## 可选依赖

- **rembg**（更好的透明背景处理）：`pip install rembg`
- **pytest**（运行测试）：`pip install pytest`

## 验证安装

```bash
python -c "from generator.assets.gemini_generator import GeminiImageGenerator; print('OK')"
```
