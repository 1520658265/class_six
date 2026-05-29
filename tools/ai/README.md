# AI 生成工具

## 目录

- `prompts/` — AI prompt 源文件（按资产类型分中文目录）
  - `_archive/` — 2026-05-25 之前的英文版本，仅作参考
- `out/` — 模型原始输出，按资产类型分类
  - `models_list.json` — 模型列表临时记录
- `_experiments/` — 一次性实验脚本与产物（grass_cliff 切片、road_tileset 自生成）
- `gen_with_gemini.py` — 调 Gemini 生成图片，含重试逻辑
- `jpg_to_png_alpha.py` — 把洋红背景、白/浅灰格子底和横竖格线残留转为 PNG alpha；详细说明见 `docs/reference/jpg_to_png_alpha.md`

## 使用

prompt 文件用中文命名，方便和《美术资产清单-spec.md》、剧情/资产清单对应。
工程归档资产使用英文 ID（避免 Godot 导入和跨平台路径问题）。

## 本地配置

图片生成脚本从 `tools/ai/config.local.json` 读取密钥。该文件已被 `.gitignore` 排除，不应提交到 git。

首次配置时复制 `tools/ai/config.example.json` 为 `tools/ai/config.local.json`，再填写各服务的 `api_key`。也可以用环境变量覆盖：

- `GEMINI_IMAGE_API_KEY`
- `GPT_IMAGE_API_KEY`
- `ROAD_TILESET_API_KEY`
