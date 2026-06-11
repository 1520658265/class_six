# AI 生成工具

## 目录

- `prompts/` — AI prompt 源文件（按资产类型分中文目录）
  - `_archive/` — 2026-05-25 之前的英文版本，仅作参考
- `gen_with_gemini.py` — 调 Gemini 生成图片，含重试逻辑
- `pixellab_v2_client.py` — PixelLab v2 API 客户端，供 `asset_general_system` 的 tilemap 流程调用
- `jpg_to_png_alpha.py` — 把洋红背景、白/浅灰格子底和横竖格线残留转为 PNG alpha；详细说明见 `docs/reference/jpg_to_png_alpha.md`
- `check_grid.py` — 给 sprite sheet 叠加等分网格，辅助人工验收切片边界
- `postprocess.py` — 洋红抠图和网格切片的轻量后处理工具
- `audit_art.py` — 基础美术资产检查脚本
- `batch_jpg_to_png_alpha.py`、`resize_sprite.py` — 历史资产批处理辅助工具

## 使用

prompt 文件用中文命名，方便和《美术资产清单-spec.md》、剧情/资产清单对应。
工程归档资产使用英文 ID（避免 Godot 导入和跨平台路径问题）。

## 本地配置

图片生成脚本从 `tools/ai/config.local.json` 读取密钥。该文件已被 `.gitignore` 排除，不应提交到 git。

首次配置时复制 `tools/ai/config.example.json` 为 `tools/ai/config.local.json`，再填写各服务的 `api_key`。也可以用环境变量覆盖：

- `GEMINI_IMAGE_API_KEY`
- `PIXELLAB_TOKEN`

## 常用命令

Gemini 图片生成：

```powershell
python tools/ai/gen_with_gemini.py prompts/<prompt>.txt --aspect 1:1 --size 1K -o tools/ai/out/<name>
```

透明化与网格检查：

```powershell
python tools/ai/jpg_to_png_alpha.py <input.jpg> -o <output.png>
python tools/ai/check_grid.py <sheet.png> <rows> <cols>
```

PixelLab tilemap 生成由 `asset_general_system/generate.py scene-tileset-generate --pixellab` 调用；真实 API 需要先设置 `PIXELLAB_TOKEN`，并显式传入 `--run-api`。

```powershell
python -B asset_general_system/generate.py scene-tileset-generate <scene_dir> --pixellab --run-api
```
