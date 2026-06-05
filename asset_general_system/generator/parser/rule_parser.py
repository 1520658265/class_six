from __future__ import annotations

import re
from random import Random

from ..config import VERSION
from ..models import (
    ConstraintsSpec,
    EntitySpec,
    GenerateRequest,
    MapConfig,
    ObjectSpec,
    PathSpec,
    RegionSpec,
    RPGMapSpec,
)
from .base import PromptParser


POSITION_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("top_left", ("左上", "upper left", "top left")),
    ("top_right", ("右上", "upper right", "top right")),
    ("bottom_left", ("左下", "lower left", "bottom left")),
    ("bottom_right", ("右下", "lower right", "bottom right")),
    ("left", ("左侧", "左边", "left")),
    ("right", ("右侧", "右边", "right")),
    ("top", ("上方", "上面", "朝上", "顶部", "北部", "top", "north")),
    ("bottom", ("下方", "下面", "底部", "南部", "bottom", "south")),
    ("center", ("中间", "中央", "中心", "center", "middle")),
]

REGION_KEYWORDS: list[tuple[str, tuple[str, ...], str, int]] = [
    ("river", ("河流", "河", "溪流", "river", "stream"), "medium", 90),
    ("market", ("集市", "市场", "鱼市", "market"), "medium", 85),
    ("temple", ("神庙", "寺庙", "祭坛", "temple", "shrine", "sanctuary"), "small", 80),
    ("entrance", ("入口", "entrance"), "small", 90),
    ("hall", ("大厅", "hall"), "medium", 80),
    ("boss_room", ("boss房", "boss 房", "首领房", "boss room"), "medium", 90),
    ("campfire", ("篝火", "campfire"), "small", 80),
    ("cabin", ("木屋", "小屋", "cabin", "hut"), "small", 75),
    ("altar", ("神坛", "altar"), "small", 80),
    ("ruins", ("遗迹", "废墟", "ruins"), "medium", 80),
    ("dock", ("码头", "dock", "pier"), "medium", 75),
    ("lighthouse", ("灯塔", "lighthouse"), "small", 75),
    ("school", ("学校", "教学楼", "school"), "large", 95),
    ("playground", ("操场", "playground", "sports ground"), "large", 90),
    ("mud_road", ("泥巴路", "泥路", "土路", "mud road", "dirt road"), "medium", 85),
    ("toilet", ("厕所", "卫生间", "toilet", "restroom"), "small", 80),
]


