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

SCHOOL_OBJECT_KEYWORDS: list[tuple[str, tuple[str, ...], int, str]] = [
    ("dormitory", ("宿舍", "学生宿舍", "寄宿", "dormitory"), 1, "upper_left"),
    ("laundry_line", ("晾衣绳", "红领巾", "校服"), 1, "near:dormitory_01"),
    ("school_shop", ("小卖部", "玻璃柜台", "辣条", "冰棍", "跳跳糖", "健力宝", "shop"), 1, "upper_right"),
    ("shop_goods", ("辣条", "冰棍", "跳跳糖", "健力宝", "玻璃柜台"), 1, "near:school_shop_01"),
    ("dining_hall", ("食堂", "蒸饭", "饭盒", "烟囱"), 1, "upper_right"),
    ("chimney_smoke", ("烟囱", "炊烟", "白烟"), 1, "near:dining_hall_01"),
    ("lunch_box_stack", ("饭盒", "铝制饭盒"), 3, "near:dining_hall_01"),
    ("coal_pile", ("煤堆",), 1, "near:dining_hall_01"),
    ("firewood_pile", ("柴堆",), 1, "near:dining_hall_01"),
    ("rice_washing_pool", ("淘米池", "水龙头", "淘米"), 1, "near:dining_hall_01"),
    ("student_rice_washing", ("淘米", "蹲在池边"), 3, "near:rice_washing_pool_01"),
    ("school_sign", ("丁埠小学", "招牌", "大字"), 1, "school_facade"),
    ("school_slogan_banner", ("好好学习", "百年大计", "德智体美劳", "北京欢迎你", "同一个世界", "标语"), 5, "school_facade"),
    ("rail_bell", ("铁轨", "上课铃"), 1, "school_facade"),
    ("olympic_poster", ("福娃", "奥运"), 1, "school_facade"),
    ("flag_pole", ("升旗台", "五星红旗", "旗杆"), 1, "school_front"),
    ("basketball_hoop", ("篮球架",), 1, "playground"),
    ("horizontal_bar", ("单杠",), 1, "playground"),
    ("parallel_bars", ("双杠",), 1, "playground"),
    ("ping_pong_table", ("乒乓球台", "乒乓"), 1, "playground"),
    ("power_pole_speaker", ("电线杆", "高音喇叭", "喇叭"), 1, "playground"),
    ("water_well", ("压水井", "水井"), 1, "playground"),
    ("student_activity", ("跳皮筋", "滚铁环", "踢毽子", "弹珠"), 4, "playground"),
    ("bicycle", ("自行车", "28 大杠", "二八大杠"), 1, "mud_road"),
    ("dog", ("狗", "土黄狗"), 2, "mud_road"),
    ("chicken", ("鸡", "土鸡"), 4, "mud_road"),
]

CHINESE_DIGITS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

