# ControlNet 骨架模板需求

本目录存放行走图和战斗图的 ControlNet 参考骨架图。
骨架图需要手动制作或从现有素材提取，不由 AI 自动生成。

## 行走图骨架（16 张）

| 文件名 | 方向 | 帧 | 姿态描述 |
|---|---|---|---|
| walk-down-1.png | 朝下 | 中立 | 双脚并立，面向镜头 |
| walk-down-2.png | 朝下 | 左脚迈步 | 左脚前伸，重心前移 |
| walk-down-3.png | 朝下 | 中立 | 同 frame1 |
| walk-down-4.png | 朝下 | 右脚迈步 | 右脚前伸，重心前移 |
| walk-left-1~4.png | 朝左 | 同上 | 侧面视角 |
| walk-right-1~4.png | 朝右 | 同上 | 侧面视角（可镜像 left） |
| walk-up-1~4.png | 朝上 | 同上 | 背面视角 |

## 战斗图骨架（57 张）

每个动作的每一帧各需一张骨架图：

| 动作 | 帧数 | 文件名模式 |
|---|---|---|
| idle | 4 | battle-idle-1~4.png |
| walk-in | 4 | battle-walk-in-1~4.png |
| attack | 6 | battle-attack-1~6.png |
| charge | 6 | battle-charge-1~6.png |
| skill | 8 | battle-skill-1~8.png |
| guard | 3 | battle-guard-1~3.png |
| dodge | 4 | battle-dodge-1~4.png |
| hurt | 3 | battle-hurt-1~3.png |
| critical-hurt | 4 | battle-critical-hurt-1~4.png |
| low-hp | 4 | battle-low-hp-1~4.png |
| dead | 5 | battle-dead-1~5.png |
| victory | 6 | battle-victory-1~6.png |

## 制作方式（三选一）

1. **手绘骨架**：用 Aseprite / Piskel 画火柴人骨架，导出 PNG
2. **从现有素材提取**：找一套免费 RPG sprite，用 OpenPose 提取骨架
3. **3D 工具导出**：用 MagicaVoxel / Blender 摆 pose 后渲染为骨架线稿

## 规格要求

- 尺寸：与目标生成尺寸一致（行走 512x512，战斗 768x768）
- 格式：PNG，白底黑线 或 OpenPose 标准彩色关节图
- ControlNet 类型：OpenPose（推荐）或 Canny
- 所有帧的人物位置/大小必须一致（锚点对齐）
