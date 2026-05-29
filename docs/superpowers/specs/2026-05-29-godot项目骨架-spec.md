# Godot 项目骨架与通用资产管线 spec

> 创建日期：2026-05-29
> 范围：Godot 工程目录、命名、autoload、资产烤点管线、通用 helper API
> 不在范围：角色控制器、对话系统、存档、战斗系统、场景切换（各自后续 spec）
> Godot 版本：4.6
> 关联：[美术资产清单-spec.md](../../design/美术资产清单-spec.md)、[战斗特效动效实现-spec.md](../../design/战斗特效动效实现-spec.md)、[2026-05-28-对话肖像-spec.md](2026-05-28-对话肖像-spec.md)

---

## 一、目标

为《元生的六年级》提供 Godot 工程地基：

1. 把仓库根改造成 Godot 工程根（`project.godot` 在根目录）
2. 把所有美术资产管线统一到一份 manifest + 一组烤点脚本 + 4 个 autoload helper + 1 个生成常量类 `AssetIds`
3. 业务代码用名字驱动调用资产：`Sprites.walk_frames("yuansheng")`、`Portraits.get_expression("yuansheng", "smile")`、`VFX.spawn("push_dust", pos)`、`Atlas.get_item("props_p0", "lunchbox")`
4. 添加新资产 = 改 manifest + 跑一次烤点脚本，不写任何运行时代码

非目标：
- 不实现角色移动、对话、存档等业务逻辑
- 不约束场景文件结构（业务 spec 自定）
- 不约束 UI 主题/字体（UI spec 自定）

---

## 二、设计原则

### 2.1 薄 helper + 厚资源

所有"运行慢"的事（图片切片、帧拼装、参数解析）在烤点期完成，落地为 `.tres` 进 git。运行时只 `load("res://...")`。

收益：
- `AnimatedSprite2D` 在 Godot 编辑器里直接看到帧
- 0 反射、业务代码 0 拼路径、0 运行时切片（helper 内部允许按约定式资源路径加载烤点产物）
- 性能稳定，资产规模线性扩展

### 2.2 名字驱动 + 烤点生成常量

业务代码用名字调用，但名字来自烤点生成的 `AssetIds`，IDE 自动补全 + 拼错红线：

```gdscript
$Sprite.sprite_frames = Sprites.walk_frames(AssetIds.Char.YUANSHENG)
$Portrait.texture = Portraits.get_expression(AssetIds.Char.YUANSHENG, AssetIds.Portrait.Yuansheng.SMILE)
```

### 2.3 拼错就崩，不做 fallback

helper 不返回兜底贴图、不打 warning 继续。资产缺失是开发期问题，崩在调用点比静默错误更省时间。

### 2.4 烤点产物全部进 git

`resources/*.tres`、`asset_ids.gd` 都进 git。好处：
- 没装 Godot 的人也能 review
- CI 不跑烤点
- 跨机器/平台一致
- diff 可见"这次改了什么资产"

---

## 三、目录结构

仓库根 = Godot 工程根。所有 `res://` 路径基于仓库根。

```
class_six/
├── project.godot                        ← 新建（Godot 4.6）
├── icon.svg                             ← 新建
├── README.md                            ← 已有
│
├── assets/                              ← 已有，原始资产（烤点输入）
│   └── art/
│       ├── characters/<id>/
│       │   ├── walk/                    ← 整张行走 sheet
│       │   ├── portrait/                ← 整张肖像 sheet
│       │   ├── battle/{body,effects,weapons}/
│       │   └── raw/                     ← 概念图/参考图，烤点不读
│       ├── effects/<group>/
│       ├── props/{p0,p1,p2}/
│       ├── ui/<group>/
│       └── scenes/{p0,p1,p2}/
│
├── resources/                           ← 新建，烤点产物（进 git）
│   ├── sprite_frames/<id>.tres          ← SpriteFrames（一角色一资源）
│   ├── portraits/<id>.tres              ← PortraitSet
│   ├── vfx/<name>.tres                  ← VfxClip
│   └── atlas/<category>.tres            ← AtlasSet
│
├── scripts/                             ← 新建
│   ├── autoload/                        ← 4 个全局单例 + asset_ids.gd（生成常量类，进 git）
│   │   ├── asset_ids.gd
│   │   ├── sprites.gd
│   │   ├── portraits.gd
│   │   ├── vfx.gd
│   │   └── atlas.gd
│   └── shared/                          ← Resource 子类
│       ├── portrait_set.gd
│       ├── atlas_set.gd
│       └── vfx_clip.gd
│
├── scenes/                              ← 新建（业务 spec 才会用到）
│
├── tests/                               ← 新建（GUT 单测）
│   ├── unit/
│   │   ├── test_manifest.gd
│   │   ├── test_sprites.gd
│   │   ├── test_portraits.gd
│   │   ├── test_vfx.gd
│   │   └── test_atlas.gd
│   └── fixtures/
│
├── addons/                              ← 新建
│   └── gut/                             ← GUT 测试框架（git 提交）
│
├── tools/                               ← 已有
│   ├── ai/                              ← 已有（图像生成相关）
│   └── godot_bake/                      ← 新建
│       ├── manifest.json                ← 全局 manifest（人工维护）
│       ├── bake_all.gd
│       ├── bake_sprites.gd
│       ├── bake_portraits.gd
│       ├── bake_vfx.gd
│       ├── bake_atlas.gd
│       └── bake_asset_ids.gd
│
└── docs/                                ← 已有，不进 Godot import
```

