"""
Object sprite generator - generates individual map objects with metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from generator.assets.image_generation import (
    ImageGenerationRequest,
    ImageGenerationResponse,
    ImageGenerator,
    ImageStyle,
    TransparencyMode,
    validate_generated_image,
)
from generator.assets.sprite_cleanup import (
    RpgSpriteUsability,
    SpriteRepackResult,
    clean_object_sprite_background,
    fit_object_sprite_to_runtime_canvas,
    validate_object_sprite_quality,
    validate_rpg_sprite_usability,
)
from generator.models.asset_metadata import (
    AnchorPoint,
    AssetKind,
    AssetMetadata,
    AssetSourceType,
    GenerationMetadata,
    SourceMetadata,
    VisualBounds,
)


@dataclass
class ObjectGenerationRequest:
    """
    Request to generate a map object sprite.

    Attributes:
        object_type: Type of object (tree, rock, chest, etc.)
        description: Detailed description for generation
        style: Visual style
        footprint: Tile grid size [columns, rows]
        tile_size: Base tile size in pixels
        theme: Compatible themes
        seed: Random seed
        tags: Additional semantic tags
    """
    object_type: str
    description: str
    style: ImageStyle = ImageStyle.PIXEL_ART
    footprint: tuple[int, int] = (1, 1)
    tile_size: tuple[int, int] = (32, 32)
    source_canvas: tuple[int, int] | None = None
    category: str = ""
    anchor: str = ""
    theme: list[str] | None = None
    seed: int | None = None
    tags: list[str] | None = None


@dataclass
class ObjectGenerationResult:
    """Result of object generation."""
    success: bool
    asset_id: str | None = None
    sprite_path: str | None = None
    metadata_path: str | None = None
    metadata: AssetMetadata | None = None
    usability: RpgSpriteUsability | None = None
    repack: SpriteRepackResult | None = None
    error: str | None = None


class ObjectGenerator:
    """
    Generates map object sprites with automatic metadata annotation.
    """

    def __init__(
        self,
        image_generator: ImageGenerator,
        output_dir: Path,
    ):
        """
        Initialize object generator.

        Args:
            image_generator: Image generation backend
            output_dir: Directory for generated objects
        """
        self.image_generator = image_generator
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: ObjectGenerationRequest) -> ObjectGenerationResult:
        """
        Generate a map object sprite with metadata.

        Args:
            request: Object generation request

        Returns:
            Result with asset ID, paths, and metadata
        """
        # Generate asset ID
        asset_id = self._generate_asset_id(request.object_type, request.seed)

        # Build generation prompt
        prompt = self._build_prompt(request)

        # Calculate pixel size from footprint
        pixel_size = request.source_canvas or (
            request.footprint[0] * request.tile_size[0],
            request.footprint[1] * request.tile_size[1],
        )

        # Create image generation request
        img_request = ImageGenerationRequest(
            prompt=prompt,
            style=request.style,
            size=pixel_size,
            seed=request.seed,
            transparency=TransparencyMode.REQUIRED,
            tile_aligned=True,
            tile_size=request.tile_size,
            negative_prompt=self._build_negative_prompt(),
        )

        # Generate image
        img_response = self.image_generator.generate(img_request)

        if not img_response.success:
            return ObjectGenerationResult(
                success=False,
                error=f"Image generation failed: {img_response.error}"
            )

        # Move image to assets directory
        sprite_filename = f"{asset_id}.png"
        sprite_path = self.output_dir / sprite_filename

        import shutil

        try:
            shutil.move(img_response.image_path, sprite_path)
        except PermissionError:
            shutil.copyfile(img_response.image_path, sprite_path)
            try:
                Path(img_response.image_path).unlink()
            except OSError:
                pass

        quality = clean_object_sprite_background(sprite_path)
        if not quality.passed:
            return ObjectGenerationResult(
                success=False,
                sprite_path=str(sprite_path),
                error=f"Object sprite quality failed: {'; '.join(quality.errors)}",
            )
        anchor = request.anchor or ("bottom_center" if request.footprint[1] > 1 else "center")
        repack = fit_object_sprite_to_runtime_canvas(
            sprite_path,
            request.footprint,
            request.tile_size,
            anchor=anchor,
            category=request.category,
        )
        if not repack.passed:
            return ObjectGenerationResult(
                success=False,
                sprite_path=str(sprite_path),
                repack=repack,
                error=f"Object sprite repack failed: {'; '.join(repack.errors)}",
            )
        quality = validate_object_sprite_quality(sprite_path)
        if not quality.passed:
            return ObjectGenerationResult(
                success=False,
                sprite_path=str(sprite_path),
                repack=repack,
                error=f"Object sprite quality failed after repack: {'; '.join(quality.errors)}",
            )
        usability = validate_rpg_sprite_usability(
            sprite_path,
            request.footprint,
            request.tile_size,
            category=request.category,
        )
        if not usability.passed:
            return ObjectGenerationResult(
                success=False,
                sprite_path=str(sprite_path),
                usability=usability,
                repack=repack,
                error=f"RPG sprite usability failed: {'; '.join(usability.errors)}",
            )

        # Auto-annotate metadata
        metadata = self._create_metadata(
            asset_id=asset_id,
            request=request,
            sprite_filename=sprite_filename,
            img_response=img_response,
        )

        # Save metadata
        metadata_filename = f"{asset_id}.json"
        metadata_path = self.output_dir / metadata_filename
        metadata.metadata_path = metadata_filename

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)

        return ObjectGenerationResult(
            success=True,
            asset_id=asset_id,
            sprite_path=str(sprite_path),
            metadata_path=str(metadata_path),
            metadata=metadata,
            usability=usability,
            repack=repack,
        )

    def _generate_asset_id(self, object_type: str, seed: int | None) -> str:
        """Generate unique asset ID."""
        base = object_type.lower().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if seed is not None:
            return f"{base}_{seed:04d}"
        return f"{base}_{timestamp}"

    def _build_prompt(self, request: ObjectGenerationRequest) -> str:
        """Build image generation prompt from request."""
        pixel_size = request.source_canvas or (
            request.footprint[0] * request.tile_size[0],
            request.footprint[1] * request.tile_size[1],
        )
        runtime_size = (
            request.footprint[0] * request.tile_size[0],
            request.footprint[1] * request.tile_size[1],
        )
        description = request.description.strip()
        parts = []
        if description.startswith("TASK:") or "Asset contract:" in description:
            parts.append(description)
        else:
            parts.extend(
                [
                    "TASK: Create one production-ready RPG map object sprite for a Tiled/RPGMaker-style object layer.",
                    "This must be an isolated transparent PNG sprite asset, not a full scene, not a tileset, and not a UI icon.",
                    "",
                    "Asset contract:",
                    f"- Description: {description}",
                    f"- Category: {request.category or 'object'}",
                    f"- Source canvas: {pixel_size[0]}x{pixel_size[1]} px",
                    f"- Footprint in map: {request.footprint[0]}x{request.footprint[1]} tiles",
                    f"- Runtime display size: {runtime_size[0]}x{runtime_size[1]} px",
                    f"- Tile size: {request.tile_size[0]}x{request.tile_size[1]} px",
                    f"- Anchor: {request.anchor or ('bottom_center' if request.footprint[1] > 1 else 'center')}",
                    "",
                    "Composition:",
                    "- Make the main silhouette large, clear, and readable at runtime size.",
                    "- Do not leave a tiny subject floating in a huge empty canvas.",
                    "- Use chunky readable pixel-art shapes instead of thin fragile lines.",
                    "- Use real PNG alpha transparency only.",
                    "- Keep transparent margins, but no background, no floor, no terrain, no sky, no scene, no frame, no cast shadow.",
                ]
            )

        if request.style == ImageStyle.PIXEL_ART:
            parts.extend(
                [
                    "",
                    "Pixel-art style:",
                    "- 16-bit RPG pixel art suitable for in-game map object sprites.",
                    "- Crisp hard pixel edges, readable clusters, no blur, no painterly texture.",
                    "- Limited clean palette, avoid random speckles and noisy anti-aliasing.",
                    "- Do not use 8-bit micro-icon style.",
                ]
            )
        elif request.style == ImageStyle.HAND_DRAWN:
            parts.extend(["", "Style:", "- Hand-drawn 2D game asset with clean transparent silhouette."])

        area = request.footprint[0] * request.footprint[1]
        building_words = ("building", "house", "shop", "hall", "dormitory", "school", "食堂", "宿舍", "小卖部", "教学楼", "房", "楼")
        if area >= 9 or any(word in request.description.lower() for word in building_words):
            parts.extend(
                [
                    "",
                    "Building-specific requirements:",
                    "- Draw only the building sprite itself: facade, roof, side volume, visible entrance, and windows.",
                    "- No surrounding ground, no road, no landscape, no campus scene.",
                    "- The building should fill most of its footprint and stay readable at runtime scale.",
                    "- Use broad pixel clusters for walls, roof, windows, and doors; avoid tiny noisy texture.",
                ]
            )
        else:
            parts.extend(
                [
                    "",
                    "Object-specific requirements:",
                    "- Draw exactly one prop/object, not multiple variants and not a scene.",
                    "- Avoid hairline details; use simplified thick readable pixel shapes.",
                    "- The object must still be recognizable when displayed at the runtime size.",
                ]
            )

        parts.extend(
            [
                "",
                "View and output:",
                "- Top-down 3/4 or slight isometric RPG view, aligned to the map tile grid.",
                "- Transparent outside the object only.",
                "- No checkerboard, fake transparency, watermark, labels, UI, border, or text unless explicitly requested.",
            ]
        )

        if request.theme:
            parts.append(f"- Theme context: {', '.join(request.theme)}")

        return "\n".join(parts)

    def _build_negative_prompt(self) -> str:
        """Build negative prompt to avoid unwanted features."""
        return ", ".join([
            "text",
            "watermark",
            "signature",
            "3D render",
            "photorealistic",
            "blurry",
            "soft edges",
            "anti-aliased blur",
            "jpeg artifacts",
            "white background",
            "black background",
            "gray background",
            "solid background",
            "checkerboard background",
            "fake transparency",
            "noisy background",
            "floor",
            "terrain",
            "landscape",
            "sky",
            "scene",
        ])

    def _create_metadata(
        self,
        asset_id: str,
        request: ObjectGenerationRequest,
        sprite_filename: str,
        img_response: ImageGenerationResponse,
    ) -> AssetMetadata:
        """Create metadata from generation request and response."""
        # Determine tags
        tags = list(request.tags) if request.tags else []
        if request.object_type not in tags:
            tags.insert(0, request.object_type)

        # Determine if blocking
        blocking_types = {"tree", "rock", "wall", "building", "chest", "stall"}
        if any(t in request.object_type.lower() for t in blocking_types):
            if "blocking" not in tags:
                tags.append("blocking")

        # Determine collision based on footprint
        # For multi-tile objects, assume bottom row blocks movement
        collision = []
        if request.footprint[1] > 1:
            # Bottom row blocks
            for col in range(request.footprint[0]):
                collision.append((col, request.footprint[1] - 1))
        else:
            # Single row, mark center as blocking if it's a blocking object
            if "blocking" in tags:
                collision.append((request.footprint[0] // 2, 0))

        # Determine anchor
        anchor = AnchorPoint.BOTTOM_CENTER
        if request.footprint[1] > 1:
            # Tall objects anchor at bottom
            anchor = AnchorPoint.BOTTOM_CENTER
        else:
            # Small objects anchor at center
            anchor = AnchorPoint.CENTER

        # Build generation metadata
        gen_metadata = GenerationMetadata(
            timestamp=datetime.now().isoformat(),
            generator=self.image_generator.get_model_name(),
            prompt=request.description,
            seed=img_response.actual_seed or 0,
            model=img_response.model or "unknown",
        )

        # Build source metadata
        source = SourceMetadata(
            type=AssetSourceType.GENERATED,
            attribution="AI-generated by asset_general_system",
        )

        return AssetMetadata(
            asset_id=asset_id,
            kind=AssetKind.TILE_OBJECT,
            tags=tags,
            tile_size=request.tile_size,
            theme=request.theme or [],
            footprint=request.footprint,
            collision=collision,
            anchor=anchor,
            sprite_path=sprite_filename,
            generated=gen_metadata,
            source=source,
        )


def generate_standard_objects(
    generator: ObjectGenerator,
    style: ImageStyle = ImageStyle.PIXEL_ART,
    tile_size: tuple[int, int] = (32, 32),
    seed_offset: int = 1000,
) -> list[ObjectGenerationResult]:
    """
    Generate a standard set of 20 RPG map objects.

    Args:
        generator: Object generator instance
        style: Visual style for all objects
        tile_size: Base tile size
        seed_offset: Starting seed value

    Returns:
        List of generation results
    """
    requests = [
        # Trees (5)
        ObjectGenerationRequest(
            object_type="tree_oak",
            description="oak tree with green leaves and brown trunk",
            style=style,
            footprint=(1, 2),
            tile_size=tile_size,
            theme=["forest", "village", "plains"],
            seed=seed_offset + 1,
            tags=["tree", "oak", "nature", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="tree_pine",
            description="pine tree with dark green needles and conical shape",
            style=style,
            footprint=(1, 2),
            tile_size=tile_size,
            theme=["forest", "snow", "mountains"],
            seed=seed_offset + 2,
            tags=["tree", "pine", "nature", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="tree_palm",
            description="palm tree with long leaves and curved trunk",
            style=style,
            footprint=(1, 2),
            tile_size=tile_size,
            theme=["desert", "beach", "tropical"],
            seed=seed_offset + 3,
            tags=["tree", "palm", "nature", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="tree_willow",
            description="willow tree with drooping branches",
            style=style,
            footprint=(2, 2),
            tile_size=tile_size,
            theme=["village", "forest", "plains"],
            seed=seed_offset + 4,
            tags=["tree", "willow", "nature", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="tree_dead",
            description="dead tree with bare branches",
            style=style,
            footprint=(1, 2),
            tile_size=tile_size,
            theme=["ruins", "desert", "haunted"],
            seed=seed_offset + 5,
            tags=["tree", "dead", "nature", "blocking"],
        ),

        # Rocks (3)
        ObjectGenerationRequest(
            object_type="rock_small",
            description="small gray rock with moss patches",
            style=style,
            footprint=(1, 1),
            tile_size=tile_size,
            theme=["forest", "mountains", "desert"],
            seed=seed_offset + 6,
            tags=["rock", "stone", "nature", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="rock_large",
            description="large boulder with rough surface",
            style=style,
            footprint=(2, 1),
            tile_size=tile_size,
            theme=["mountains", "desert", "ruins"],
            seed=seed_offset + 7,
            tags=["rock", "boulder", "stone", "nature", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="crystal",
            description="glowing blue crystal cluster",
            style=style,
            footprint=(1, 1),
            tile_size=tile_size,
            theme=["cave", "dungeon", "magic"],
            seed=seed_offset + 8,
            tags=["crystal", "magic", "glowing", "blocking"],
        ),

        # Containers (3)
        ObjectGenerationRequest(
            object_type="chest",
            description="wooden treasure chest with metal lock",
            style=style,
            footprint=(1, 1),
            tile_size=tile_size,
            theme=["dungeon", "village", "ruins"],
            seed=seed_offset + 9,
            tags=["chest", "treasure", "container", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="barrel",
            description="wooden barrel with metal bands",
            style=style,
            footprint=(1, 1),
            tile_size=tile_size,
            theme=["village", "dungeon", "ship"],
            seed=seed_offset + 10,
            tags=["barrel", "container", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="crate",
            description="wooden crate with nails",
            style=style,
            footprint=(1, 1),
            tile_size=tile_size,
            theme=["village", "warehouse", "dock"],
            seed=seed_offset + 11,
            tags=["crate", "container", "blocking"],
        ),

        # Decorations (5)
        ObjectGenerationRequest(
            object_type="lamppost",
            description="iron lamppost with glowing lantern",
            style=style,
            footprint=(1, 2),
            tile_size=tile_size,
            theme=["village", "city", "street"],
            seed=seed_offset + 12,
            tags=["lamppost", "light", "decoration", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="statue",
            description="stone statue of a warrior",
            style=style,
            footprint=(1, 2),
            tile_size=tile_size,
            theme=["temple", "ruins", "plaza"],
            seed=seed_offset + 13,
            tags=["statue", "monument", "decoration", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="well",
            description="stone well with wooden roof",
            style=style,
            footprint=(2, 2),
            tile_size=tile_size,
            theme=["village", "desert", "ruins"],
            seed=seed_offset + 14,
            tags=["well", "water", "building", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="fountain",
            description="decorative fountain with water",
            style=style,
            footprint=(2, 2),
            tile_size=tile_size,
            theme=["plaza", "garden", "temple"],
            seed=seed_offset + 15,
            tags=["fountain", "water", "decoration", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="bench",
            description="wooden bench with backrest",
            style=style,
            footprint=(2, 1),
            tile_size=tile_size,
            theme=["park", "village", "plaza"],
            seed=seed_offset + 16,
            tags=["bench", "furniture", "decoration"],
        ),

        # Signs and Markers (2)
        ObjectGenerationRequest(
            object_type="signpost",
            description="wooden signpost with directional arrows",
            style=style,
            footprint=(1, 1),
            tile_size=tile_size,
            theme=["village", "forest", "crossroad"],
            seed=seed_offset + 17,
            tags=["signpost", "marker", "decoration", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="torch",
            description="wall-mounted torch with flame",
            style=style,
            footprint=(1, 1),
            tile_size=tile_size,
            theme=["dungeon", "castle", "cave"],
            seed=seed_offset + 18,
            tags=["torch", "light", "fire", "decoration"],
        ),

        # Structures (2)
        ObjectGenerationRequest(
            object_type="stall",
            description="wooden market stall with striped canopy",
            style=style,
            footprint=(2, 1),
            tile_size=tile_size,
            theme=["village", "market"],
            seed=seed_offset + 19,
            tags=["stall", "market", "shop", "blocking"],
        ),
        ObjectGenerationRequest(
            object_type="gate",
            description="wooden gate with iron reinforcement",
            style=style,
            footprint=(2, 1),
            tile_size=tile_size,
            theme=["village", "castle", "garden"],
            seed=seed_offset + 20,
            tags=["gate", "door", "entrance"],
        ),
    ]

    results = []
    for req in requests:
        result = generator.generate(req)
        results.append(result)

    return results
