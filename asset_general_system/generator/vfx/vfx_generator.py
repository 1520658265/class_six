"""
VFX 生成器。

生成可挂载到技能、交互和环境事件上的 VFX sprite sheet。
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
from ..models.vfx import (
    BlendMode,
    VFXAnchor,
    VFXCategory,
    VFXGenerationInfo,
    VFXMetadata,
)


@dataclass
class VFXGenerationRequest:
    """
    VFX 生成请求。

    Attributes:
        vfx_type: 特效类型，例如 'fireball', 'slash', 'heal'
        description: 详细描述
        frame_size: 单帧尺寸
<<<<<<< HEAD
        style: 视觉风格
=======
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
        frames: 总帧数
        fps: 帧率
        loop: 是否循环
        blend: 混合模式
        category: 类别
        anchor: 锚点
        seed: 随机种子
        tags: 标签
    """
    vfx_type: str
    description: str
    frame_size: tuple[int, int] = (64, 64)
<<<<<<< HEAD
    style: ImageStyle = ImageStyle.PIXEL_ART
=======
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
    frames: int = 8
    fps: int = 12
    loop: bool = False
    blend: BlendMode = BlendMode.NORMAL
    category: VFXCategory = VFXCategory.COMBAT
    anchor: VFXAnchor = VFXAnchor.CENTER
    seed: int | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class VFXGenerationResult:
    """生成结果。"""
    success: bool
    asset_id: str | None = None
    sheet_path: str | None = None
    metadata_path: str | None = None
    metadata: VFXMetadata | None = None
    error: str | None = None


class VFXGenerator:
    """
    VFX sprite sheet 生成器。
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

    def generate(self, request: VFXGenerationRequest) -> VFXGenerationResult:
        """
        生成 VFX sprite sheet。

        Args:
            request: 生成请求

        Returns:
            生成结果
        """
        try:
            from PIL import Image
        except ImportError:
            return VFXGenerationResult(
                success=False,
                error="PIL 不可用",
            )

        asset_id = self._generate_asset_id(request.vfx_type, request.seed)

        # 为每一帧生成图像
        frames = []
        for frame_idx in range(request.frames):
            prompt = self._build_frame_prompt(request, frame_idx)

            img_request = ImageGenerationRequest(
                prompt=prompt,
<<<<<<< HEAD
                style=request.style,
=======
                style=ImageStyle.PIXEL_ART,
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
                size=request.frame_size,
                seed=(request.seed or 0) + frame_idx,
                transparency=TransparencyMode.REQUIRED,
                tile_aligned=False,
                tile_size=request.frame_size,
            )

            response = self.image_generator.generate(img_request)
            if not response.success or not response.image_path:
                return VFXGenerationResult(
                    success=False,
                    error=f"帧 {frame_idx} 生成失败",
                )

            try:
                img = Image.open(response.image_path)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                frames.append(img)
            except Exception as e:
                return VFXGenerationResult(
                    success=False,
                    error=f"加载帧 {frame_idx} 失败: {e}",
                )

        # 打包到一行
        fw, fh = request.frame_size
        sheet_width = fw * request.frames
        sheet_height = fh

        sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))
        for col, frame in enumerate(frames):
            if frame.size != (fw, fh):
                frame = frame.resize((fw, fh), Image.NEAREST)
            sheet.paste(frame, (col * fw, 0), frame if frame.mode == "RGBA" else None)

        sheet_filename = f"{asset_id}.png"
        sheet_path = self.output_dir / sheet_filename
        sheet.save(sheet_path, "PNG")
        sheet.close()

        # 构建 metadata
        metadata = VFXMetadata(
            asset_id=asset_id,
            image=sheet_filename,
            frame_size=request.frame_size,
            frames=request.frames,
            fps=request.fps,
            loop=request.loop,
            blend=request.blend,
            anchor=request.anchor,
            category=request.category,
            tags=request.tags or [request.vfx_type, "vfx"],
            generated=VFXGenerationInfo(
                timestamp=datetime.now().isoformat(),
                generator=self.image_generator.get_model_name(),
                prompt=request.description,
                seed=request.seed or 0,
                model="vfx_generator",
            ),
        )

        # 保存 metadata
        metadata_filename = f"{asset_id}.json"
        metadata_path = self.output_dir / metadata_filename
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return VFXGenerationResult(
            success=True,
            asset_id=asset_id,
            sheet_path=str(sheet_path),
            metadata_path=str(metadata_path),
            metadata=metadata,
        )

    def _generate_asset_id(self, vfx_type: str, seed: int | None) -> str:
        """生成唯一 ID。"""
        base = vfx_type.lower().replace(" ", "_")
        if seed is not None:
            return f"{base}_{seed:04d}"
        return f"{base}_{datetime.now().strftime('%H%M%S')}"

    def _build_frame_prompt(self, request: VFXGenerationRequest, frame_idx: int) -> str:
        """构造单帧 prompt。"""
        progress = (frame_idx + 1) / request.frames

        parts = [request.description]