边界规则：

- `assets/art/` 放烤点输入贴图和原始资产；业务代码**不直接 load** 这里（除非另立 spec 明确豁免）。注意：`.tres` 里的 `AtlasTexture` 仍会引用这些贴图，所以参与烤点的图片不能从导出包排除。
- `assets/art/**/raw/`、概念图、参考图、未标准化 `_source` 图默认不进运行时 manifest；如需导入，先复制/整理成标准运行时 sheet。
- `resources/` 只放烤点产物（除 `bake_asset_ids.gd` 输出的 `.gd` 例外，进 `scripts/autoload/`）
- `scripts/generated/` 不存在——常量表直接落进 `scripts/autoload/asset_ids.gd`，避免业务代码额外路径
- `tools/godot_bake/` 不被运行时引用，可在打包时排除

Godot 扫描边界：

仓库根作为 Godot 工程根后，Godot 会扫描 `res://` 下的大部分资源。为避免 `docs/`、AI 输出和第三方大素材包拖慢导入，必须新增 `.gdignore`：

| 路径 | 是否加 `.gdignore` | 理由 |
|---|---:|---|
| `docs/` | ✅ | 文档不进 Godot import |
| `tools/ai/` | ✅ | AI 生成脚本和中间输出不进运行时 |
| `tools/godot_bake/` | ❌ | headless 烤点脚本需要 Godot 识别 |
| `assets/tilesets/kenney/`、`assets/tilesets/opengameart/` | 默认 ✅ | 第三方大素材库暂不整体导入；被选中的素材应复制到 `assets/art/` 或专门 runtime 目录 |
| `assets/art/` | ❌ | 烤点输入贴图需要 Godot import |
| `.godot/` | 不用 `.gdignore`，用 `.gitignore` | 编辑器本地缓存，不进 git |

`.gdignore` 只是阻止 Godot 扫描，不等于 git 忽略；两者要分开维护。

---

## 四、project.godot 关键配置

```ini
[application]
config/name="元生的六年级"
config/features=PackedStringArray("4.6", "GL Compatibility")
run/main_scene=""                                  ← 业务 spec 决定

[autoload]
Sprites="*res://scripts/autoload/sprites.gd"
Portraits="*res://scripts/autoload/portraits.gd"
VFX="*res://scripts/autoload/vfx.gd"
Atlas="*res://scripts/autoload/atlas.gd"

[gui]
theme/custom=""                                    ← UI spec 决定

[rendering]
textures/canvas_textures/default_texture_filter=0  ← Nearest（像素风必需）
```

`*` 前缀表示作为 singleton 全局可见。

---

## 五、manifest.json 格式

`tools/godot_bake/manifest.json` 是**手工维护**的全局清单。烤点的所有输入都在这一份文件里。

格式按烤点类型分四个顶层 section：`sprites` / `portraits` / `vfx` / `atlas`。

### 5.1 完整示例

