"""
Image generation interface and protocol for AI-generated assets.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ImageStyle(str, Enum):
    """Visual style for generated images."""
    PIXEL_ART = "pixel_art"
    HAND_DRAWN = "hand_drawn"
    LOW_POLY = "low_poly"
    REALISTIC = "realistic"


class TransparencyMode(str, Enum):
    """Background transparency handling."""
    REQUIRED = "required"  # Must have transparent background
    OPTIONAL = "optional"  # Transparent if possible
    OPAQUE = "opaque"  # Solid background allowed


@dataclass
class ImageGenerationRequest:
    """
    Request for AI image generation.

    Attributes:
        prompt: Text description of what to generate
        style: Visual style (pixel_art, hand_drawn, etc.)
        size: Target size in pixels [width, height]
        seed: Random seed for reproducibility
        transparency: Background transparency requirement
        tile_aligned: Whether size must align to tile grid
        tile_size: Base tile size if tile_aligned is True
        negative_prompt: Things to avoid in generation
        reference_images: Paths to style reference images
        metadata: Additional generation parameters
    """
    prompt: str
    style: ImageStyle
    size: tuple[int, int]
    seed: int | None = None
    transparency: TransparencyMode = TransparencyMode.REQUIRED
    tile_aligned: bool = True
    tile_size: tuple[int, int] = (32, 32)
    negative_prompt: str | None = None
    reference_images: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageValidation:
    """Validation results for generated image."""
    passed: bool
    has_transparency: bool
    has_clean_edges: bool
    size_correct: bool
    tile_aligned: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ImageGenerationResponse:
    """
    Response from image generation.

    Attributes:
        success: Whether generation succeeded
        image_path: Path to generated PNG file
        validation: Validation results
        generation_time: Time taken in seconds
        model: Model used for generation
        actual_seed: Actual seed used (may differ from request if auto-generated)
        error: Error message if success is False
        metadata: Additional response metadata
    """
    success: bool
    image_path: str | None = None
    validation: ImageValidation | None = None
    generation_time: float = 0.0
    model: str | None = None
    actual_seed: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationHistory:
    """History entry for a generated asset."""
    request: ImageGenerationRequest
    response: ImageGenerationResponse
    timestamp: str
    asset_id: str | None = None


class ImageGenerator(ABC):
    """
    Abstract base class for image generation backends.

    Subclasses implement specific AI image generation services
    (Gemini, DALL-E, Stable Diffusion, etc.).
    """

    @abstractmethod
    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """
        Generate an image from the request.

        Args:
            request: Generation request with prompt, style, size, etc.

        Returns:
            Response with image path and validation results
        """
        pass

    @abstractmethod
    def supports_style(self, style: ImageStyle) -> bool:
        """Check if this generator supports the given style."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name/version of the underlying model."""
        pass


class MockImageGenerator(ImageGenerator):
    """
    Mock generator for testing that creates placeholder images.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResponse:
        """Generate a simple placeholder image."""
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            return ImageGenerationResponse(
                success=False,
                error="PIL not available for mock generation"
            )

        # Create placeholder image
        img = Image.new("RGBA", request.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw a simple shape based on prompt
        color = (100, 150, 200, 255)
        if "tree" in request.prompt.lower():
            color = (50, 150, 50, 255)
        elif "rock" in request.prompt.lower():
            color = (128, 128, 128, 255)
        elif "chest" in request.prompt.lower():
            color = (139, 69, 19, 255)

        # Draw a simple rectangle
        margin = max(1, min(request.size) // 4)
        draw.rectangle(
            [margin, margin, request.size[0] - margin, request.size[1] - margin],
            fill=color
        )

        # Save
        filename = f"mock_{hash(request.prompt) % 10000:04d}.png"
        output_path = self.output_dir / filename
        img.save(output_path, "PNG")
        img.close()

        validation = ImageValidation(
            passed=True,
            has_transparency=True,
            has_clean_edges=True,
            size_correct=True,
            tile_aligned=request.tile_aligned
        )

        return ImageGenerationResponse(
            success=True,
            image_path=str(output_path),
            validation=validation,
            generation_time=0.1,
            model="mock",
            actual_seed=request.seed or 0
        )

    def supports_style(self, style: ImageStyle) -> bool:
        return True

    def get_model_name(self) -> str:
        return "MockGenerator-v1"


def validate_generated_image(
    image_path: str | Path,
    expected_size: tuple[int, int] | None = None,
    require_transparency: bool = True,
    tile_size: tuple[int, int] = (32, 32),
) -> ImageValidation:
    """
    Validate a generated image.

    Args:
        image_path: Path to image file
        expected_size: Expected [width, height], None to skip check
        require_transparency: Whether transparent background is required
        tile_size: Base tile size for alignment check

    Returns:
        Validation results
    """
    try:
        from PIL import Image
    except ImportError:
        return ImageValidation(
            passed=False,
            has_transparency=False,
            has_clean_edges=False,
            size_correct=False,
            tile_aligned=False,
            errors=["PIL not available for validation"]
        )

    errors = []
    warnings = []

    try:
        img = Image.open(image_path)
    except Exception as e:
        return ImageValidation(
            passed=False,
            has_transparency=False,
            has_clean_edges=False,
            size_correct=False,
            tile_aligned=False,
            errors=[f"Failed to open image: {e}"]
        )

    # Check size
    size_correct = True
    if expected_size and img.size != expected_size:
        size_correct = False
        errors.append(f"Size mismatch: expected {expected_size}, got {img.size}")

    # Check tile alignment
    tile_aligned = (
        img.width % tile_size[0] == 0 and
        img.height % tile_size[1] == 0
    )
    if not tile_aligned:
        warnings.append(f"Image size {img.size} not aligned to tile grid {tile_size}")

    # Check transparency
    has_transparency = img.mode == "RGBA" and img.getextrema()[-1][0] < 255
    if require_transparency and not has_transparency:
        errors.append("Image does not have transparent background")

    # Check clean edges (simple heuristic: check if corners are transparent)
    has_clean_edges = True
    if img.mode == "RGBA":
        corners = [
            img.getpixel((0, 0)),
            img.getpixel((img.width - 1, 0)),
            img.getpixel((0, img.height - 1)),
            img.getpixel((img.width - 1, img.height - 1)),
        ]
        if any(c[3] > 10 for c in corners):  # Alpha > 10
            has_clean_edges = False
            warnings.append("Image corners are not fully transparent")

    passed = len(errors) == 0

    return ImageValidation(
        passed=passed,
        has_transparency=has_transparency,
        has_clean_edges=has_clean_edges,
        size_correct=size_correct,
        tile_aligned=tile_aligned,
        errors=errors,
        warnings=warnings
    )
