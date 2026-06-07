# AI 生成工具

## 目录

- `prompts/` — AI prompt 源文件（按资产类型分中文目录）
  - `_archive/` — 2026-05-25 之前的英文版本，仅作参考
- `out/` — 模型原始输出，按资产类型分类
  - `models_list.json` — 模型列表临时记录
- `_experiments/` — 一次性实验脚本与产物（grass_cliff 切片、road_tileset 自生成）
- `gen_with_gemini.py` — 调 Gemini 生成图片，含重试逻辑
- `gen_with_gpt_image.py` — 调 OpenAI 兼容图像接口（gpt-image-2-pro）
- `gen_with_liblib.py` — 调 LiblibAI 自定义模型（HMAC 签名 + 任务轮询，支持 LoRA / ControlNet / img2img）
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
- `LIBLIB_ACCESS_KEY` / `LIBLIB_SECRET_KEY`（双密钥，覆盖 services.liblib.access_key/secret_key）

## gen_with_liblib.py 用法

文档：[飞书 wiki](https://resonate.feishu.cn/wiki/UAMVw67NcifQHukf8fpccgS5n6d)

最简文生图（需要先在 `config.local.json` 的 `services.liblib` 里填好双密钥和 `checkpoint_id`）：

```powershell
python gen_with_liblib.py prompts/hero01/portrait.txt --width 832 --height 1216 --steps 30 --cfg 7
```

带 LoRA + ControlNet OpenPose 的行走图单帧：

```powershell
python gen_with_liblib.py prompts/hero01/walk.txt `
  --width 512 --height 512 --seed 42 `
  --lora <pixel_lora_uuid>:0.9 `
  --lora <char_hero01_uuid>:0.8 `
  --controlnet-image https://example.com/walk-down-1.png `
  --controlnet-type openpose --controlnet-weight 0.9
```

img2img（提供公网可访问的源图 URL，自动切到 img2img 模式）：

```powershell
python gen_with_liblib.py prompts/hero01/face-icon.txt `
  --source https://example.com/portrait.png --denoise 0.4 `
  --width 256 --height 256
```

`checkpoint_id` 和 LoRA 的 `versionUuid` 在模型详情页 URL 末尾的 `versionUuid=...` 里。`additionalNetwork` 最多 5 条，超出会被截断。任务提交后脚本每 3 秒轮询一次状态，最多等 10 分钟。