```json
{
  "version": 1,

  "sprites": {
    "yuansheng": {
      "sheet": "res://assets/art/characters/yuansheng/walk/char_yuansheng_walksheet.png",
      "tile_w": 32,
      "tile_h": 32,
      "rows": 4,
      "cols": 4,
      "animations": {
        "walk_down":  { "row": 0, "frames": [0, 1, 2, 3], "fps": 6, "loop": true, "idle_frame": 0 },
        "walk_left":  { "row": 1, "frames": [0, 1, 2, 3], "fps": 6, "loop": true, "idle_frame": 0 },
        "walk_right": { "row": 2, "frames": [0, 1, 2, 3], "fps": 6, "loop": true, "idle_frame": 0 },
        "walk_up":    { "row": 3, "frames": [0, 1, 2, 3], "fps": 6, "loop": true, "idle_frame": 0 }
      }
    }
  },

  "portraits": {
    "yuansheng": {
      "sheet": "res://assets/art/characters/yuansheng/portrait/char_yuansheng_portrait_sheet.png",
      "slice_mode": "regions",
      "regions": {
        "neutral_rect": [0, 0, 421, 424],
        "tense_rect": [421, 0, 421, 424],
        "smile_rect": [842, 0, 422, 424],
        "blush_rect": [0, 424, 421, 424],
        "down_rect": [421, 424, 421, 424],
        "shocked_rect": [842, 424, 422, 424]
      },
      "expressions": {
        "neutral": { "region": "neutral_rect" },
        "tense":   { "region": "tense_rect" },
        "smile":   { "region": "smile_rect" },
        "blush":   { "region": "blush_rect" },
        "down":    { "region": "down_rect" },
        "shocked": { "region": "shocked_rect" }
      }
    }
  },

  "vfx": {
    "push_dust": {
      "sheet": "res://assets/art/characters/yuansheng/battle/effects/char_yuansheng_fx_push_dust.png",
      "rows": 1, "cols": 1,
      "tile_w": 96, "tile_h": 96,
      "frames": [0],
      "preset": {
        "scale_from": [0.3, 0.3], "scale_to": [1.2, 1.0], "scale_dur": 0.15,
        "alpha_from": 0.9, "alpha_to": 0.0, "alpha_dur": 0.35,
        "offset": [8, -4]
      }
    }
  },

  "atlas": {
    "props_p0": {
      "sheet": "res://assets/art/props/p0/props_p0_core_icons_sheet.png",
      "slice_mode": "regions",
      "regions": {
        "lunchbox_rect": [0, 0, 421, 424],
        "spicy_strip_rect": [421, 0, 421, 424],
        "pop_candy_rect": [842, 0, 422, 424],
        "coin_50_rect": [0, 424, 421, 424],
        "yoyo_rect": [421, 424, 421, 424],
        "tab_book_rect": [842, 424, 422, 424]
      },
      "items": {
        "lunchbox":    { "region": "lunchbox_rect" },
        "spicy_strip": { "region": "spicy_strip_rect" },
        "pop_candy":   { "region": "pop_candy_rect" },
        "coin_50":     { "region": "coin_50_rect" },
        "yoyo":        { "region": "yoyo_rect" },
        "tab_book":    { "region": "tab_book_rect" }
      }
    }
  }
}
```

### 5.2 字段约定

### 5.2.1 regions 模式示例

用于尺寸不规整的 AI sheet，例如 `1264x848` 的 2×3 肖像表。不要写 `tile_w=421` 这种会产生 `421×3=1263` 的近似值；直接写显式矩形：

```json
{
  "portraits": {
    "yuansheng": {
      "sheet": "res://assets/art/characters/yuansheng/portrait/char_yuansheng_portrait_sheet.png",
      "slice_mode": "regions",
      "regions": {
        "neutral_rect": [0, 0, 421, 424],
        "tense_rect": [421, 0, 421, 424],
        "smile_rect": [842, 0, 422, 424],
        "blush_rect": [0, 424, 421, 424],
        "down_rect": [421, 424, 421, 424],
        "shocked_rect": [842, 424, 422, 424]
      },
      "expressions": {
        "neutral": { "region": "neutral_rect" },
        "tense": { "region": "tense_rect" },
        "smile": { "region": "smile_rect" },
        "blush": { "region": "blush_rect" },
        "down": { "region": "down_rect" },
        "shocked": { "region": "shocked_rect" }
      }
    }
  }
}
```

`regions` 模式仍要校验每个矩形在 sheet 范围内，且 `w/h > 0`。矩形之间是否允许重叠由条目类型决定：portraits/atlas 默认不允许重叠；vfx 可以允许重叠但必须显式写 `allow_overlap: true`。


