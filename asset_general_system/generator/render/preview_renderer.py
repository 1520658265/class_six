from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from ..config import TILE_BY_ID, TILES
from ..models import TilemapData


class PreviewRenderer:
    def render(self, tilemap: TilemapData, output_path: str | Path, debug: bool = False) -> None:
        output_path = Path(output_path)
        image = self.render_image(tilemap, debug=debug)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            image.save(output_path)
        finally:
            image.close()

    def render_image(self, tilemap: TilemapData, debug: bool = False) -> Image.Image:
        width = tilemap.map.width
        height = tilemap.map.height
        tile_width = tilemap.map.tile_width
        tile_height = tilemap.map.tile_height
        image = Image.new("RGB", (width * tile_width, height * tile_height), (0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")

        for layer_name in ("terrain", "path", "building", "decoration"):
            layer = tilemap.layers[layer_name]
            for y in range(height):
                for x in range(width):
                    tile_id = layer[y * width + x]
                    if tile_id == 0:
                        continue
                    color = TILE_BY_ID.get(tile_id, TILE_BY_ID[0]).color
                    rect = [x * tile_width, y * tile_height, (x + 1) * tile_width, (y + 1) * tile_height]
                    draw.rectangle(rect, fill=color)
                    if layer_name in {"building", "decoration"}:
                        draw.rectangle(rect, outline=(34, 34, 34, 90))

        for obj in tilemap.objects:
            cx = obj.x * tile_width + tile_width // 2
            cy = obj.y * tile_height + tile_height // 2
            color = (255, 235, 95, 220) if obj.type != "door" else (70, 38, 24, 240)
            draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=color, outline=(30, 30, 30, 180))

        for event in tilemap.events:
            if event.type == "player_spawn":
                cx = event.x * tile_width + tile_width // 2
                cy = event.y * tile_height + tile_height // 2
                draw.polygon([(cx, cy - 10), (cx - 9, cy + 8), (cx + 9, cy + 8)], fill=(50, 220, 95, 240))

        if debug:
            self._draw_debug(tilemap, draw)

        return image

    def ensure_tileset_png(self, path: str | Path) -> None:
        path = Path(path)
        if path.exists():
            return
        tile_width = 32
        tile_height = 32
        columns = 16
        rows = 2
        image = Image.new("RGBA", (columns * tile_width, rows * tile_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        for tile in TILES.values():
            if tile.tile_id <= 0:
                continue
            index = tile.tile_id - 1
            x = (index % columns) * tile_width
            y = (index // columns) * tile_height
            draw.rectangle([x, y, x + tile_width - 1, y + tile_height - 1], fill=tile.color + (255,))
            draw.rectangle([x, y, x + tile_width - 1, y + tile_height - 1], outline=(30, 30, 30, 120))
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)

    def _draw_debug(self, tilemap: TilemapData, draw: ImageDraw.ImageDraw) -> None:
        tile_width = tilemap.map.tile_width
        tile_height = tilemap.map.tile_height
        width = tilemap.map.width
        for y in range(tilemap.map.height):
            for x in range(width):
                if tilemap.layers["collision"][y * width + x]:
                    rect = [x * tile_width, y * tile_height, (x + 1) * tile_width, (y + 1) * tile_height]
                    draw.rectangle(rect, fill=(210, 45, 45, 70))
        for region in tilemap.regions:
            x, y, w, h = region.bounds
            rect = [x * tile_width, y * tile_height, (x + w) * tile_width, (y + h) * tile_height]
            draw.rectangle(rect, outline=(255, 255, 255, 190), width=2)
            ax, ay = region.access
            draw.rectangle(
                [ax * tile_width + 8, ay * tile_height + 8, (ax + 1) * tile_width - 8, (ay + 1) * tile_height - 8],
                outline=(40, 240, 255, 230),
                width=2,
            )
