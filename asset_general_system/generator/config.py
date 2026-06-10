from __future__ import annotations

from dataclasses import dataclass


VERSION = "0.1.0"
DEFAULT_MAP_SIZE = (64, 64)
DEFAULT_TILE_SIZE = (32, 32)
DEFAULT_TILESET_ID = "default_rpg_32"


@dataclass(frozen=True)
class TileDef:
    tile_id: int
    name: str
    color: tuple[int, int, int]
    walkable: bool
    tags: tuple[str, ...]


TILES: dict[str, TileDef] = {
    "empty": TileDef(0, "empty", (0, 0, 0), True, ("empty",)),
    "grass": TileDef(1, "grass", (88, 166, 83), True, ("terrain", "grass")),
    "autumn_grass": TileDef(2, "autumn_grass", (155, 147, 74), True, ("terrain", "grass", "autumn")),
    "dirt": TileDef(3, "dirt", (148, 104, 58), True, ("terrain", "dirt")),
    "forest_floor": TileDef(4, "forest_floor", (87, 122, 62), True, ("terrain", "forest")),
    "water": TileDef(5, "water", (55, 129, 184), False, ("terrain", "water", "blocking")),
    "snow": TileDef(6, "snow", (218, 233, 238), True, ("terrain", "snow")),
    "sand": TileDef(7, "sand", (214, 185, 111), True, ("terrain", "sand")),
    "stone_floor": TileDef(8, "stone_floor", (119, 119, 122), True, ("terrain", "stone")),
    "wall": TileDef(9, "wall", (70, 67, 73), False, ("building", "wall", "blocking")),
    "dirt_road": TileDef(10, "dirt_road", (185, 139, 80), True, ("path", "road")),
    "bridge": TileDef(11, "bridge", (139, 91, 53), True, ("path", "bridge")),
    "house": TileDef(12, "house", (136, 84, 62), False, ("building", "house", "blocking")),
    "temple": TileDef(13, "temple", (169, 160, 129), False, ("building", "temple", "blocking")),
    "market_stall": TileDef(14, "market_stall", (192, 76, 73), False, ("object", "stall", "blocking")),
    "tree": TileDef(15, "tree", (39, 102, 54), False, ("decoration", "tree", "blocking")),
    "pine": TileDef(16, "pine", (38, 94, 84), False, ("decoration", "pine", "blocking")),
    "rock": TileDef(17, "rock", (103, 104, 101), False, ("decoration", "rock", "blocking")),
    "campfire": TileDef(18, "campfire", (232, 111, 42), True, ("object", "campfire")),
    "chest": TileDef(19, "chest", (178, 120, 39), False, ("object", "chest", "blocking")),
    "door": TileDef(20, "door", (101, 58, 37), True, ("object", "door")),
    "ruin_wall": TileDef(21, "ruin_wall", (143, 126, 91), False, ("building", "ruin", "blocking")),
    "dock": TileDef(22, "dock", (121, 83, 52), True, ("path", "dock")),
    "lighthouse": TileDef(23, "lighthouse", (205, 208, 198), False, ("building", "lighthouse", "blocking")),
    "mountain": TileDef(24, "mountain", (85, 94, 88), False, ("terrain", "mountain", "blocking")),
    "school": TileDef(25, "school", (188, 176, 137), False, ("building", "school", "blocking")),
    "playground": TileDef(26, "playground", (181, 91, 63), True, ("terrain", "playground", "walkable")),
    "toilet": TileDef(27, "toilet", (178, 184, 174), False, ("building", "toilet", "blocking")),
    "mud_rut": TileDef(28, "mud_rut", (122, 83, 45), True, ("ground_detail", "road", "rut", "walkable")),
    "puddle": TileDef(29, "puddle", (82, 118, 130), True, ("ground_detail", "road", "water", "walkable")),
    "wild_grass": TileDef(30, "wild_grass", (73, 132, 61), True, ("ground_detail", "grass", "walkable")),
    "wild_flower": TileDef(31, "wild_flower", (218, 177, 91), True, ("ground_detail", "flower", "walkable")),
    "worn_playground": TileDef(32, "worn_playground", (139, 74, 48), True, ("ground_detail", "playground", "worn", "walkable")),
    "wheat_field": TileDef(33, "wheat_field", (218, 183, 67), True, ("terrain", "wheat", "field", "walkable")),
}

TILE_ID_BY_NAME = {tile.name: tile.tile_id for tile in TILES.values()}
TILE_BY_ID = {tile.tile_id: tile for tile in TILES.values()}
BLOCKING_TILE_IDS = {tile.tile_id for tile in TILES.values() if not tile.walkable}
PATH_TILE_IDS = {TILE_ID_BY_NAME["dirt_road"], TILE_ID_BY_NAME["bridge"], TILE_ID_BY_NAME["dock"]}


THEME_DEFAULT_TERRAIN = {
    "forest_village": "grass",
    "autumn_forest_village": "autumn_grass",
    "dungeon": "stone_floor",
    "snow_camp": "snow",
    "desert_ruins": "sand",
    "seaside_village": "grass",
    "school_campus": "grass",
    "golden_rice_field": "wheat_field",
}
