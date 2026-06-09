"""
角色 Sprite Sheet 数据模型。

支持 4 方向 idle/walk 动画，sprite sheet 打包，feet anchor 和 hitbox。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Direction(str, Enum):
    """角色朝向。"""
    DOWN = "down"
<<<<<<< HEAD
    DOWN_LEFT = "down_left"
    DOWN_RIGHT = "down_right"
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    UP_LEFT = "up_left"
    UP_RIGHT = "up_right"
=======
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0


class AnimationName(str, Enum):
    """标准动作名称。"""
    IDLE = "idle"
    WALK = "walk"
    RUN = "run"
    ATTACK = "attack"
    CAST = "cast"
    HURT = "hurt"
    DEATH = "death"


class CharacterAnchor(str, Enum):
    """角色锚点。"""
    FEET_CENTER = "feet_center"
    CENTER = "center"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"


@dataclass
class AnimationClip:
    """单个动画片段定义。"""
    row: int
    frames: int
    fps: int
    loop: bool
    direction: Direction | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {
            "row": self.row,
            "frames": self.frames,
            "fps": self.fps,
            "loop": self.loop,
        }
        if self.direction:
            result["direction"] = self.direction.value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnimationClip:
        kwargs = {
            "row": data["row"],
            "frames": data["frames"],
            "fps": data["fps"],
            "loop": data["loop"],
        }
        if "direction" in data:
            kwargs["direction"] = Direction(data["direction"])
        return cls(**kwargs)


@dataclass
class HitBox:
    """碰撞盒，相对于 frame 左上角。"""
    x: int
    y: int
    width: int
    height: int

    def to_list(self) -> list[int]:
        return [self.x, self.y, self.width, self.height]

    @classmethod
    def from_list(cls, data: list[int]) -> HitBox:
        return cls(x=data[0], y=data[1], width=data[2], height=data[3])


@dataclass
class ShadowSpec:
    """角色阴影定义。"""
    offset: tuple[int, int] = (0, 0)
    radius: int = 8

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset": list(self.offset),
            "radius": self.radius,
        }


@dataclass
class SpriteSheetGenerationInfo:
    """生成元信息。"""
    timestamp: str
    generator: str
    prompt: str
    seed: int
    model: str


@dataclass
class SpriteSheetMetadata:
    """
    完整的角色 sprite sheet metadata。

    Attributes:
        asset_id: 唯一标识，如 'villager_merchant_01'
        image: sprite sheet PNG 相对路径
        frame_size: 单帧尺寸 [width, height]
        directions: 支持的朝向
        animations: 动画定义 dict
        anchor: 视觉锚点
        hitbox: 碰撞盒
        weapon_socket: 武器挂点
        shadow: 阴影定义
        portrait: 立绘路径
        tags: 标签
        generated: 生成信息
    """
    asset_id: str
    image: str
    frame_size: tuple[int, int]
    directions: list[Direction]
    animations: dict[str, AnimationClip]
    anchor: CharacterAnchor = CharacterAnchor.FEET_CENTER
    hitbox: HitBox | None = None
    weapon_socket: tuple[int, int] | None = None
    shadow: ShadowSpec | None = None
    portrait: str | None = None
    tags: list[str] = field(default_factory=list)
    generated: SpriteSheetGenerationInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "asset_id": self.asset_id,
            "image": self.image,
            "frame_size": list(self.frame_size),
            "directions": [d.value for d in self.directions],
            "animations": {name: clip.to_dict() for name, clip in self.animations.items()},
            "anchor": self.anchor.value,
        }
        if self.hitbox:
            result["hitbox"] = self.hitbox.to_list()
        if self.weapon_socket:
            result["weapon_socket"] = list(self.weapon_socket)
        if self.shadow:
            result["shadow"] = self.shadow.to_dict()
        if self.portrait:
            result["portrait"] = self.portrait
        if self.tags:
            result["tags"] = self.tags
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
    def from_dict(cls, data: dict[str, Any]) -> SpriteSheetMetadata:
        animations = {
            name: AnimationClip.from_dict(clip_data)
            for name, clip_data in data["animations"].items()
        }
        kwargs: dict[str, Any] = {
            "asset_id": data["asset_id"],
            "image": data["image"],
            "frame_size": tuple(data["frame_size"]),
            "directions": [Direction(d) for d in data["directions"]],
            "animations": animations,
            "anchor": CharacterAnchor(data.get("anchor", "feet_center")),
        }
        if "hitbox" in data:
            kwargs["hitbox"] = HitBox.from_list(data["hitbox"])
        if "weapon_socket" in data:
            kwargs["weapon_socket"] = tuple(data["weapon_socket"])
        if "shadow" in data:
            s = data["shadow"]
            kwargs["shadow"] = ShadowSpec(
                offset=tuple(s["offset"]),
                radius=s["radius"],
            )
        if "portrait" in data:
            kwargs["portrait"] = data["portrait"]
        if "tags" in data:
            kwargs["tags"] = data["tags"]
        if "generated" in data:
            g = data["generated"]
            kwargs["generated"] = SpriteSheetGenerationInfo(
                timestamp=g["timestamp"],
                generator=g["generator"],
                prompt=g["prompt"],
                seed=g["seed"],
                model=g["model"],
            )
        return cls(**kwargs)
