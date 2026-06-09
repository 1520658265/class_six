"""
角色生成器。

<<<<<<< HEAD
生成 RPG 角色的 sprite sheet：4/8 方向 idle/walk 动画。
=======
生成 RPG 角色的 sprite sheet：4 方向 idle/walk 动画。
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ..assets.image_generation import (
    ImageGenerationRequest,
    ImageGenerator,
    ImageStyle,
    TransparencyMode,
)
from ..models.sprite_sheet import (
    AnimationClip,
    CharacterAnchor,
    Direction,
    HitBox,
    ShadowSpec,
    SpriteSheetGenerationInfo,
    SpriteSheetMetadata,
)
from .sprite_packer import SpriteSheetPacker


@dataclass
class CharacterGenerationRequest:
    """
    角色生成请求。

    Attributes:
        character_type: 角色类型，例如 'merchant', 'guard', 'villager'
        description: 详细描述
        style: 视觉风格
        frame_size: 单帧尺寸 [width, height]，默认 32x48
        directions: 朝向列表
        animations: 动作列表，例如 ['idle', 'walk']
        frames_per_animation: 每个动作帧数
<<<<<<< HEAD
        fps: 播放帧率；为空时由打包器根据动作名推断
=======
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
        seed: 随机种子
        tags: 标签
    """
    character_type: str
    description: str
    style: ImageStyle = ImageStyle.PIXEL_ART
    frame_size: tuple[int, int] = (32, 48)
    directions: list[Direction] = field(default_factory=lambda: [
        Direction.DOWN, Direction.LEFT, Direction.RIGHT, Direction.UP,
    ])
    animations: list[str] = field(default_factory=lambda: ["idle", "walk"])
    frames_per_animation: int = 4
<<<<<<< HEAD
    fps: int | None = None
=======
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
    seed: int | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class CharacterGenerationResult:
    """生成结果。"""
    success: bool
    asset_id: str | None = None
    sheet_path: str | None = None
    metadata_path: str | None = None
    metadata: SpriteSheetMetadata | None = None
    error: str | None = None


class CharacterGenerator:
    """
    角色 sprite sheet 生成器。

    生成流程：
    1. 为每个 animation x direction 生成单帧
    2. 使用 SpriteSheetPacker 打包成单个 PNG
    3. 生成完整 metadata
    """

    def __init__(
        self,
        image_generator: ImageGenerator,
        output_dir: Path,
    ):
        """
        Args:
            image_generator: 图像生成后端
            output_dir: 输出目录
        """
        self.image_generator = image_generator
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: CharacterGenerationRequest) -> CharacterGenerationResult:
        """
        生成角色 sprite sheet。

        Args:
            request: 角色生成请求

        Returns:
            生成结果
        """
        try:
            from PIL import Image
        except ImportError:
            return CharacterGenerationResult(
                success=False,
                error="PIL 不可用",
            )

        # 生成 asset_id
        asset_id = self._generate_asset_id(request.character_type, request.seed)

        # 创建打包器
        packer = SpriteSheetPacker(frame_size=request.frame_size)

        # 为每个 animation x direction 生成帧
        frames_by_animation: dict[str, list] = {}

        for animation in request.animations:
            for direction in request.directions:
                anim_key = f"{animation}_{direction.value}"
                frames = self._generate_frames(
                    request=request,
                    animation=animation,
                    direction=direction,
                    asset_id=asset_id,
                )

                if not frames:
                    return CharacterGenerationResult(
                        success=False,
                        error=f"生成 {anim_key} 帧失败",
                    )

                frames_by_animation[anim_key] = frames

        # 打包成 sprite sheet
        sheet_filename = f"{asset_id}.png"
        sheet_path = self.output_dir / sheet_filename

<<<<<<< HEAD
        animations = packer.pack_frames(
            frames_by_animation,
            sheet_path,
            default_fps=request.fps,
        )
=======
        animations = packer.pack_frames(frames_by_animation, sheet_path)
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0

        # 构建 metadata
        metadata = packer.build_metadata(
            asset_id=asset_id,
            image_path=sheet_filename,
            animations=animations,
            directions=request.directions,
            anchor=CharacterAnchor.FEET_CENTER,
            tags=request.tags or [request.character_type, "character"],
        )

        # 添加生成信息
        metadata.generated = SpriteSheetGenerationInfo(
            timestamp=datetime.now().isoformat(),
            generator=self.image_generator.get_model_name(),
            prompt=request.description,
            seed=request.seed or 0,
            model="character_generator",
        )

        # 保存 metadata
        metadata_filename = f"{asset_id}.json"
        metadata_path = self.output_dir / metadata_filename
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return CharacterGenerationResult(
            success=True,
            asset_id=asset_id,
            sheet_path=str(sheet_path),
            metadata_path=str(metadata_path),
            metadata=metadata,
        )

    def _generate_asset_id(self, character_type: str, seed: int | None) -> str:
        """生成唯一 ID。"""
        base = character_type.lower().replace(" ", "_")
        if seed is not None:
            return f"{base}_{seed:04d}"
        return f"{base}_{datetime.now().strftime('%H%M%S')}"

    def _generate_frames(
        self,
        request: CharacterGenerationRequest,
        animation: str,
        direction: Direction,
        asset_id: str,
    ) -> list:
        """为单个 animation x direction 生成所有帧。"""
        frames = []

        for frame_idx in range(request.frames_per_animation):
            prompt = self._build_frame_prompt(
                request=request,
                animation=animation,
                direction=direction,
                frame_idx=frame_idx,
            )

            img_request = ImageGenerationRequest(
                prompt=prompt,
                style=request.style,
                size=request.frame_size,
                seed=(request.seed or 0) + hash((animation, direction.value, frame_idx)) % 10000,
                transparency=TransparencyMode.REQUIRED,
                tile_aligned=False,
                tile_size=request.frame_size,
            )

            response = self.image_generator.generate(img_request)
            if not response.success or not response.image_path:
                return []

            try:
                from PIL import Image
                img = Image.open(response.image_path)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                frames.append(img)
            except Exception:
                return []

        return frames

    def _build_frame_prompt(
        self,
        request: CharacterGenerationRequest,
        animation: str,
        direction: Direction,
        frame_idx: int,
    ) -> str:
        """构造单帧的生成 prompt。"""
        parts = [request.description]

        # 风格
        if request.style == ImageStyle.PIXEL_ART:
            parts.append("pixel art")

        # 方向描述
        direction_text = {
            Direction.DOWN: "facing camera (front view)",
<<<<<<< HEAD
            Direction.DOWN_LEFT: "three-quarter front view, facing down-left",
            Direction.DOWN_RIGHT: "three-quarter front view, facing down-right",
            Direction.UP: "back view",
            Direction.UP_LEFT: "three-quarter back view, facing up-left",
            Direction.UP_RIGHT: "three-quarter back view, facing up-right",
=======
            Direction.UP: "back view",
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
            Direction.LEFT: "left side view",
            Direction.RIGHT: "right side view",
        }[direction]
        parts.append(direction_text)

        # 动作描述
        action_text = {
            "idle": "standing pose",
            "walk": f"walking, frame {frame_idx + 1}",
            "run": f"running, frame {frame_idx + 1}",
            "attack": f"attack pose, frame {frame_idx + 1}",
            "cast": f"casting spell, frame {frame_idx + 1}",
            "hurt": "hurt reaction",
            "death": f"falling down, frame {frame_idx + 1}",
        }.get(animation, animation)
        parts.append(action_text)

        # 通用属性
        parts.append("transparent background")
        parts.append("centered, full body")
        parts.append("RPG character sprite")

        if request.tags:
            parts.append(", ".join(request.tags))

        return ", ".join(parts)


def generate_standard_characters(
    generator: CharacterGenerator,
    seed_offset: int = 5000,
) -> list[CharacterGenerationResult]:
    """
    生成 10 个标准 RPG 角色。

    Args:
        generator: 角色生成器
        seed_offset: 种子偏移

    Returns:
        生成结果列表
    """
    requests = [
        CharacterGenerationRequest(
            character_type="villager_male",
            description="village man with brown shirt and pants",
            seed=seed_offset + 1,
            tags=["villager", "male", "civilian"],
        ),
        CharacterGenerationRequest(
            character_type="villager_female",
            description="village woman with simple dress",
            seed=seed_offset + 2,
            tags=["villager", "female", "civilian"],
        ),
        CharacterGenerationRequest(
            character_type="merchant",
            description="merchant in green robes with a coin pouch",
            seed=seed_offset + 3,
            tags=["merchant", "vendor", "civilian"],
        ),
        CharacterGenerationRequest(
            character_type="guard",
            description="armored guard with helmet and spear",
            seed=seed_offset + 4,
            tags=["guard", "armored", "warrior"],
        ),
        CharacterGenerationRequest(
            character_type="knight",
            description="knight in shining armor with sword",
            seed=seed_offset + 5,
            tags=["knight", "armored", "warrior"],
        ),
        CharacterGenerationRequest(
            character_type="mage",
            description="wizard with blue robe and pointy hat",
            seed=seed_offset + 6,
            tags=["mage", "wizard", "magic"],
        ),
        CharacterGenerationRequest(
            character_type="archer",
            description="archer with green hood and bow",
            seed=seed_offset + 7,
            tags=["archer", "ranger", "warrior"],
        ),
        CharacterGenerationRequest(
            character_type="goblin",
            description="small green goblin with crude weapon",
            seed=seed_offset + 8,
            tags=["goblin", "monster", "enemy"],
        ),
        CharacterGenerationRequest(
            character_type="skeleton",
            description="skeleton warrior with rusty sword",
            seed=seed_offset + 9,
            tags=["skeleton", "undead", "enemy"],
        ),
        CharacterGenerationRequest(
            character_type="hero",
            description="young hero with cloak and silver sword",
            seed=seed_offset + 10,
            tags=["hero", "protagonist", "warrior"],
        ),
    ]

    results = []
    for req in requests:
        result = generator.generate(req)
        results.append(result)

    return results
