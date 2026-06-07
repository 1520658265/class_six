# 快速开始 - 5 分钟上手

## 第一步：运行完整示例

```bash
cd D:\AI\class_six\asset_general_system
python examples/full_pipeline.py
```

等待 10-30 秒，完成后查看：
- `output/full_demo/preview.png` - 预览图
- `output/full_demo/REPORT.txt` - 详细报告

## 第二步：查看生成的资源

```
output/full_demo/
├── objects/         20 种对象（树/石头/箱子等）
├── characters/      10 个角色 sprite sheets
├── vfx/            10 种特效
├── godot/          Godot 4.x 场景
├── unity/          Unity 数据
├── phaser/         Phaser 3 场景
└── preview.png     地图预览
```

## 第三步：在游戏引擎中打开

**Godot 4.x**:
1. 打开 Godot
2. 导入项目或复制 `output/full_demo/godot/` 到你的项目
3. 打开 `demo_map.tscn`

**Phaser 3**:
1. `cd output/full_demo/phaser`
2. `python -m http.server`
3. 浏览器打开 `http://localhost:8000/index.html`

## 第四步：生成自己的地图

编辑 `examples/full_pipeline.py` 第 71 行：

```python
# 修改这里的 prompt
request = GenerateRequest(prompt="生成一个雪地城堡，周围是冰山")
```

重新运行即可。

## 第五步：使用真实 AI 生成（可选）

1. 获取 Gemini API key: https://aistudio.google.com/app/apikey
2. 配置：编辑 `D:\AI\class_six\tools\ai\config.local.json`
3. 修改 `examples/full_pipeline.py` 第 42 行：

```python
# 改这一行
from generator.assets.gemini_generator import GeminiImageGenerator
image_gen = GeminiImageGenerator(output_base / "gemini")
```

---

完成！更多示例见 `EXAMPLES.md`
