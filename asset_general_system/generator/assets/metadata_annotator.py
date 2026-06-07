"""
Automatic metadata annotation from image analysis.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from generator.models.asset_metadata import AnchorPoint, VisualBounds


def analyze_footprint_from_image(
    image_path: str | Path,
    tile_size: tuple[int, int] = (32, 32),
) -> tuple[int, int]:
    """
    Calculate footprint (occupied grid cells) from image dimensions.

    Args:
        image_path: Path to image file
        tile_size: Base tile size [width, height]

    Returns:
        Footprint as [columns, rows]
    """
    try:
        from PIL import Image
    except ImportError:
        # Fallback to 1x1 if PIL not available
        return (1, 1)

    img = Image.open(image_path)
    cols = (img.width + tile_size[0] - 1) // tile_size[0]
    rows = (img.height + tile_size[1] - 1) // tile_size[1]
    return (cols, rows)


def analyze_collision_from_image(
    image_path: str | Path,
    footprint: tuple[int, int],
    tile_size: tuple[int, int] = (32, 32),
    alpha_threshold: int = 128,
) -> list[tuple[int, int]]:
    """
    Calculate collision cells from alpha channel analysis.

    A tile is marked as blocking if it has significant opaque pixels.

    Args:
        image_path: Path to image file
        footprint: Object footprint [columns, rows]
        tile_size: Base tile size
        alpha_threshold: Minimum alpha to consider pixel opaque

    Returns:
        List of blocking cells in footprint coordinates
    """
    try:
        from PIL import Image
    except ImportError:
        # Default: bottom-center cell blocks
        return [(footprint[0] // 2, footprint[1] - 1)]

    img = Image.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    collision_cells = []

    for row in range(footprint[1]):
        for col in range(footprint[0]):
            # Sample tile region
            x0 = col * tile_size[0]
            y0 = row * tile_size[1]
            x1 = min(x0 + tile_size[0], img.width)
            y1 = min(y0 + tile_size[1], img.height)

            # Count opaque pixels in this tile
            opaque_count = 0
            total_count = 0
            for y in range(y0, y1):
                for x in range(x0, x1):
                    alpha = img.getpixel((x, y))[3]
                    total_count += 1
                    if alpha >= alpha_threshold:
                        opaque_count += 1

            # If more than 25% opaque, mark as blocking
            if total_count > 0 and opaque_count / total_count > 0.25:
                collision_cells.append((col, row))

    # Fallback: if no collision detected, mark bottom-center
    if not collision_cells:
        collision_cells.append((footprint[0] // 2, footprint[1] - 1))

    return collision_cells


def analyze_visual_bounds_from_image(
    image_path: str | Path,
    alpha_threshold: int = 10,
) -> VisualBounds:
    """
    Calculate tight bounding box around visible pixels.

    Args:
        image_path: Path to image file
        alpha_threshold: Minimum alpha to consider pixel visible

    Returns:
        Bounding box as VisualBounds
    """
    try:
        from PIL import Image
    except ImportError:
        # Fallback to full image
        return VisualBounds(x=0, y=0, width=0, height=0)

    img = Image.open(image_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Find bounds of opaque pixels
    min_x, min_y = img.width, img.height
    max_x, max_y = 0, 0

    for y in range(img.height):
        for x in range(img.width):
            alpha = img.getpixel((x, y))[3]
            if alpha >= alpha_threshold:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    # Handle fully transparent image
    if max_x < min_x or max_y < min_y:
        return VisualBounds(x=0, y=0, width=img.width, height=img.height)

    return VisualBounds(
        x=min_x,
        y=min_y,
        width=max_x - min_x + 1,
        height=max_y - min_y + 1,
    )


def infer_anchor_from_footprint(footprint: tuple[int, int]) -> AnchorPoint:
    """
    Infer best anchor point from footprint shape.

    Args:
        footprint: Object footprint [columns, rows]

    Returns:
        Recommended anchor point
    """
    cols, rows = footprint

    # Tall objects (trees, buildings) anchor at bottom
    if rows >= 2:
        return AnchorPoint.BOTTOM_CENTER

    # Wide objects (bridges, roads) anchor at center
    if cols >= 2:
        return AnchorPoint.CENTER

    # Small objects anchor at center
    return AnchorPoint.CENTER


def extract_tags_from_prompt(prompt: str) -> list[str]:
    """
    Extract semantic tags from generation prompt.

    Args:
        prompt: Image generation prompt

    Returns:
        List of extracted tags
    """
    tags = []

    # Common object types
    object_keywords = [
        "tree", "oak", "pine", "palm", "willow",
        "rock", "stone", "boulder",
        "chest", "treasure", "barrel", "crate",
        "house", "building", "temple", "tower", "ruins",
        "bridge", "road", "path", "door", "gate",
        "stall", "shop", "market",
        "lamppost", "statue", "well", "fountain",
        "flower", "bush", "grass",
    ]

    prompt_lower = prompt.lower()
    for keyword in object_keywords:
        if keyword in prompt_lower:
            tags.append(keyword)

    # Common attributes
    if any(word in prompt_lower for word in ["blocking", "solid", "wall"]):
        if "blocking" not in tags:
            tags.append("blocking")

    if any(word in prompt_lower for word in ["decoration", "decorative", "ornament"]):
        if "decoration" not in tags:
            tags.append("decoration")

    if any(word in prompt_lower for word in ["nature", "natural", "plant"]):
        if "nature" not in tags:
            tags.append("nature")

    # Deduplicate while preserving order
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return unique_tags


def extract_theme_from_prompt(prompt: str) -> list[str]:
    """
    Extract theme tags from generation prompt.

    Args:
        prompt: Image generation prompt

    Returns:
        List of extracted themes
    """
    themes = []

    theme_keywords = {
        "forest": ["forest", "woods", "woodland"],
        "village": ["village", "town", "settlement"],
        "dungeon": ["dungeon", "cave", "underground"],
        "desert": ["desert", "sand", "arid"],
        "snow": ["snow", "winter", "ice", "frozen"],
        "mountains": ["mountain", "alpine", "peak"],
        "plains": ["plains", "grassland", "meadow"],
        "ruins": ["ruins", "ancient", "abandoned"],
        "market": ["market", "bazaar", "fair"],
        "temple": ["temple", "shrine", "sanctuary"],
    }

    prompt_lower = prompt.lower()
    for theme, keywords in theme_keywords.items():
        if any(kw in prompt_lower for kw in keywords):
            themes.append(theme)

    return themes


def auto_annotate_metadata(
    image_path: str | Path,
    prompt: str,
    tile_size: tuple[int, int] = (32, 32),
) -> dict[str, Any]:
    """
    Automatically generate complete metadata from image and prompt.

    Args:
        image_path: Path to generated image
        prompt: Generation prompt
        tile_size: Base tile size

    Returns:
        Dictionary with inferred metadata fields
    """
    footprint = analyze_footprint_from_image(image_path, tile_size)
    collision = analyze_collision_from_image(image_path, footprint, tile_size)
    visual_bounds = analyze_visual_bounds_from_image(image_path)
    anchor = infer_anchor_from_footprint(footprint)
    tags = extract_tags_from_prompt(prompt)
    theme = extract_theme_from_prompt(prompt)

    return {
        "footprint": footprint,
        "collision": collision,
        "visual_bounds": {
            "x": visual_bounds.x,
            "y": visual_bounds.y,
            "width": visual_bounds.width,
            "height": visual_bounds.height,
        },
        "anchor": anchor.value,
        "tags": tags,
        "theme": theme,
    }
