# 使用实例 - 3 个实战示例

## 示例 1：生成完整地图包（最常用）

```bash
cd D:\AI\class_six\asset_general_system
python examples/full_pipeline.py
```

**输出**：
- `output/full_demo/objects/` - 20 种对象素材
- `output/full_demo/characters/` - 10 个角色 sprite sheets
- `output/full_demo/vfx/` - 10 种特效
- `output/full_demo/godot/` - Godot 场景
- `output/full_demo/unity/` - Unity 数据
- `output/full_demo/phaser/` - Phaser 场景
- `output/full_demo/preview.png` - 预览图

**用时**：约 10-30 秒（Mock 模式）

---

## 示例 2：只生成地图

```python
from pathlib import Path
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.map import MapGenerator
from generator.export import GodotExporter

# 1. 解析 prompt
parser = RulePromptParser()
request = GenerateRequest(prompt="生成一个秋季村庄，中间有集市")
spec = parser.parse(request)

# 2. 生成地图
generator = MapGenerator()
tilemap = generator.generate(spec)

# 3. 导出
exporter = GodotExporter()
exporter.export(tilemap, Path("output/my_map"), "my_scene")

print("完成！查看: output/my_map/my_scene.tscn")
```

---

## 示例 3：只生成角色

```python
from pathlib import Path
from generator.assets.image_generation import MockImageGenerator
from generator.characters import CharacterGenerator, CharacterGenerationRequest

# 1. 创建生成器
image_gen = MockImageGenerator(Path("output/mock"))
char_gen = CharacterGenerator(image_gen, Path("output/characters"))

# 2. 生成一个角色
request = CharacterGenerationRequest(
    character_type="warrior",
    description="armored warrior with sword",
    tags=["warrior", "hero"],
    seed=1001,
)

result = char_gen.generate(request)

if result.success:
    print(f"成功: {result.sheet_path}")
    print(f"动画数: {len(result.metadata.animations)}")
```

---

## 示例 4：只生成对象

```python
from pathlib import Path
from generator.assets.image_generation import MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects

# 1. 创建生成器
image_gen = MockImageGenerator(Path("output/mock"))
obj_gen = ObjectGenerator(image_gen, Path("output/objects"))

# 2. 生成 20 种标准对象
results = generate_standard_objects(obj_gen, seed_offset=5000)

# 3. 查看结果
for r in results:
    if r.success:
        print(f"{r.asset_id}: {r.sprite_path}")
```

---

## 示例 5：使用真实 Gemini 生成

**前提**：配置 API key

```bash
# 方式 1：配置文件
编辑 D:\AI\class_six\tools\ai\config.local.json
添加 gemini_image 配置

# 方式 2：环境变量
set GEMINI_IMAGE_API_KEY=你的-key
```

**代码**：

```python
from pathlib import Path
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.assets.object_generator import ObjectGenerator

# 替换这一行即可！
image_gen = GeminiImageGenerator(Path("output/gemini"))
obj_gen = ObjectGenerator(image_gen, Path("output/objects"))

# 其他代码完全一样
results = generate_standard_objects(obj_gen)
```

---

## 示例 6：完整工作流（地图 + 素材 + 导出）

```python
from pathlib import Path
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.map import MapGenerator
from generator.assets.image_generation import MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.map.object_placer import ObjectPlacer
from generator.assets.asset_library import AssetLibrary
from generator.export import GodotExporter

# 步骤 1：生成素材库
image_gen = MockImageGenerator(Path("output/mock"))
obj_gen = ObjectGenerator(image_gen, Path("output/objects"))
generate_standard_objects(obj_gen)

# 步骤 2：生成地图
parser = RulePromptParser()
request = GenerateRequest(prompt="生成一个村庄地图")
spec = parser.parse(request)
tilemap = MapGenerator().generate(spec)

# 步骤 3：放置对象
library = AssetLibrary(Path("output/objects"))
placer = ObjectPlacer(library)
for region in tilemap.regions:
    if region.type == "market":
        cx, cy = region.center
        placer.place_decoration_objects(tilemap, "stall", [(cx, cy)])

# 步骤 4：导出
GodotExporter().export(tilemap, Path("output/godot"), "village")

print("完成！")
```

---

## 常用命令速查

```bash
# 运行完整示例
python examples/full_pipeline.py

# 查看生成结果
cd output/full_demo
start preview.png                    # 预览图
start godot/demo_map.tscn           # Godot 场景
start phaser/index.html             # Phaser（需启动 http server）

# 运行测试
python tests/test_phase5_characters.py
python tests/test_phase6_vfx.py
python tests/test_phase7_engines.py
```

---

## 切换到真实 AI 生成

**只需修改 1 行代码**：

```python
# 之前（Mock - 纯色块）
from generator.assets.image_generation import MockImageGenerator
image_gen = MockImageGenerator(Path("output/mock"))

# 之后（Gemini - 真实 AI）
from generator.assets.gemini_generator import GeminiImageGenerator
image_gen = GeminiImageGenerator(Path("output/gemini"))

# 其他代码完全不变！
```

---

## 目录结构

```
output/
├── full_demo/           # 完整示例输出
│   ├── objects/         # 对象素材
│   ├── characters/      # 角色素材
│   ├── vfx/            # 特效素材
│   ├── godot/          # Godot 导出
│   ├── unity/          # Unity 导出
│   ├── phaser/         # Phaser 导出
│   └── preview.png     # 预览图
```

---

## 下一步

1. **运行示例**：`python examples/full_pipeline.py`
2. **查看预览**：`output/full_demo/preview.png`
3. **在引擎打开**：
   - Godot: `output/full_demo/godot/demo_map.tscn`
   - Phaser: `output/full_demo/phaser/index.html`
4. **配置 Gemini**（可选）：见 `docs/gemini_integration_updated.md`

---

## 需要帮助？

- 详细教程：`docs/USAGE.md`
- 安装依赖：`docs/INSTALL.md`
- Gemini 配置：`docs/gemini_integration_updated.md`
- 完整报告：`FINAL_SUMMARY.md`