CUSTOM_OBJECT_MEASURES = "个只条张座根口间栋辆棵朵盆块台把面扇摞排"
CUSTOM_OBJECT_SUFFIXES = (
    "黑板报",
    "广播室",
    "告示牌",
    "宣传栏",
    "公告栏",
    "花坛",
    "花盆",
    "水桶",
    "垃圾桶",
    "储物柜",
    "储物箱",
    "课桌",
    "长椅",
    "板凳",
    "柜台",
    "栏杆",
    "海报",
    "标语",
    "招牌",
    "旗杆",
    "水井",
    "路灯",
    "室",
    "房",
    "亭",
    "棚",
    "坛",
    "盆",
    "桶",
    "箱",
    "柜",
    "桌",
    "椅",
    "凳",
    "牌",
    "报",
    "灯",
    "井",
    "杆",
    "台",
    "架",
    "池",
    "堆",
    "车",
    "桥",
    "门",
    "窗",
)
CUSTOM_OBJECT_ACTIONS = (
    "有",
    "增加",
    "新增",
    "放置",
    "摆放",
    "摆着",
    "堆着",
    "挂着",
    "贴着",
    "停着",
    "种着",
    "码着",
    "建",
    "画着",
)
CUSTOM_OBJECT_SPLIT_PATTERN = re.compile(r"[。；;.!?\n]")
CUSTOM_OBJECT_ITEM_SPLIT_PATTERN = re.compile(r"[、,，和与及]")
CUSTOM_OBJECT_IGNORE_LABELS = {
    "地图",
    "俯视图",
    "像素风",
    "风格",
    "画风",
    "元素",
    "布局",
    "画面",
    "氛围",
    "阳光",
    "蓝天",
    "白云",
    "远景",
    "轮廓",
    "方向",
    "尺寸",
    "素材",
    "学校",
    "校园",
    "教学楼",
    "操场",
    "泥巴路",
    "泥路",
    "土路",
    "厕所",
    "卫生间",
    "山林",
    "树林",
}
KNOWN_OBJECT_KEYWORDS = {
    keyword
    for _object_type, keywords, _count, _placement in SCHOOL_OBJECT_KEYWORDS
    for keyword in keywords
} | {
    keyword
    for _region_type, keywords, _size, _priority in REGION_KEYWORDS
    for keyword in keywords
}


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
            if any(word in prompt for word in ("松树", "杉树", "pine", "cedar")):
                objects.append(ObjectSpec(type="pine", count=45, placement="campus_edges"))
            if any(word in prompt for word in ("山", "山脉", "mountain", "hill")):
                objects.append(ObjectSpec(type="mountain", count=55, placement="campus_mountains"))
            for object_type, keywords, default_count, placement in SCHOOL_OBJECT_KEYWORDS:
                if any(keyword.lower() in prompt.lower() for keyword in keywords):
                    count = self._extract_count_near_keywords(prompt, keywords, default_count)
                    objects.append(ObjectSpec(type=object_type, count=count, placement=placement))
            objects.extend(self._extract_custom_objects(prompt, theme))
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

    def _extract_count_near_keywords(self, prompt: str, keywords: tuple[str, ...], default: int) -> int:
        lower = prompt.lower()
        hits = [lower.find(keyword.lower()) for keyword in keywords if lower.find(keyword.lower()) >= 0]
        if not hits:
            return default
        hit = min(hits)
        prefix = prompt[max(0, hit - 8) : hit]
        digit_matches = list(re.finditer(r"(\d+)\s*[个只条张座根口间栋]", prefix))
        digit_match = digit_matches[-1] if digit_matches else None
        if digit_match:
            return int(digit_match.group(1))
        chinese_matches = list(re.finditer(r"([一二两三四五六七八九十])\s*[个只条张座根口间栋]", prefix))
        chinese_match = chinese_matches[-1] if chinese_matches else None
        if chinese_match:
            return CHINESE_DIGITS[chinese_match.group(1)]
        return default

    def _extract_custom_objects(self, prompt: str, theme: str) -> list[ObjectSpec]:
        if theme != "school_campus":
            return []

        objects: list[ObjectSpec] = []
        seen: set[str] = set()
        suffix_pattern = "|".join(re.escape(suffix) for suffix in sorted(CUSTOM_OBJECT_SUFFIXES, key=len, reverse=True))
        quantified_pattern = re.compile(
            rf"(?P<count>\d+|[一二两三四五六七八九十几数多]+)\s*[{CUSTOM_OBJECT_MEASURES}]\s*"
            rf"(?P<label>[A-Za-z0-9 \u4e00-\u9fff]{{1,16}})"
        )
        suffix_pattern_re = re.compile(rf"(?P<label>[A-Za-z0-9 \u4e00-\u9fff]{{0,10}}(?:{suffix_pattern}))")

        for clause in self._custom_object_clauses(prompt):
            for match in quantified_pattern.finditer(clause):
                label = self._clean_custom_label(match.group("label"))
                if self._should_skip_custom_label(label, seen):
                    continue
                count = self._parse_count_token(match.group("count"), default=1)
                seen.add(label)
                objects.append(self._custom_object_spec(label, count, clause))

            if not any(action in clause for action in CUSTOM_OBJECT_ACTIONS):
                continue
            for segment in CUSTOM_OBJECT_ITEM_SPLIT_PATTERN.split(clause):
                for match in suffix_pattern_re.finditer(segment):
                    label = self._clean_custom_label(match.group("label"))
                    if self._should_skip_custom_label(label, seen):
                        continue
                    seen.add(label)
                    objects.append(self._custom_object_spec(label, 1, clause))

        return objects

    def _custom_object_clauses(self, prompt: str) -> list[str]:
        clauses = []
        for clause in CUSTOM_OBJECT_SPLIT_PATTERN.split(prompt):
            clause = clause.strip()
            if not clause:
                continue
            if any(action in clause for action in CUSTOM_OBJECT_ACTIONS) or re.search(rf"(\d+|[一二两三四五六七八九十几数多]+)\s*[{CUSTOM_OBJECT_MEASURES}]", clause):
                clauses.append(clause)
        return clauses

    def _custom_object_spec(self, label: str, count: int, source_clause: str) -> ObjectSpec:
        placement = self._infer_custom_object_placement(source_clause, label)
        return ObjectSpec(
            type="custom_object",
            count=count,
            placement=placement,
            label=label,
            properties={
                "display_name": label,
                "source": "prompt_fallback",
                "source_clause": source_clause[:120],
            },
        )

    def _infer_custom_object_placement(self, clause: str, label: str) -> str:
        text = f"{clause}{label}"
        if any(word in text for word in ("宿舍", "晾衣")):
            return "near:dormitory_01"
        if any(word in text for word in ("小卖部", "柜台")):
            return "near:school_shop_01"
        if any(word in text for word in ("食堂", "淘米", "烟囱", "饭盒", "煤", "柴")):
            return "near:dining_hall_01"
        if any(word in text for word in ("操场", "篮球", "单杠", "双杠", "乒乓", "活动")):
            return "playground"
        if any(word in text for word in ("泥巴路", "泥路", "土路", "路边", "路上", "车辙")):
            return "mud_road"
        if any(word in text for word in ("教学楼", "正墙", "走廊", "门口", "招牌", "海报", "标语", "黑板报")):
            return "school_facade" if any(word in text for word in ("正墙", "走廊", "招牌", "海报", "标语", "黑板报")) else "school_front"
        if any(word in text for word in ("上方", "山林", "树林", "林", "山")):
            return "campus_edges"
        if any(word in text for word in ("厕所", "卫生间")):
            return "near:toilet_01"
        return "school_front"

    def _clean_custom_label(self, label: str) -> str:
        cleaned = label.strip(" ，,。；;:：()（）[]【】")
        cleaned = re.sub(rf"^(\d+|[一二两三四五六七八九十几数多]+)\s*[{CUSTOM_OBJECT_MEASURES}]", "", cleaned)
        cleaned = re.sub(r"^(最)?(上方|下方|左边|右边|前方|后方|中上方|中下方|画面正中|正墙上|门口)", "", cleaned)
        for token in ("还有", "以及", "并且", "旁边", "前方", "后方", "左边", "右边", "里面", "外面", "门口"):
            if token in cleaned:
                cleaned = cleaned.split(token)[-1]
        for token in CUSTOM_OBJECT_ACTIONS:
            if token in cleaned:
                cleaned = cleaned.split(token)[-1]
        for token in ("在", "位于", "用于", "作为", "用", "里能看到", "能看到"):
            if token in cleaned:
                cleaned = cleaned.split(token)[0]
        cleaned = re.sub(rf"^(\d+|[一二两三四五六七八九十几数多]+)\s*[{CUSTOM_OBJECT_MEASURES}]", "", cleaned)
        cleaned = re.sub(r"^(最)?(上方|下方|左边|右边|前方|后方|中上方|中下方|画面正中|正墙上|门口)", "", cleaned)
        cleaned = cleaned.replace("的", "").strip(" ，,。；;:：")
        return cleaned[:16]

    def _should_skip_custom_label(self, label: str, seen: set[str]) -> bool:
        if len(label) < 2 or label in seen or label in CUSTOM_OBJECT_IGNORE_LABELS:
            return True
        if label in {"正墙上", "墙上", "画面正中", "世界同一个梦想", "同一个世界同一个梦想"}:
            return True
        if label.endswith(("上", "中", "里", "边")) and not any(label.endswith(suffix) for suffix in CUSTOM_OBJECT_SUFFIXES):
            return True
        if any(ignored in label for ignored in CUSTOM_OBJECT_IGNORE_LABELS):
            return True
        if any(keyword and keyword in label for keyword in KNOWN_OBJECT_KEYWORDS):
            return True
        if any(word in label for word in ("学生", "老师", "小学生", "村民", "NPC", "角色")):
            return True
        return False

    def _parse_count_token(self, token: str, default: int) -> int:
        if token.isdigit():
            return int(token)
        if token in {"几", "数"}:
            return 3
        if token == "多":
            return 4
        if token in CHINESE_DIGITS:
            return CHINESE_DIGITS[token]
        if token.startswith("十") and len(token) == 2 and token[1] in CHINESE_DIGITS:
            return 10 + CHINESE_DIGITS[token[1]]
        if token.endswith("十") and token[0] in CHINESE_DIGITS:
            return CHINESE_DIGITS[token[0]] * 10
        if len(token) == 3 and token[1] == "十" and token[0] in CHINESE_DIGITS and token[2] in CHINESE_DIGITS:
            return CHINESE_DIGITS[token[0]] * 10 + CHINESE_DIGITS[token[2]]
        return default
