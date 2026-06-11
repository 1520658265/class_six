# PixelLab Tileset Feasibility

目的：验证 PixelLab.ai v2 `create_tileset` 专用接口是否可以作为 Linsen tilemap 地表/transition tileset 的候选主路径。

当前状态：待验证。用户额度已用完，本目录先准备离线工具，不调用 API。

## 为什么重新验证

前面失败的是普通生图路径：

- Gemini 直接生成 3x3 / 4x4 patch。
- PixelLab `create_pixen` 直接生成 3x3 / 4x4 patch。

失败原因是普通生图模型会画完整场景、重复图块或装饰物，不能稳定遵守 reusable tile grammar。

PixelLab `create_tileset` 是专用 Wang tiles / transition tileset 接口，能力边界不同，值得单独验证。

## 验证集合

见 `cases.json`：

1. `grass_to_dirt_road`
2. `grass_to_plaza`
3. `grass_to_running_track`
4. `grass_to_water`
5. `wheat_to_dirt_road`

## 不消耗额度的命令

```powershell
python asset_general_system\experiments\pixellab_tileset_feasibility\run_pixellab_tileset.py
python asset_general_system\experiments\pixellab_tileset_feasibility\process_tileset_outputs.py
```

这只会生成 pending 报告和 review 页面，不调用 API。

## 额度恢复后的真实验证

```powershell
python asset_general_system\experiments\pixellab_tileset_feasibility\run_pixellab_tileset.py --run-api
python asset_general_system\experiments\pixellab_tileset_feasibility\process_tileset_outputs.py
```

## 产物

- `raw/`：原始 API JSON，git ignored。
- `decoded/`：从 API 返回内容解出的原始 tileset/tile PNG，git ignored。
- `tiles_64/`：放大到 64x64 的 tile PNG，git ignored。
- `previews/`：contact sheet 和示例拼接图，git ignored。
- `reports/`：summary 和 per-case report，git ignored。
- `review.html`：人工 review 页面，git ignored。

## 通过标准

1. 能稳定解码 API 返回内容。
2. 能识别或人工标注每个 tile 的连接签名。
3. 放大到 64x64 后像素风不糊。
4. 示例拼接没有明显断边、黑线、透底或材质跳变。
5. transition 覆盖至少四边、四角和必要的内外角。
6. 不混入建筑、角色、文字、图标或不属于材质的装饰物。
7. review 后的 mapping 能被正式 pack 使用。
