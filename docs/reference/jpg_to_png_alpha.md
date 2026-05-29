# JPG 转透明 PNG 后处理工具

日期：2026-05-28

脚本：`tools/ai/jpg_to_png_alpha.py`

用途：把 AI 生成的、带洋红抠图背景的 JPG 资产转成带 alpha 通道的 PNG。脚本不会缩放、裁切或改变原图分辨率。

## 默认用法

运行：

```powershell
python tools\ai\jpg_to_png_alpha.py input.jpg -o output.png
```

默认使用 `--mode auto`，处理逻辑如下：

- 移除和画布边缘连通的洋红背景。
- 移除 sprite sheet 中被格线隔开的、大块高纯度洋红背景。
- 吸收背景边缘附近的 JPG 弱洋红 halo。
- 移除贴着背景的大块白色/浅灰色格子底。
- 移除检测到的格子边界附近的低饱和横向/竖向格线残留。
- 保留角色或特效内部的小块、低纯度粉色/紫色细节。
- 保持输入图的原始宽高不变。

## 常用参数

```powershell
python tools\ai\jpg_to_png_alpha.py input.jpg -o output.png --grid-cleanup off
```

关闭黑色/灰色格线清理，适合需要更保守输出的素材。

```powershell
python tools\ai\jpg_to_png_alpha.py input.jpg -o output.png --matte-cleanup off
```

关闭白色/浅灰色格子底清理。

```powershell
python tools\ai\jpg_to_png_alpha.py input.jpg -o output.png --mode edge
```

只移除和画布边缘连通的洋红区域。

```powershell
python tools\ai\jpg_to_png_alpha.py input.jpg -o output.png --mode global
```

移除所有洋红候选像素。只有在确认角色/特效本体不包含需要保留的洋红或紫色细节时再使用。

## 验证记录

已用角色行走表、概念图、头像表和 boss 特效表做过抽查。优化后的默认配置可以处理隔开的洋红格子底、白色格子底和横竖格线残留，同时在抽查样本中保留了角色描边和特效主体形状。