class RulePromptParser(PromptParser):
    def parse(self, request: GenerateRequest) -> RPGMapSpec:
        seed = request.seed if request.seed is not None else self._seed_from_prompt(request.prompt)
        theme = request.theme or self._detect_theme(request.prompt)
        title = self._title_for_theme(theme)
        regions = self._detect_regions(request.prompt, theme)
        entities = self._default_entities(request.prompt, theme)
        objects = self._default_objects(request.prompt, theme, regions)
        paths = self._default_paths(regions)

        width, height = request.map_size
        tile_width, tile_height = request.tile_size
        return RPGMapSpec(
            version=VERSION,
            id=self._id_for(theme, seed),
            title=title,
            theme=theme,
            map=MapConfig(width=width, height=height, tile_width=tile_width, tile_height=tile_height),
            regions=regions,
            paths=paths,
            objects=objects,
            entities=entities,
            constraints=ConstraintsSpec(),
            seed=seed,
            tileset_id=request.tileset_id,
        )

    def _detect_theme(self, prompt: str) -> str:
        lower = prompt.lower()
        if any(word in lower for word in ("学校", "校园", "操场", "厕所", "school", "campus", "playground", "toilet")):
            return "school_campus"
        if any(word in lower for word in ("地牢", "地下城", "dungeon", "boss")):
            return "dungeon"
        if any(word in lower for word in ("雪", "营地", "snow", "camp")):
            return "snow_camp"
        if any(word in lower for word in ("沙漠", "遗迹", "desert", "ruins")):
            return "desert_ruins"
        if any(word in lower for word in ("海边", "渔村", "seaside", "fishing")):
            return "seaside_village"
        if any(word in lower for word in ("秋", "autumn")):
            return "autumn_forest_village"
        return "forest_village"

    def _detect_regions(self, prompt: str, theme: str) -> list[RegionSpec]:
        regions: list[RegionSpec] = []
        prompt_lower = prompt.lower()
        for region_type, keywords, size, priority in REGION_KEYWORDS:
            if any(keyword.lower() in prompt_lower for keyword in keywords):
                regions.append(
                    RegionSpec(
                        id=f"{region_type}_{self._next_index(regions, region_type):02d}",
                        type=region_type,
                        position=self._position_near_keyword(prompt, keywords),
                        size=size,
                        priority=priority,
                    )
                )

        existing = {region.type for region in regions}
        for region in self._theme_default_regions(theme):
            if region.type not in existing:
                regions.append(region)
        return sorted(regions, key=lambda item: item.priority, reverse=True)

    def _theme_default_regions(self, theme: str) -> list[RegionSpec]:
        defaults = {
            "autumn_forest_village": [
                RegionSpec(id="river_01", type="river", position="left", size="medium", priority=90),
                RegionSpec(id="market_01", type="market", position="center", size="medium", priority=85),
                RegionSpec(id="temple_01", type="temple", position="top_right", size="small", priority=80),
            ],
            "forest_village": [
                RegionSpec(id="market_01", type="market", position="center", size="medium", priority=85),
                RegionSpec(id="river_01", type="river", position="left", size="medium", priority=80),
            ],
            "dungeon": [
                RegionSpec(id="entrance_01", type="entrance", position="bottom_left", size="small", priority=90),
                RegionSpec(id="hall_01", type="hall", position="center", size="medium", priority=80),
                RegionSpec(id="boss_room_01", type="boss_room", position="top_right", size="medium", priority=90),
            ],
            "snow_camp": [
                RegionSpec(id="campfire_01", type="campfire", position="center", size="small", priority=85),
                RegionSpec(id="cabin_01", type="cabin", position="top", size="small", priority=75),
            ],
            "desert_ruins": [
                RegionSpec(id="ruins_01", type="ruins", position="center", size="medium", priority=85),
                RegionSpec(id="altar_01", type="altar", position="top_right", size="small", priority=80),
            ],
            "seaside_village": [
                RegionSpec(id="dock_01", type="dock", position="left", size="medium", priority=80),
                RegionSpec(id="market_01", type="market", position="center", size="medium", priority=75),
                RegionSpec(id="lighthouse_01", type="lighthouse", position="top_right", size="small", priority=75),
            ],
            "school_campus": [
                RegionSpec(id="school_01", type="school", position="top", size="large", priority=95),
            ],
        }
        return defaults.get(theme, defaults["forest_village"])

    def _position_near_keyword(self, prompt: str, keywords: tuple[str, ...]) -> str:
        lower = prompt.lower()
        hits = [lower.find(keyword.lower()) for keyword in keywords if lower.find(keyword.lower()) >= 0]
        hit = min(hits) if hits else 0
        window = lower[max(0, hit - 24) : min(len(lower), hit + 24)]
        for position, tokens in POSITION_KEYWORDS:
            if any(token in window for token in tokens):
                return position
        for position, tokens in POSITION_KEYWORDS:
            if any(token in lower for token in tokens):
                return position
        return "random"

    def _default_paths(self, regions: list[RegionSpec]) -> list[PathSpec]:
        key_regions = [region for region in regions if region.type != "river"]
        if not key_regions:
            return []
        paths = [PathSpec(**{"from": "spawn_01", "to": key_regions[0].id, "kind": "dirt_road"})]
        for source, target in zip(key_regions, key_regions[1:]):
            paths.append(PathSpec(**{"from": source.id, "to": target.id, "kind": "dirt_road"}))
        return paths

    def _default_entities(self, prompt: str, theme: str) -> list[EntitySpec]:
        entities = [EntitySpec(id="spawn_01", type="player_spawn", position="bottom_center")]
        lower = prompt.lower()
        if theme in {"forest_village", "autumn_forest_village", "seaside_village"}:
            entities.append(EntitySpec(type="villager", count=self._extract_count(lower, "村民", default=6), placement="near:market_01"))
        if theme == "snow_camp":
            entities.append(EntitySpec(type="guard", count=2, placement="near:campfire_01"))
        if theme == "school_campus" and any(word in lower for word in ("学生", "师生", "student")):
            entities.append(EntitySpec(type="student", count=8, placement="near:playground_01"))
        return entities

    def _default_objects(self, prompt: str, theme: str, regions: list[RegionSpec]) -> list[ObjectSpec]:
        region_types = {region.type for region in regions}
        objects: list[ObjectSpec] = []
        if theme in {"forest_village", "autumn_forest_village"}:
            objects.append(ObjectSpec(type="tree", count=90 if theme == "autumn_forest_village" else 70, placement="forest_edges"))
            objects.append(ObjectSpec(type="rock", count=18, placement="scattered"))
        if theme == "snow_camp":
            objects.append(ObjectSpec(type="pine", count=80, placement="forest_edges"))
            objects.append(ObjectSpec(type="rock", count=12, placement="scattered"))
        if theme == "dungeon":
            objects.append(ObjectSpec(type="rock", count=30, placement="scattered"))
            objects.append(ObjectSpec(type="chest", count=1, placement="near:boss_room_01"))
        if theme == "desert_ruins":
            objects.append(ObjectSpec(type="rock", count=25, placement="scattered"))
        if theme == "school_campus":
            if any(word in prompt for word in ("树", "树木", "树林", "tree", "forest")):
                objects.append(ObjectSpec(type="tree", count=80, placement="campus_edges"))
            if any(word in prompt for word in ("山", "山脉", "mountain", "hill")):
                objects.append(ObjectSpec(type="mountain", count=55, placement="campus_mountains"))
        if "market" in region_types:
            objects.append(ObjectSpec(type="market_stall", count=6, placement="near:market_01"))
        if "campfire" in region_types:
            objects.append(ObjectSpec(type="campfire", count=1, placement="near:campfire_01"))
        return objects

    def _title_for_theme(self, theme: str) -> str:
        return {
            "forest_village": "森林村庄",
            "autumn_forest_village": "秋季森林村庄",
            "dungeon": "小型地下城",
            "snow_camp": "雪地营地",
            "desert_ruins": "沙漠遗迹",
            "seaside_village": "海边渔村",
            "school_campus": "学校建筑场景",
        }.get(theme, "RPG 地图")

    def _id_for(self, theme: str, seed: int) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", f"{theme}_{seed}".lower())

    def _seed_from_prompt(self, prompt: str) -> int:
        rng = Random(prompt)
        return rng.randint(1, 2_147_483_647)

    def _next_index(self, regions: list[RegionSpec], region_type: str) -> int:
        return sum(1 for region in regions if region.type == region_type) + 1

    def _extract_count(self, prompt: str, token: str, default: int) -> int:
        match = re.search(rf"(\d+)\s*个?{re.escape(token)}", prompt)
        return int(match.group(1)) if match else default