通用字段（4 个 section 都有）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `sheet` | string | `res://` 路径，必须存在；jpg 或 png |
| `slice_mode` | string | `grid` 或 `regions`；未写时默认 `grid` |
| `rows` | int | `grid` 模式必填：sheet 行数 |
| `cols` | int | `grid` 模式必填：sheet 列数 |
| `tile_w` | int | `grid` 模式必填：单格逻辑宽度（像素），必须满足 `cols × tile_w == sheet.width` |
| `tile_h` | int | `grid` 模式必填：单格逻辑高度（像素），必须满足 `rows × tile_h == sheet.height` |
| `regions` | object | `regions` 模式必填：命名矩形，值为 `[x, y, w, h]` |

#### grid vs regions

- `grid`：用于已经标准化的行走表、特效表、图标表。要求整张图尺寸可被行列严格整除，失败就跳过该条。
- `regions`：用于 AI 输出的非整除 sheet、肖像表、特殊 UI。每个子项显式引用一个命名矩形，不要求整图尺寸整除。

原则：正式可复用资产优先整理成 `grid`；短期必须接入但尺寸不规整的图才用 `regions`。`regions` 是兼容手段，不是放弃资产标准化。

`sprites` 专属：

| 字段 | 类型 | 说明 |
|---|---|---|
| `animations` | object | 多 animation 字典，key 是 animation 名 |
| `animations.<name>.row` | int | 该动画占哪一行 |
| `animations.<name>.frames` | int[] | 列号数组，决定播放顺序 |
| `animations.<name>.fps` | int | 帧率 |
| `animations.<name>.loop` | bool | 是否循环 |
| `animations.<name>.idle_frame` | int | 静止帧的列号（用于角色原地停留） |

`portraits` / `atlas` 专属：

| 字段 | 类型 | 说明 |
|---|---|---|
| `expressions` / `items` | object | 子项字典。`grid` 模式下每项 `{row, col}`；`regions` 模式下每项 `{region: "name"}` 或直接 `{rect: [x, y, w, h]}` |

`vfx` 专属：

| 字段 | 类型 | 说明 |
|---|---|---|
| `frames` | int[] 或 string[] | `grid` 模式用一维序号数组（按行优先编号）；`regions` 模式用 region 名数组 |
| `preset.scale_from` / `scale_to` | [float, float] | tween 起止 scale |
| `preset.scale_dur` | float | scale tween 时长（秒） |
| `preset.alpha_from` / `alpha_to` | float | tween 起止透明度 |
| `preset.alpha_dur` | float | alpha tween 时长（秒） |
| `preset.offset` | [float, float] | 相对 spawn 点的位移 |

### 5.3 命名 key 规范

- 所有 key 走小写英文 + 下划线（`pop_candy`、`walk_left`）
- 角色 id 与 `assets/art/characters/<id>/` 目录名严格一致
- 表情 key 与对话肖像 spec 中的英文表情名对齐（`neutral` / `tense` / `smile` 等）
- 道具 key 写最直接的英文翻译（`lunchbox`、`yoyo`），与剧本道具表的内部 id 对齐
- VFX key 与战斗特效 spec 中的英文名对齐（`push_dust` / `punch_arc` / `hurt_stars` 等）

不允许中文/拼音混用 key。中文留在 manifest 注释或文档里。

### 5.4 `version` 字段

`"version": 1` 永久写在顶层。将来格式破坏性变更时，烤点脚本会拒绝低版本 manifest 并提示迁移路径。当前 v1 不需要兼容历史。

---

## 六、烤点脚本

全部用 GDScript，从命令行 headless 跑：

```bash
godot --headless --script tools/godot_bake/bake_all.gd
```

### 6.1 5 个烤点脚本职责

| 脚本 | 输入 | 输出 |
|---|---|---|
| `bake_sprites.gd` | manifest.sprites | `resources/sprite_frames/<id>.tres` |
| `bake_portraits.gd` | manifest.portraits | `resources/portraits/<id>.tres` |
| `bake_vfx.gd` | manifest.vfx | `resources/vfx/<name>.tres` |
| `bake_atlas.gd` | manifest.atlas | `resources/atlas/<category>.tres` |
| `bake_asset_ids.gd` | 全部 manifest section | `scripts/autoload/asset_ids.gd` |
| `bake_all.gd` | — | 顺序调用上面 5 个 |

### 6.2 共用流程

每个烤点脚本固定走这 6 步：

