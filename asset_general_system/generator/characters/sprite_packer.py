"""
Sprite Sheet 打包工具。

把多张单帧图打包成一张 sprite sheet PNG，并生成 metadata。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..models.sprite_sheet import (
    AnimationClip,
    CharacterAnchor,
    Direction,
    HitBox,
    SpriteSheetMetadata,
)


class SpriteSheetPacker:
    """
    Sprite sheet 打包器。

    布局规则：每个动作和方向组合占一行，行顺序由传入的帧字典决定。
    """

    def __init__(
        self,
        frame_size: tuple[int, int] = (32, 48),
    ):
        """
        Args:
            frame_size: 单帧尺寸 [width, height]
        """
        self.frame_size = frame_size

    def pack_frames(
        self,
        frames_by_animation: dict[str, list],
        output_path: Path,
        default_fps: int | None = None,
        fps_overrides: dict[str, int] | None = None,
    ) -> dict[str, AnimationClip]:
        """
        把帧序列打包成 sprite sheet。

        Args:
            frames_by_animation: 每个动画的帧列表，例如:
                {
                    "walk_down": [PIL.Image, PIL.Image, ...],
                    "idle_down": [PIL.Image, ...],
                }
            output_path: 输出 PNG 路径
            default_fps: 所有动画统一使用的 fps；为空时根据动作名推断
            fps_overrides: 单个动画名到 fps 的覆盖

        Returns:
            动画名到 AnimationClip 的映射
        """
        try:
            from PIL import Image
        except ImportError:
            raise RuntimeError("PIL 不可用")

        if not frames_by_animation:
            raise ValueError("frames_by_animation 不能为空")

        fw, fh = self.frame_size

        # 按动画顺序组织行
        animation_names = list(frames_by_animation.keys())
        max_frames = max(len(frames) for frames in frames_by_animation.values())

        sheet_width = fw * max_frames
        sheet_height = fh * len(animation_names)

        sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

        animations: dict[str, AnimationClip] = {}

        for row, anim_name in enumerate(animation_names):
            frames = frames_by_animation[anim_name]
            for col, frame in enumerate(frames):
                # 缩放到 frame_size
                if frame.size != (fw, fh):
                    frame = frame.resize((fw, fh), Image.NEAREST)
                sheet.paste(frame, (col * fw, row * fh), frame if frame.mode == "RGBA" else None)

            # 推断 fps 和 loop
            fps = (fps_overrides or {}).get(anim_name)
            if fps is None:
                fps = default_fps if default_fps is not None else self._infer_fps(anim_name, len(frames))
            loop = self._infer_loop(anim_name)
            direction = self._infer_direction(anim_name)

            animations[anim_name] = AnimationClip(
                row=row,
                frames=len(frames),
                fps=fps,
                loop=loop,
                direction=direction,
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(output_path, "PNG")

        return animations

    def _infer_fps(self, anim_name: str, frame_count: int) -> int:
        """根据动作名推断 fps。"""
        name_lower = anim_name.lower()
        if "idle" in name_lower:
            return 4
        if "walk" in name_lower:
            return 8
        if "run" in name_lower:
            return 12
        if "attack" in name_lower or "cast" in name_lower:
            return 12
        return 8

    def _infer_loop(self, anim_name: str) -> bool:
        """根据动作名推断是否循环。"""
        name_lower = anim_name.lower()
        if any(k in name_lower for k in ["idle", "walk", "run"]):
            return True
        if any(k in name_lower for k in ["attack", "cast", "hurt", "death"]):
            return False
        return True

    def _infer_direction(self, anim_name: str) -> Direction | None:
        """从动作名提取方向。"""
        name_lower = anim_name.lower()
        directions = sorted(Direction, key=lambda item: len(item.value), reverse=True)
        for direction in directions:
            if name_lower.endswith(f"_{direction.value}") or name_lower == direction.value:
                return direction
        return None

    def build_metadata(
        self,
        asset_id: str,
        image_path: str,
        animations: dict[str, AnimationClip],
        directions: list[Direction] | None = None,
        anchor: CharacterAnchor = CharacterAnchor.FEET_CENTER,
        hitbox: HitBox | None = None,
        tags: list[str] | None = None,
    ) -> SpriteSheetMetadata:
        """
        构建完整 metadata。

        Args:
            asset_id: 角色 ID
            image_path: sprite sheet 路径
            animations: 动画定义
            directions: 支持的方向（默认从 animations 推断）
            anchor: 锚点
            hitbox: 碰撞盒（默认根据 frame_size 推断）
            tags: 标签

        Returns:
            完整的 SpriteSheetMetadata
        """
        if directions is None:
            # 从动画名推断方向
            dirs = set()
            for anim_name in animations.keys():
                name_lower = anim_name.lower()
                sorted_dirs = sorted(Direction, key=lambda item: len(item.value), reverse=True)
                for d in sorted_dirs:
                    if name_lower.endswith(f"_{d.value}") or name_lower == d.value:
                        dirs.add(d)
                        break
            directions = list(dirs) if dirs else [Direction.DOWN]

        if hitbox is None:
            # 默认 hitbox：底部 1/3 区域
            fw, fh = self.frame_size
            hitbox = HitBox(
                x=fw // 4,
                y=fh * 2 // 3,
                width=fw // 2,
                height=fh // 3,
            )

        return SpriteSheetMetadata(
            asset_id=asset_id,
            image=image_path,
            frame_size=self.frame_size,
            directions=directions,
            animations=animations,
            anchor=anchor,
            hitbox=hitbox,
            tags=tags or [],
        )
