# tools/godot_bake/

把 `assets/art/` 的原始 sheet 烤成 Godot 用的 `.tres` 资源 + 生成 `AssetIds` 常量类。

参考完整 spec：`docs/superpowers/specs/2026-05-29-godot项目骨架-spec.md`

## 加新资产的步骤

1. 把 sheet 放到 `assets/art/...` 下，用规范化文件名（不带 `_v数字`）
2. 在 `tools/godot_bake/manifest.json` 加一段 entry
3. 让 Godot import 新图（编辑器打开一次即可，或 headless：`.\tools\godot.cmd --headless --editor --path . --quit`）
4. 跑烤点：

   ```bash
   .\tools\godot.cmd --headless --path . -s tools/godot_bake/bake_all.gd
   ```

5. 把 `tools/godot_bake/manifest.json`、`resources/**/*.tres`、`scripts/autoload/asset_ids.gd` 一并 commit

第 4 步以后业务代码可以直接用 `Sprites.walk_frames(AssetIds.Sprites.YOUR_NEW_ID)` 引用。

## 退出码

- 0：全部成功
- 1：部分跳过（某些 entry 有问题，但其他已成功落盘）
- 2：致命（manifest.json 解析失败 / 版本不支持）

## manifest.json 字段说明

详见 spec 第五节。简要：

| section | 用途 | 输出资源 |
|---|---|---|
| `sprites` | 角色行走/战斗动画 | SpriteFrames |
| `portraits` | 对话肖像表情贴图 | PortraitSet |
| `vfx` | 战斗特效（含 tween preset） | VfxClip |
| `atlas` | 道具/UI/场景图标贴图 | AtlasSet |

每条 entry 都需要 `sheet` 路径 + 切片信息（`grid` 或 `regions` 模式）。

## 测试 fixture

`tests/fixtures/` 下有一份独立的小 sheet + manifest，用于 baker 端到端 smoke test：

- `tools/godot_bake/_make_test_fixtures.py` — 一次性 PIL 生成器（已运行过；如需重生再跑）
- `tests/fixtures/sheets/*.png` — 灰度棋盘格、纯色方块、矩形分块
- `tests/fixtures/manifest.json` — 覆盖 4 个 section 的最小 manifest

跑 fixture smoke test（手工流程）：

```powershell
Copy-Item tools/godot_bake/manifest.json tools/godot_bake/manifest.json.bak -Force
Copy-Item tests/fixtures/manifest.json tools/godot_bake/manifest.json -Force
.\tools\godot.cmd --headless --path . -s tools/godot_bake/bake_all.gd
Move-Item tools/godot_bake/manifest.json.bak tools/godot_bake/manifest.json -Force
```

## 常见错误

| 现象 | 原因 | 处理 |
|---|---|---|
| `sheet not found` | manifest 路径写错或资产没 import | 跑一次 `--headless --editor --quit` 让 Godot 扫描；或检查 `sheet` 字段是否 `res://` 起始且文件存在 |
| `sheet size mismatch` | `tile_w * cols ≠ sheet.width` | 用 PIL 检查实际尺寸：`python -c "from PIL import Image;print(Image.open('path').size)"`，回头改 `tile_w/tile_h` |
| `region out of bounds` | regions 模式矩形超出 sheet | 检查 `[x,y,w,h]` 是否在 sheet 内 |
| 业务代码报 `Missing SpriteFrames` | 没跑烤点或 entry 没 commit | 跑 `bake_all.gd` 并 commit 产物 |
| `unsupported manifest version` | manifest 顶层 `version` 字段缺失或非 1 | 写入 `"version": 1` |