1. **读 manifest**：`JSON.parse_string(FileAccess.get_file_as_string("res://tools/godot_bake/manifest.json"))`
2. **校验**：sheet 文件存在；`grid` 模式校验 `tile_w * cols == sheet.width`、`tile_h * rows == sheet.height`；`regions` 模式校验每个矩形在 sheet 范围内
3. **切片**：创建 `AtlasTexture`。`grid` 模式按 `Rect2(col * tile_w, row * tile_h, tile_w, tile_h)`；`regions` 模式按 manifest 的 `[x, y, w, h]`
4. **组装**：把 AtlasTexture 塞进 SpriteFrames / PortraitSet / VfxClip / AtlasSet
5. **保存**：`ResourceSaver.save(resource, "res://resources/.../id.tres")`
6. **报告**：每条目打印一行 `[OK]` 或 `[ERR]`，最后汇总

### 6.3 sheet 尺寸与 region 硬校验

烤点必做的校验，不可关闭。`grid` 模式校验整图尺寸：

```gdscript
var img := load(entry.sheet) as Texture2D
var actual_w := img.get_width()
var actual_h := img.get_height()
var expected_w := entry.tile_w * entry.cols
var expected_h := entry.tile_h * entry.rows
if actual_w != expected_w or actual_h != expected_h:
    push_error("[ERR] %s: sheet %dx%d but manifest expects %dx%d (tile %dx%d × %d×%d)" %
        [entry_id, actual_w, actual_h, expected_w, expected_h,
         entry.tile_w, entry.tile_h, entry.cols, entry.rows])
    skipped += 1
    continue
```

`regions` 模式校验每个矩形：

```gdscript
var rect := Rect2i(x, y, w, h)
var sheet_rect := Rect2i(0, 0, actual_w, actual_h)
if w <= 0 or h <= 0 or not sheet_rect.encloses(rect):
    push_error("[ERR] %s: region %s out of sheet bounds" % [entry_id, region_name])
    skipped += 1
    continue
```

校验失败 → 跳过该条目、不写 .tres、错误信息记入退出报告。

### 6.4 错误处理

| 错误 | 行为 | 退出码影响 |
|---|---|---|
| manifest.json 解析失败 | 立即终止，不写任何产物 | 退出码 2 |
| 单条 sheet 不存在/损坏 | 跳过该条目，继续其他 | 退出码 1 |
| 单条 tile_w/tile_h 不匹配 | 跳过该条目，继续其他 | 退出码 1 |
| ResourceSaver.save 失败 | 跳过该条目，继续其他 | 退出码 1 |
| 全部成功 | — | 退出码 0 |

退出码：
- 0：全部成功
- 1：部分跳过（manifest 中有问题条目，但其他条目已落盘）
- 2：致命（manifest 自身或 IO 错误，无任何产物）

### 6.5 三个 Resource 子类（`scripts/shared/`）

manifest 里 portraits / vfx / atlas 三类需要 Resource 子类承载烤点产物。

```gdscript
# scripts/shared/portrait_set.gd
class_name PortraitSet
extends Resource

@export var character_id: String = ""
@export var expressions: Dictionary = {}  # { "neutral": Texture2D, "smile": Texture2D, ... }
```

```gdscript
# scripts/shared/atlas_set.gd
class_name AtlasSet
extends Resource

@export var category: String = ""
@export var items: Dictionary = {}  # { "lunchbox": Texture2D, ... }
```

```gdscript
# scripts/shared/vfx_clip.gd
class_name VfxClip
extends Resource

@export var name: String = ""
@export var frames: SpriteFrames                 # 单 anim 名 "default"
@export var scale_from: Vector2 = Vector2.ONE
@export var scale_to: Vector2 = Vector2.ONE
@export var scale_dur: float = 0.0
@export var alpha_from: float = 1.0
@export var alpha_to: float = 0.0
@export var alpha_dur: float = 0.0
@export var offset: Vector2 = Vector2.ZERO
```

每个都是纯数据 Resource，烤点脚本填字段、`ResourceSaver.save()` 落盘。

### 6.6 asset_ids.gd 生成示例

烤点产物 `scripts/autoload/asset_ids.gd`：

