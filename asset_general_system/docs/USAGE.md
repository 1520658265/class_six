# 使用教程 - 从零到完整 RPG 资源包

## 📋 目录

1. [快速开始](#快速开始)
2. [生成地图](#生成地图)
3. [生成对象素材](#生成对象素材)
4. [生成角色](#生成角色)
5. [生成特效](#生成特效)
6. [导出到游戏引擎](#导出到游戏引擎)
7. [完整示例](#完整示例)

---

## 快速开始

### 1. 安装依赖

```bash
cd D:\AI\class_six\asset_general_system
pip install pillow numpy requests
```

### 2. 配置 Gemini API（可选）

**使用 Mock 模式（测试用）**：
- 不需要配置，直接用，生成纯色块图像

**使用真实 AI 生成**：
```bash
cd D:\AI\class_six\tools\ai
# 编辑 config.local.json，添加：
{
  "services": {
    "gemini_image": {
      "api_host": "bobdong.cn",
      "api_key": "你的-API-key",
      "model": "gemini-3.1-flash-image-preview"
    }
  }
}
```

获取免费 API key：https://aistudio.google.com/app/apikey

---

## 生成地图

### 方式 1：命令行（简单）

```bash
cd D:\AI\class_six\asset_general_system

# 生成秋季村庄
python -c "
from pathlib import Path
from generator.parser import PromptParser
from generator.map import MapGenerator
from generator.export import TiledExporter

# 解析 prompt
parser = PromptParser()
spec = parser.parse('生成一个秋季森林村庄，中间有集市，左侧有河流，右上角有神庙')

# 生成地图
generator = MapGenerator()
tilemap = generator.generate(spec)

# 导出
exporter = TiledExporter()
exporter.export(tilemap, Path('output/autumn_village'))
print('✓ 生成完成: output/autumn_village/')
"
```

### 方式 2：Python 脚本（完整）

创建 `examples/generate_map.py`：

```python
from pathlib import Path
from generator.parser import PromptParser
from generator.map import MapGenerator
from generator.export import TiledExporter
from generator.validation import MapValidator
from generator.render import PreviewRenderer

def generate_map(prompt: str, output_dir: Path):
    """生成完整地图包。"""
    output_dir = Path(output_dir)
    
    # 1. 解析 prompt
    print(f"[1/5] 解析 prompt: {prompt}")
    parser = PromptParser()
    spec = parser.parse(prompt)
    
    # 2. 生成地图
    print("[2/5] 生成地图...")
    generator = MapGenerator()
    tilemap = generator.generate(spec)
    
    # 3. 校验
    print("[3/5] 校验地图...")
    validator = MapValidator()
    report = validator.validate(tilemap)
    if report.errors:
        print(f"  警告: {len(report.errors)} 个错误")
        for err in report.errors[:3]:
            print(f"    - {err.message}")
    
    # 4. 导出
    print("[4/5] 导出 Tiled JSON...")
    exporter = TiledExporter()
    exporter.export(tilemap, output_dir)
    
    # 5. 生成预览图
    print("[5/5] 生成预览图...")
    renderer = PreviewRenderer()
    renderer.render(tilemap, output_dir / "preview.png")
    
    print(f"\n✓ 完成! 输出目录: {output_dir}")
    print(f"  - map.tiled.json (Tiled 可打开)")
    print(f"  - preview.png (预览图)")
    print(f"  - map_data.json (原始数据)")

if __name__ == "__main__":
    generate_map(
        prompt="生成一个秋季森林村庄，中间有集市，左侧有河流",
        output_dir=Path("output/autumn_village")
    )
```

运行：
```bash
python examples/generate_map.py
```

---

## 生成对象素材

### 使用 Mock 生成（测试）

```python
from pathlib import Path
from generator.assets.image_generation import MockImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects

# Mock 生成器（纯色块）
mock_gen = MockImageGenerator(Path("output/mock"))

# 对象生成器
obj_gen = ObjectGenerator(mock_gen, Path("output/objects"))

# 生成 20 种标准对象
print("生成 20 种标准对象...")
results = generate_standard_objects(obj_gen, seed_offset=5000)

# 统计
success = [r for r in results if r.success]
print(f"✓ 成功: {len(success)}/20")
for r in success[:5]:
    print(f"  - {r.asset_id}: {r.sprite_path}")
```

### 使用 Gemini 真实生成

```python
from pathlib import Path
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects

# Gemini 生成器（真实 AI）
gemini_gen = GeminiImageGenerator(Path("output/gemini"))

# 对象生成器
obj_gen = ObjectGenerator(gemini_gen, Path("output/objects"))

# 生成 20 种标准对象
print("使用 Gemini 生成 20 种对象...")
results = generate_standard_objects(obj_gen, seed_offset=5000)

# 查看结果
for r in results:
    if r.success:
        print(f"✓ {r.asset_id}")
        print(f"  图像: {r.sprite_path}")
        print(f"  metadata: {r.metadata_path}")
```

### 生成特定对象

```python
from generator.assets.object_generator import ObjectGenerationRequest

# 自定义对象
request = ObjectGenerationRequest(
    object_type="magic_tree",
    description="a glowing magical tree with blue leaves and sparkling particles",
    footprint=(2, 3),  # 占 2x3 tiles
    tags=["tree", "magic", "decoration"],
    seed=1234,
)

result = obj_gen.generate(request)
if result.success:
    print(f"✓ 生成魔法树: {result.sprite_path}")
```

---

## 生成角色

```python
from pathlib import Path
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.characters import CharacterGenerator, generate_standard_characters

# 创建生成器
gemini = GeminiImageGenerator(Path("output/gemini"))
char_gen = CharacterGenerator(gemini, Path("output/characters"))

# 生成 10 个标准角色
print("生成 10 个标准角色...")
results = generate_standard_characters(char_gen, seed_offset=6000)

for r in results:
    if r.success:
        print(f"✓ {r.asset_id}")
        print(f"  sprite sheet: {r.sheet_path}")
        print(f"  动画数: {len(r.metadata.animations)}")
```

### 生成自定义角色

```python
from generator.characters import CharacterGenerationRequest

request = CharacterGenerationRequest(
    character_type="wizard",
    description="old wizard with purple robe and long white beard",
    tags=["wizard", "magic", "old"],
    seed=7000,
)

result = char_gen.generate(request)
if result.success:
    print(f"✓ {result.asset_id}: {result.sheet_path}")
    print(f"  方向: {[d.value for d in result.metadata.directions]}")
    print(f"  动作: {list(result.metadata.animations.keys())}")
```

---

## 生成特效

```python
from pathlib import Path
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.vfx import VFXGenerator, generate_standard_vfx

# 创建生成器
gemini = GeminiImageGenerator(Path("output/gemini"))
vfx_gen = VFXGenerator(gemini, Path("output/vfx"))

# 生成 10 种标准 VFX
print("生成 10 种 VFX...")
results = generate_standard_vfx(vfx_gen, seed_offset=8000)

for r in results:
    if r.success:
        print(f"✓ {r.asset_id}")
        print(f"  类别: {r.metadata.category.value}")
        print(f"  帧数: {r.metadata.frames}, blend: {r.metadata.blend.value}")
```

### 生成自定义特效

```python
from generator.vfx import VFXGenerationRequest
from generator.models.vfx import BlendMode, VFXCategory

request = VFXGenerationRequest(
    vfx_type="ice_blast",
    description="blue ice crystal explosion with frost particles",
    frame_size=(64, 64),
    frames=8,
    fps=15,
    loop=False,
    blend=BlendMode.ADDITIVE,
    category=VFXCategory.MAGIC,
    seed=9000,
)

result = vfx_gen.generate(request)
if result.success:
    print(f"✓ {result.asset_id}: {result.sheet_path}")
```

---

## 导出到游戏引擎

### 导出到 Godot

```python
from pathlib import Path
from generator.export import GodotExporter

# 假设你已经有了 tilemap
exporter = GodotExporter()
report = exporter.export(
    tilemap=tilemap,
    output_dir=Path("output/godot"),
    scene_name="autumn_village"
)

print("✓ Godot 导出完成:")
for f in report['files']:
    print(f"  - {f}")
```

**在 Godot 中使用**：
1. 复制 `output/godot/` 到 Godot 项目的 `res://maps/`
2. 在 Godot 中打开 `autumn_village.tscn`
3. 运行场景

### 导出到 Unity

```python
from generator.export import UnityExporter

exporter = UnityExporter()
report = exporter.export(tilemap, Path("output/unity"))

print("✓ Unity 导出完成:")
for f in report['files']:
    print(f"  - {f}")
```

**在 Unity 中使用**：
1. 复制 `output/unity/` 到 Unity 项目的 `Assets/Maps/`
2. 创建空 GameObject，挂载 `ImportTilemap.cs`
3. 配置 JSON 文件和 Tile 数组
4. 运行

### 导出到 Phaser

```python
from generator.export import PhaserExporter

exporter = PhaserExporter()
report = exporter.export(
    tilemap=tilemap,
    output_dir=Path("output/phaser"),
    scene_key="MainScene"
)

print("✓ Phaser 导出完成:")
for f in report['files']:
    print(f"  - {f}")
```

**在 Phaser 中使用**：
1. 启动本地服务器：`python -m http.server -d output/phaser`
2. 浏览器打开 `http://localhost:8000/index.html`
3. 或集成到现有 Phaser 项目

---

## 完整示例

创建 `examples/full_pipeline.py`：

```python
#!/usr/bin/env python
"""完整流程：从 prompt 到引擎资源包。"""

from pathlib import Path
from generator.parser import PromptParser
from generator.map import MapGenerator
from generator.assets.gemini_generator import GeminiImageGenerator
from generator.assets.object_generator import ObjectGenerator, generate_standard_objects
from generator.characters import CharacterGenerator, generate_standard_characters
from generator.vfx import VFXGenerator, generate_standard_vfx
from generator.map.object_placer import ObjectPlacer
from generator.assets.asset_library import AssetLibrary
from generator.export import GodotExporter, UnityExporter, PhaserExporter

def main():
    output_base = Path("output/full_demo")
    
    print("="*60)
    print("完整 RPG 资源生成流程")
    print("="*60)
    
    # 1. 生成素材库
    print("\n[1/6] 生成素材库...")
    gemini = GeminiImageGenerator(output_base / "gemini")
    
    # 1a. 对象
    print("  生成 20 种对象...")
    obj_gen = ObjectGenerator(gemini, output_base / "objects")
    obj_results = generate_standard_objects(obj_gen, seed_offset=5000)
    print(f"  ✓ {len([r for r in obj_results if r.success])}/20 对象")
    
    # 1b. 角色
    print("  生成 10 个角色...")
    char_gen = CharacterGenerator(gemini, output_base / "characters")
    char_results = generate_standard_characters(char_gen, seed_offset=6000)
    print(f"  ✓ {len([r for r in char_results if r.success])}/10 角色")
    
    # 1c. 特效
    print("  生成 10 种 VFX...")
    vfx_gen = VFXGenerator(gemini, output_base / "vfx")
    vfx_results = generate_standard_vfx(vfx_gen, seed_offset=7000)
    print(f"  ✓ {len([r for r in vfx_results if r.success])}/10 VFX")
    
    # 2. 生成地图
    print("\n[2/6] 生成地图...")
    parser = PromptParser()
    spec = parser.parse("生成一个秋季森林村庄，中间有集市，左侧有河流")
    generator = MapGenerator()
    tilemap = generator.generate(spec)
    print(f"  ✓ 地图尺寸: {tilemap.map.width}x{tilemap.map.height}")
    
    # 3. 放置对象
    print("\n[3/6] 放置对象到地图...")
    library = AssetLibrary(output_base / "objects")
    placer = ObjectPlacer(library)
    
    # 在集市区域放置摊位
    for region in tilemap.regions:
        if region.type == "market":
            cx, cy = region.center
            for i in range(-2, 3):
                placer.place_decoration_objects(
                    tilemap,
                    object_type="stall",
                    positions=[(cx + i, cy)]
                )
    print(f"  ✓ 已放置 {len(tilemap.objects)} 个对象")
    
    # 4. 导出到 Godot
    print("\n[4/6] 导出到 Godot...")
    godot_exp = GodotExporter()
    godot_report = godot_exp.export(tilemap, output_base / "godot", "demo_map")
    print(f"  ✓ {len(godot_report['files'])} 个文件")
    
    # 5. 导出到 Unity
    print("\n[5/6] 导出到 Unity...")
    unity_exp = UnityExporter()
    unity_report = unity_exp.export(tilemap, output_base / "unity")
    print(f"  ✓ {len(unity_report['files'])} 个文件")
    
    # 6. 导出到 Phaser
    print("\n[6/6] 导出到 Phaser...")
    phaser_exp = PhaserExporter()
    phaser_report = phaser_exp.export(tilemap, output_base / "phaser", "DemoScene")
    print(f"  ✓ {len(phaser_report['files'])} 个文件")
    
    print("\n" + "="*60)
    print("✓ 全部完成!")
    print("="*60)
    print(f"\n输出目录: {output_base}")
    print("  objects/    - 20 种对象素材")
    print("  characters/ - 10 个角色 sprite sheet")
    print("  vfx/        - 10 种特效")
    print("  godot/      - Godot 4.x 场景和资源")
    print("  unity/      - Unity 数据和脚本")
    print("  phaser/     - Phaser 3 tilemap 和场景")

if __name__ == "__main__":
    main()
```

运行：
```bash
python examples/full_pipeline.py
```

---

## 常见问题

### Q: Gemini 生成太慢

A: 使用 Mock 模式快速测试：
```python
from generator.assets.image_generation import MockImageGenerator
mock_gen = MockImageGenerator(Path("output/mock"))
```

### Q: 生成的图像背景不透明

A: 系统会自动后处理，如果还是不满意：
```python
# 在 prompt 中强调
request.prompt = "your object, solid white background, isolated"
# 然后用工具手动移除白色
```

### Q: 想要其他风格（非像素画）

A: 修改 style 参数：
```python
request = ObjectGenerationRequest(
    ...
    style=ImageStyle.HAND_DRAWN,  # 或 LOW_POLY
)
```

### Q: API 配额用完了

A: 切回 Mock 模式，或使用本地 Stable Diffusion（需要自己集成）

---

## 进阶技巧

### 批量生成优化

```python
from concurrent.futures import ThreadPoolExecutor

def generate_batch(requests, generator, max_workers=2):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(generator.generate, req) for req in requests]
        return [f.result() for f in futures]

# 注意：Gemini API 有限流，建议 max_workers=2
```

### 质量检查

```python
from generator.assets.style_checker import StyleConsistencyChecker

checker = StyleConsistencyChecker()
issues = checker.check_batch([
    Path("output/objects/tree_oak_5001.png"),
    Path("output/objects/tree_pine_5002.png"),
])

for issue in issues:
    print(f"警告: {issue}")
```

### 自动补齐缺失素材

```python
from generator.map.missing_asset_handler import MissingAssetHandler

handler = MissingAssetHandler(library, gemini)
tilemap_with_missing = ...  # 地图引用了不存在的对象

fixed_tilemap = handler.handle_missing_assets(tilemap_with_missing)
# 自动生成缺失的对象并回填
```

---

**需要帮助？**
- 查看 `docs/` 目录下的详细文档
- 运行测试：`python tests/test_*.py`
- 查看示例：`examples/` 目录
