# Phase 2 导出与校验基线

更新时间：2026-06-05

## 1. 当前目标

Phase 2 的目标是让地图从“能生成”推进到“能稳定进入工具链”。

本次基线优先完成自动化可验证部分：

- Tiled JSON 结构校验。
- 生成阶段输出 Tiled 校验报告。
- 5 套 Phase 1 demo 重新生成并全部通过地图校验和 Tiled 结构校验。

## 2. 新增能力

新增 `TiledJsonValidator`：

- 文件：`generator/export/tiled_validator.py`
- 校验内容：
  - 顶层 `type == "map"`。
  - `orientation == "orthogonal"`。
  - 必要 tile layer：`terrain`、`path`、`building`、`decoration`、`collision`。
  - 必要 object layer：`objects`、`events`。
  - tile layer 尺寸和 data 长度。
  - gid 非负且不超过 tileset 范围。
  - layer id 和 object id 唯一。
  - tileset 存在，且 image 使用相对路径。
  - `nextlayerid`、`nextobjectid` 合法。
  - collision layer 默认隐藏。

新增 Tiled 本机检测：

- 文件：`generator/export/tiled_runtime.py`
- 命令：

```bash
python -m generator.cli check-tiled
```

当前本机尚未安装 Tiled，命令会返回：

```text
available=False
message=Tiled executable was not found. Install Tiled or pass --tiled-path.
```

安装 Tiled 后可以直接复跑该命令，或显式指定路径：

```bash
python -m generator.cli check-tiled --tiled-path "C:/Program Files/Tiled/tiled.exe"
```

新增标准 demo 批量验证：

```bash
python -m generator.cli verify-tiled-demos --outputs examples/outputs --output examples/outputs/tiled_demo_verification.json
```

默认只验证 5 套标准 Phase 1 demo。如果需要扫描 `examples/outputs` 下所有 `map.tiled.json`，可以加：

```bash
python -m generator.cli verify-tiled-demos --outputs examples/outputs --all
```

## 3. 输出变化

`generate` 命令现在额外输出：

```text
tiled_validation_report.json
```

`generation_report.json` 中的 `validation_passed` 现在需要同时满足：

```text
map validation passed && tiled validation passed
```

`export-tiled` 命令会打印：

```text
tiled_validation_passed=True|False
```

## 4. 当前验证结果

命令：

```bash
pytest -q
python -m generator.demo
```

当前结果：

```text
13 passed
```

5 套标准 demo：

| Demo | 地图校验 | Tiled 结构校验 |
| --- | --- | --- |
| `autumn_village` | passed | passed |
| `dungeon_demo` | passed | passed |
| `snow_camp_demo` | passed | passed |
| `desert_ruins_demo` | passed | passed |
| `seaside_village_demo` | passed | passed |

## 5. 仍需人工验证

当前 `TiledJsonValidator` 是静态结构校验，不等价于真实 Tiled 编辑器打开验证。

当前环境状态：

- 本机未安装 Tiled，真实打开验证暂时不能执行。
- 已提供 `check-tiled` 命令，后续安装后可复测。
- 已提供 `verify-tiled-demos` 命令，当前会生成 `examples/outputs/tiled_demo_verification.json`，其中 `runtime_verification` 为 `skipped_tiled_not_installed`。

下一步建议：

- 安装或定位本机 Tiled 可执行文件。
- 用 Tiled 打开 5 套 `map.tiled.json`。
- 如果 Tiled 报错，把错误写入兼容性测试用例。
- 根据真实报错修正 exporter 字段。