```gdscript
# AUTO-GENERATED by tools/godot_bake/bake_asset_ids.gd. DO NOT EDIT.
# Last bake: 2026-05-29 12:34:56

class_name AssetIds
extends Object

class Sprites:
    const YUANSHENG := "yuansheng"
    const BAOXIANJIN := "baoxianjin"
    # ...

class Portraits:
    class Yuansheng:
        const NEUTRAL := "neutral"
        const TENSE := "tense"
        const SMILE := "smile"
        const BLUSH := "blush"
        const DOWN := "down"
        const SHOCKED := "shocked"
    class Baoxianjin:
        const SERIOUS := "serious"
        # ...

class Vfx:
    const PUSH_DUST := "push_dust"
    const PUNCH_ARC := "punch_arc"
    const HURT_STARS := "hurt_stars"
    # ...

class Atlas:
    class PropsP0:
        const LUNCHBOX := "lunchbox"
        const SPICY_STRIP := "spicy_strip"
        const POP_CANDY := "pop_candy"
        # ...
```

调用方式：

```gdscript
$AnimSprite.sprite_frames = Sprites.walk_frames(AssetIds.Char.YUANSHENG)
$Portrait.texture = Portraits.get_expression(AssetIds.Char.YUANSHENG, AssetIds.Portrait.Yuansheng.SMILE)
VFX.spawn(AssetIds.Vfx.PUSH_DUST, position)
$Icon.texture = Atlas.get_item("props_p0", AssetIds.Item.PropsP0.LUNCHBOX)
```

拼错 → IDE 红线 + 编辑器加载失败。

---

## 七、4 个 Autoload Helper + AssetIds

每个 helper 都是薄包装：内部只做 `load()` + 缓存，不做切片。

### 7.1 Sprites

```gdscript
# scripts/autoload/sprites.gd
extends Node

var _cache: Dictionary = {}

func walk_frames(character_id: String) -> SpriteFrames:
    if character_id in _cache:
        return _cache[character_id]
    var path := "res://resources/sprite_frames/%s.tres" % character_id
    assert(ResourceLoader.exists(path), "Missing SpriteFrames: %s" % path)
    var res := load(path) as SpriteFrames
    assert(res != null, "Invalid SpriteFrames: %s" % path)
    _cache[character_id] = res
    return res
```

调用：`Sprites.walk_frames(AssetIds.Char.YUANSHENG)`

后续角色加 battle 动画时，同一个 `.tres` 里多挂 `battle_idle` / `battle_punch` 等 animation 即可。`AnimatedSprite2D.play("battle_idle")` 直接切，不需要 helper 新方法。

### 7.2 Portraits

```gdscript
# scripts/autoload/portraits.gd
extends Node

var _cache: Dictionary = {}

func get_expression(character_id: String, expression: String) -> Texture2D:
    var set := _get_set(character_id)
    assert(set.expressions.has(expression), "Missing portrait expression: %s/%s" % [character_id, expression])
    return set.expressions[expression]

func get_set(character_id: String) -> PortraitSet:
    return _get_set(character_id)

func _get_set(character_id: String) -> PortraitSet:
    if character_id not in _cache:
        var path := "res://resources/portraits/%s.tres" % character_id
        assert(ResourceLoader.exists(path), "Missing PortraitSet: %s" % path)
        var res := load(path) as PortraitSet
        assert(res != null, "Invalid PortraitSet: %s" % path)
        _cache[character_id] = res
    return _cache[character_id]
```

### 7.3 VFX

```gdscript
# scripts/autoload/vfx.gd
extends Node

var _cache: Dictionary = {}

func spawn(vfx_name: String, pos: Vector2, direction: float = 1.0) -> AnimatedSprite2D:
    var clip := _load_clip(vfx_name)
    var sprite := AnimatedSprite2D.new()
    sprite.sprite_frames = clip.frames
    sprite.global_position = pos + Vector2(clip.offset.x * direction, clip.offset.y)
    sprite.scale = clip.scale_from
    if direction < 0:
        sprite.flip_h = true
    get_tree().current_scene.add_child(sprite)
    sprite.play("default")

    var tween := sprite.create_tween()
    tween.tween_property(sprite, "scale", clip.scale_to, clip.scale_dur).set_ease(Tween.EASE_OUT)
    tween.parallel().tween_property(sprite, "modulate:a", clip.alpha_to, clip.alpha_dur).from(clip.alpha_from)
    tween.tween_callback(sprite.queue_free)
    return sprite

func _load_clip(vfx_name: String) -> VfxClip:
    if vfx_name not in _cache:
        var path := "res://resources/vfx/%s.tres" % vfx_name
        assert(ResourceLoader.exists(path), "Missing VfxClip: %s" % path)
        var res := load(path) as VfxClip
        assert(res != null, "Invalid VfxClip: %s" % path)
        _cache[vfx_name] = res
    return _cache[vfx_name]
```

