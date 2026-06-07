"""
VFX (视觉特效) 数据模型。

支持 sprite sheet 格式的特效动画：fireball, slash, heal, explosion 等。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class BlendMode(str, Enum):
    """混合模式。"""
    NORMAL = "normal"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"


class VFXAnchor(str, Enum):
    """特效锚点。"""
    CENTER = "center"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"
    FEET_CENTER = "feet_center"


class VFXCategory(str, Enum):
    """特效类别。"""
    COMBAT = "combat"
    MAGIC = "magic"
    ENVIRONMENT = "environment"
    AMBIENT = "ambient"
    INTERACTION = "interaction"


@dataclass
class VFXGenerationInfo:
    """生成元信息。"""
    timestamp: str
    generator: str
    prompt: str
    seed: int
    model: str


@dataclass
class VFXMetadata:
    """
    特效 sprite sheet metadata。

    Attributes:
        asset_id: 唯一标识，如 'fireball_small_01'
        image: sprite sheet PNG 路径
        frame_size: 单帧尺寸 [width, height]
        frames: 总帧数
        fps: 播放帧率
        loop: 是否循环
        blend: 混合模式
        anchor: 锚点
        category: 类别
        tags: 标签
        scale_range: 缩放范围 [min, max]
        generated: 生成元信息
    """
    asset_id: str
    image: str
    frame_size: tuple[int, int]
    frames: int
    fps: int
    loop: bool
    blend: BlendMode = BlendMode.NORMAL
    anchor: VFXAnchor = VFXAnchor.CENTER
    category: VFXCategory = VFXCategory.COMBAT
    tags: list[str] = field(default_factory=list)
    scale_range: tuple[float, float] | None = None
    generated: VFXGenerationInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "asset_id": self.asset_id,
            "image": self.image,
            "frame_size": list(self.frame_size),
            "frames": self.frames,
            "fps": self.fps,
            "loop": self.loop,
            "blend": self.blend.value,
            "anchor": self.anchor.value,
            "category": self.category.value,
        }
        if self.tags:
            result["tags"] = self.tags
        if self.scale_range:
            result["scale_range"] = list(self.scale_range)
        if self.generated:
            result["generated"] = {
                "timestamp": self.generated.timestamp,
                "generator": self.generated.generator,
                "prompt": self.generated.prompt,
                "seed": self.generated.seed,
                "model": self.generated.model,
            }
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VFXMetadata:
        kwargs: dict[str, Any] = {
            "asset_id": data["asset_id"],
            "image": data["image"],
            "frame_size": tuple(data["frame_size"]),
            "frames": data["frames"],
            "fps": data["fps"],
            "loop": data["loop"],
            "blend": BlendMode(data.get("blend", "normal")),
            "anchor": VFXAnchor(data.get("anchor", "center")),
            "category": VFXCategory(data.get("category", "combat")),
        }
        if "tags" in data:
            kwargs["tags"] = data["tags"]
        if "scale_range" in data:
            kwargs["scale_range"] = tuple(data["scale_range"])
        if "generated" in data:
            g = data["generated"]
            kwargs["generated"] = VFXGenerationInfo(
                timestamp=g["timestamp"],
                generator=g["generator"],
                prompt=g["prompt"],
                seed=g["seed"],
                model=g["model"],
            )
        return cls(**kwargs)