<<<<<<< HEAD
        if request.style == ImageStyle.PIXEL_ART:
            parts.append("pixel art")
        elif request.style == ImageStyle.HAND_DRAWN:
            parts.append("hand-drawn 2D game effect")
        elif request.style == ImageStyle.LOW_POLY:
            parts.append("low-poly stylized game effect")
        elif request.style == ImageStyle.REALISTIC:
            parts.append("realistic 2D game effect")
=======
        parts.append("pixel art")
>>>>>>> 8b590ee9c80c53c98742d31415f0cb7c10bc58d0
        parts.append("VFX sprite")
        parts.append("transparent background")
        parts.append(f"animation frame {frame_idx + 1} of {request.frames}")

        # 根据进度添加描述
        if progress < 0.3:
            parts.append("starting phase, small")
        elif progress < 0.7:
            parts.append("peak phase, full size")
        else:
            parts.append("dissipating phase, fading")

        if request.blend == BlendMode.ADDITIVE:
            parts.append("glowing, bright")

        parts.append("centered, no shadow")

        return ", ".join(parts)


def generate_standard_vfx(
    generator: VFXGenerator,
    seed_offset: int = 6000,
) -> list[VFXGenerationResult]:
    """
    生成 10 种标准 VFX。

    Returns:
        生成结果列表
    """
    requests = [
        # 战斗特效 (4)
        VFXGenerationRequest(
            vfx_type="fireball",
            description="bright orange fireball with flames and smoke",
            frame_size=(64, 64),
            frames=8,
            fps=12,
            loop=False,
            blend=BlendMode.ADDITIVE,
            category=VFXCategory.COMBAT,
            seed=seed_offset + 1,
            tags=["fireball", "fire", "projectile"],
        ),
        VFXGenerationRequest(
            vfx_type="slash",
            description="white sword slash arc effect",
            frame_size=(64, 64),
            frames=6,
            fps=15,
            loop=False,
            blend=BlendMode.ADDITIVE,
            category=VFXCategory.COMBAT,
            seed=seed_offset + 2,
            tags=["slash", "sword", "melee"],
        ),
        VFXGenerationRequest(
            vfx_type="explosion",
            description="big orange explosion with smoke and debris",
            frame_size=(96, 96),
            frames=10,
            fps=15,
            loop=False,
            blend=BlendMode.ADDITIVE,
            category=VFXCategory.COMBAT,
            seed=seed_offset + 3,
            tags=["explosion", "boom", "fire"],
        ),
        VFXGenerationRequest(
            vfx_type="impact",
            description="white impact burst with radial lines",
            frame_size=(48, 48),
            frames=5,
            fps=20,
            loop=False,
            blend=BlendMode.ADDITIVE,
            category=VFXCategory.COMBAT,
            seed=seed_offset + 4,
            tags=["impact", "hit", "burst"],
        ),

        # 魔法特效 (3)
        VFXGenerationRequest(
            vfx_type="heal",
            description="green healing aura with sparkles rising upward",
            frame_size=(64, 64),
            frames=8,
            fps=10,
            loop=True,
            blend=BlendMode.ADDITIVE,
            category=VFXCategory.MAGIC,
            seed=seed_offset + 5,
            tags=["heal", "magic", "buff"],
        ),
        VFXGenerationRequest(
            vfx_type="teleport",
            description="purple swirl portal with energy lines",
            frame_size=(64, 96),
            frames=8,
            fps=12,
            loop=False,
            blend=BlendMode.ADDITIVE,
            category=VFXCategory.MAGIC,
            seed=seed_offset + 6,
            tags=["teleport", "portal", "magic"],
        ),
        VFXGenerationRequest(
            vfx_type="sparkle",
            description="small twinkling stars and dust particles",
            frame_size=(32, 32),
            frames=6,
            fps=10,
            loop=True,
            blend=BlendMode.ADDITIVE,
            category=VFXCategory.MAGIC,
            seed=seed_offset + 7,
            tags=["sparkle", "magic", "ambient"],
        ),

        # 环境特效 (3)
        VFXGenerationRequest(
            vfx_type="rain",
            description="white rain drops falling diagonally",
            frame_size=(128, 128),
            frames=4,
            fps=12,
            loop=True,
            blend=BlendMode.NORMAL,
            category=VFXCategory.ENVIRONMENT,
            seed=seed_offset + 8,
            tags=["rain", "weather", "environment"],
        ),
        VFXGenerationRequest(
            vfx_type="snow",
            description="soft white snow flakes drifting down",
            frame_size=(128, 128),
            frames=6,
            fps=8,
            loop=True,
            blend=BlendMode.NORMAL,
            category=VFXCategory.ENVIRONMENT,
            seed=seed_offset + 9,
            tags=["snow", "weather", "environment"],
        ),
        VFXGenerationRequest(
            vfx_type="leaves",
            description="autumn leaves falling and rotating",
            frame_size=(128, 128),
            frames=8,
            fps=10,
            loop=True,
            blend=BlendMode.NORMAL,
            category=VFXCategory.ENVIRONMENT,
            seed=seed_offset + 10,
            tags=["leaves", "autumn", "ambient"],
        ),
    ]

    results = []
    for req in requests:
        result = generator.generate(req)
        results.append(result)

    return results