VFX 是唯一"做事"的 helper（创建节点 + tween）。`spawn()` 返回创建的节点，调用方需要时可以接管（比如用于持续生成的 slide_dust）。

### 7.4 Atlas

```gdscript
# scripts/autoload/atlas.gd
extends Node

var _cache: Dictionary = {}

func get_item(category: String, item_name: String) -> Texture2D:
    if category not in _cache:
        var path := "res://resources/atlas/%s.tres" % category
        assert(ResourceLoader.exists(path), "Missing AtlasSet: %s" % path)
        var res := load(path) as AtlasSet
        assert(res != null, "Invalid AtlasSet: %s" % path)
        _cache[category] = res
    var set: AtlasSet = _cache[category]
    assert(set.items.has(item_name), "Missing atlas item: %s/%s" % [category, item_name])
    return set.items[item_name]
```

### 7.5 AssetIds

`AssetIds` 不是 autoload singleton，而是烤点生成的纯常量类：`class_name AssetIds extends RefCounted`。Godot 的 autoload 更适合 `Node` 脚本；把 `AssetIds` 注册成 autoload 会引入不必要的实例语义，也可能和 `extends Object` 不匹配。业务代码直接通过全局类名访问 `AssetIds.Char.YUANSHENG`。

**内部类命名（避免与 autoload 名冲突）**：autoload 用 `Sprites/Portraits/VFX/Atlas`，AssetIds 内部嵌套类用单数 `Char/Portrait/Vfx/Item`。这是 GDScript 限制——同名 `class_name`-嵌套类与 autoload singleton 撞名会触发 "Class X hides an autoload singleton" parse error。

### 7.6 helper 设计原则

- helper 不 fallback：资源缺失或 key 不存在必须立即 `assert(false, message)` 或 `push_error(message); return null`。不要只依赖调用方下一行 NPE。
- 缓存用 Dictionary，进程级，不主动清理。资产量级（< 100 MB）不需要 LRU。
- 不提供 `clear_cache()` 公开 API。

---

## 八、数据流与生命周期

### 8.0 当前仓库迁移步骤

现有仓库的美术资产还不是完全按运行时目录摆放，实施 Godot 骨架前先做一次轻量迁移：

1. 为每个要接入运行时的角色建立标准目录：`assets/art/characters/<id>/walk/`、`portrait/`、`battle/...`。
2. 从 `raw/` 或角色目录根部挑选当前可用 sheet，复制/重命名为不带 `_vN` 的运行时输入名，例如 `char_baoxianjin_walksheet.png`。
3. `_source.png`、概念图、参考稿继续保留原位或 `raw/`，默认不写入 manifest。
4. 对尺寸不整除的肖像/图标表，优先另存标准化 sheet；短期无法标准化时用 `slice_mode: "regions"`。
5. 只把 manifest 指向“运行时输入图”，不要直接指向待验图、实验图、`tools/ai/out/` 或第三方素材大包。
6. 每次迁移一个资产小批次，跑 `bake_all.gd`，确认 `.tres` diff 合理后再提交。

### 8.1 开发期数据流（添加新资产的完整步骤）

```
1. 美术：在 assets/art/ 加新 sheet
       例：assets/art/characters/baoxianjin/walk/char_baoxianjin_walksheet.png

2. 人工：在 manifest.json 加一段
       "sprites": { "baoxianjin": { sheet, rows, cols, tile_w, tile_h, animations } }

3. 跑烤点：godot --headless --script tools/godot_bake/bake_all.gd
       输出：resources/sprite_frames/baoxianjin.tres
            scripts/autoload/asset_ids.gd 多一行 BAOXIANJIN := "baoxianjin"

4. git add → commit → push
       .tres 和 asset_ids.gd 一并进 git

5. 业务代码：Sprites.walk_frames(AssetIds.Char.BAOXIANJIN)  ← 直接可用
```

第 3 步以后**不再修改任何代码**。

### 8.2 运行时数据流

```
游戏代码 Sprites.walk_frames("yuansheng")
   ↓
autoload Sprites 内 _cache 查表
   ├─ 命中 → 返回缓存的 SpriteFrames
   └─ 未命中 → load("res://resources/sprite_frames/yuansheng.tres")
                ↓
                Godot ResourceLoader（.import 缓存）
                ↓
                返回 SpriteFrames，挂入 _cache
```

