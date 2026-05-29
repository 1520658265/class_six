# Class Six

《元生六年级》游戏项目的设定、美术资产和 AI 生成工具仓库。当前仓库重点是故事/设计文档、像素风美术资产归档，以及生成和检查资产用的 Python 脚本。

## 目录

- `docs/`：设计规格、世界观参考和工作日志。
  - `docs/design/`：正式设计/规格文档，文件统一使用 `-spec.md` 后缀。
  - `docs/reference/`：故事线、创作素材和工具说明。
  - `docs/journal/`：按日期记录的工作日志。
- `assets/`：正式归档的美术资产。
  - `assets/art/`：角色、场景、道具、UI、特效等自产美术。
  - `assets/tilesets/`：第三方 tileset 资源，按来源分为 `kenney/`、`opengameart/`、`itch/`。
- `tools/ai/`：AI 生成、透明化、网格检查和资产审计脚本。

## Python 环境

建议在项目根目录创建虚拟环境后安装依赖：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

常用命令：

```bash
python tools/ai/check_grid.py <sheet.png> <rows> <cols>
python tools/ai/jpg_to_png_alpha.py <input.jpg>
python tools/ai/audit_art.py
```

## AI 配置

真实密钥放在 `tools/ai/config.local.json`，该文件已被 `.gitignore` 排除，不要提交到 git。

首次配置：

```bash
copy tools\ai\config.example.json tools\ai\config.local.json
```

然后编辑 `tools/ai/config.local.json`，填入各服务的 `api_key`。也可以用环境变量覆盖，详见 `tools/ai/README.md`。

## 版本管理约定

- 提交正式资产、设计文档、脚本和可共享的示例配置。
- 不提交真实密钥、本机配置、虚拟环境和 Python 缓存。
- AI 原始图按资产目录归档；除非明确需要工程导入版本，不默认切图、压缩或改透明。