第一次访问 ≈ 几毫秒，之后全 hit cache。

### 8.3 git 策略

| 产物 | 进 git | 理由 |
|---|---|---|
| `manifest.json` | ✅ | 输入数据，必须版本化 |
| `resources/**/*.tres` | ✅ | 决定性产出，跨机器一致 |
| `scripts/autoload/asset_ids.gd` | ✅ | 生成常量类，IDE 自动补全依赖 |
| `tools/godot_bake/*.gd` | ✅ | 烤点脚本本身 |
| `assets/art/**/*.import` | ✅ | Godot 资源数据库 |
| `.godot/` | ❌ | Godot 编辑器本地缓存（写入 .gitignore） |

### 8.4 缓存生命周期

- 进程启动 → 退出：缓存累积，进程结束自动释放
- 场景切换：缓存保留（角色 sheet 跨场景共用）
- Godot 编辑器热重载：autoload 重建，缓存清空

### 8.5 错误传导

| 错误 | 谁发现 | 行为 |
|---|---|---|
| manifest.json 解析失败 | 烤点脚本 | 退出码 2，红色 ERR，无产物 |
| sheet 文件不存在 | 烤点脚本 | 该条目跳过，红色 ERR，其他条目继续 |
| sheet 尺寸不匹配 manifest | 烤点脚本 | 同上 |
| .tres 不存在（运行时调用） | helper | `assert(ResourceLoader.exists(path), message)`，开发期直接暴露 |
| .tres 损坏 | helper | `load()` 后检查类型，不匹配则 `assert(false, message)` |
| 表情/道具 key 拼错 | helper | 先 `dict.has(key)`，失败则 `assert(false, message)` |

---

## 九、单元测试

用 GUT（Gota's Unit Testing）作为测试框架，提交到 `addons/gut/` 与代码同 git。

### 9.1 测试覆盖

| 测试文件 | 验证 |
|---|---|
| `tests/unit/test_manifest.gd` | manifest.json 解析；版本号；每个条目字段完整；sheet 路径有效 |
| `tests/unit/test_sprites.gd` | `Sprites.walk_frames()` 命中 yuansheng.tres；返回 SpriteFrames 含 4 个 animation |
| `tests/unit/test_portraits.gd` | `Portraits.get_expression()` 命中存在表情；不存在表情触发断言 |
| `tests/unit/test_vfx.gd` | `VFX.spawn()` 创建 AnimatedSprite2D；tween 参数与 manifest 一致 |
| `tests/unit/test_atlas.gd` | `Atlas.get_item()` 命中存在 item；不存在 item 触发断言 |

### 9.2 测试 fixture

`tests/fixtures/` 放最小测试用 sheet（例如 4×4 的 32px 灰色棋盘格 + 一个迷你 manifest 子集），不依赖正式资产。这样：

- 测试与正式资产解耦
- 正式 manifest 改动不破坏测试
- CI 跑测试不需要等正式资产 ready

### 9.3 运行方式

```bash
godot --headless --path . --script addons/gut/gut_cmdln.gd -gdir=res://tests/unit -gexit
```

退出码 0 = 全部通过。

---

## 十、范围与排除

本 spec **包含**：

- Godot 工程目录结构与命名
- `project.godot` 配置（autoload、渲染、应用名）
- `manifest.json` 格式（4 个 section + 字段约定）
- 5 个烤点脚本（sprites/portraits/vfx/atlas/asset_ids）的输入输出契约与错误处理
- 3 个 Resource 子类（PortraitSet/AtlasSet/VfxClip）的字段定义
- 4 个 Autoload Helper 的接口与实现，以及 `AssetIds` 生成常量类
- GUT 单测的覆盖面与 fixture 策略

本 spec **不包含**（各自独立 spec）：

- 角色控制器（移动、跳跃、动画状态机）
- 对话系统（对白显示、选项分支、肖像切换）
- 存档系统
- 场景切换
- 战斗系统循环（HP/勇气槽/技能/AI）
- UI 主题与字体
- 数据驱动表（对白、NPC、道具、属性）
- 音频管线

---

## 十一、待用户确认的问题

无。本 spec 的关键决策已确定：Godot 4.6、薄 helper + 厚资源 + manifest 驱动 + 烤点产物进 git、仓库根 = 工程根、4 autoload helper、AssetIds 生成常量类、多尺寸并存、英文 key、嵌套 AssetIds、GUT 单测。

