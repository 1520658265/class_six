from generator.map import MapGenerator
from generator.config import TILE_ID_BY_NAME
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.export import TiledExporter, TiledJsonValidator
from generator.validation import Validator


def _build(prompt: str):
    spec = RulePromptParser().parse(GenerateRequest(prompt=prompt, seed=20260608))
    tilemap = MapGenerator().generate(spec)
    report = Validator().validate(tilemap)
    assert report.passed, report.model_dump()
    return spec, tilemap


def test_school_prompt_with_toilet_places_toilet_region():
    spec, tilemap = _build("生成一个学校建筑，位于中间朝上，下面是操场，操场下面是一条从左贯穿到右的泥巴路，路的尽头是一间厕所。")

    assert {region.type for region in spec.regions} >= {"school", "playground", "mud_road", "toilet"}
    assert "toilet" in {region.type for region in tilemap.regions}
    assert any(obj.id == "toilet_01_door" for obj in tilemap.objects)


def test_school_prompt_without_toilet_does_not_place_toilet_region():
    spec, tilemap = _build("生成一个学校建筑，位于中间朝上，上左右是山和树木，下面是操场，操场下面是一条从左贯穿到右的泥巴路。")

    assert {region.type for region in spec.regions} >= {"school", "playground", "mud_road"}
    assert "toilet" not in {region.type for region in spec.regions}
    assert "toilet" not in {region.type for region in tilemap.regions}
    assert not any(obj.id == "toilet_01_door" for obj in tilemap.objects)


def test_complex_boarding_school_prompt_preserves_rpg_tilemap_elements():
    prompt = (
        "可爱像素风 RPG 地图俯视图，2008 年中国安徽金寨大别山区的丁埠乡村寄宿小学。"
        "最上方是山林和杉树松树；中上方左边是一栋学生宿舍楼，二楼外挂晾衣绳，"
        "上面有红领巾和蓝白校服。宿舍楼右边是一间挂着小卖部木牌的平房，"
        "玻璃柜台里有辣条、冰棍、跳跳糖、健力宝。小卖部前方是蒸饭食堂，"
        "砖砌烟囱冒着白烟，门口堆着铝制饭盒，墙边有煤堆和柴堆。"
        "食堂左前方是一座长条形水泥淘米池，有多个生锈水龙头，几个小学生蹲在池边淘米。"
        "画面正中是四到五层红砖白墙教学楼，正墙竖排红色大字丁埠小学，"
        "每层有标语：好好学习 天天向上、百年大计 教育为本、德智体美劳 全面发展、"
        "北京欢迎你 2008、同一个世界同一个梦想，屋檐下挂着废弃铁轨当上课铃，"
        "走廊里贴着 2008 北京奥运福娃海报。教学楼正前方是升旗台和五星红旗旗杆。"
        "教学楼下方是黄泥土操场，有篮球架、单杠双杠、水泥乒乓球台、"
        "木电线杆高音喇叭、压水井，学生在跳皮筋、滚铁环、踢毽子、弹珠。"
        "最下方是一条黄土泥巴路，靠墙停着一辆 28 大杠老式自行车，"
        "两条土黄狗在路上散步，几只散养土鸡在啄食，路的最右端是一间旱厕厕所。"
    )

    spec = RulePromptParser().parse(GenerateRequest(prompt=prompt, map_size=(96, 96), seed=20260608))
    parsed_object_types = {obj.type for obj in spec.objects}

    assert parsed_object_types >= {
        "dormitory",
        "school_shop",
        "dining_hall",
        "rice_washing_pool",
        "flag_pole",
        "basketball_hoop",
        "ping_pong_table",
        "power_pole_speaker",
        "water_well",
        "bicycle",
        "dog",
        "chicken",
        "school_slogan_banner",
    }

    tilemap = MapGenerator().generate(spec)
    report = Validator().validate(tilemap)
    assert report.passed, report.model_dump()

    generated_region_types = {region.type for region in tilemap.regions}
    generated_object_types = {obj.type for obj in tilemap.objects}

    assert generated_region_types >= {"school", "playground", "mud_road", "toilet", "dormitory", "school_shop", "dining_hall"}
    assert generated_object_types >= {
        "laundry_line",
        "shop_goods",
        "chimney_smoke",
        "lunch_box_stack",
        "coal_pile",
        "firewood_pile",
        "rice_washing_pool",
        "student_rice_washing",
        "school_sign",
        "school_slogan_banner",
        "rail_bell",
        "olympic_poster",
        "flag_pole",
        "basketball_hoop",
        "horizontal_bar",
        "parallel_bars",
        "ping_pong_table",
        "power_pole_speaker",
        "water_well",
        "student_activity",
        "bicycle",
        "dog",
        "chicken",
    }
    assert sum(1 for obj in tilemap.objects if obj.type == "dog") == 2
    assert any(obj.properties.get("text") == "北京欢迎你 2008" for obj in tilemap.objects)
    decoration_tiles = set(tilemap.layers["decoration"])
    assert TILE_ID_BY_NAME["mud_rut"] in decoration_tiles
    assert TILE_ID_BY_NAME["puddle"] in decoration_tiles
    assert TILE_ID_BY_NAME["worn_playground"] in decoration_tiles
    assert TILE_ID_BY_NAME["wild_grass"] in decoration_tiles or TILE_ID_BY_NAME["wild_flower"] in decoration_tiles
    assert tilemap.metadata["ground_detail_report"]["details"]["mud_rut"] > 0
    assert tilemap.metadata["ground_detail_report"]["details"]["worn_playground"] > 0
    assert TiledJsonValidator().validate(TiledExporter().to_dict(tilemap)).passed


def test_school_ground_details_are_walkable_and_not_objects():
    prompt = (
        "学校地图，有教学楼、操场和黄土泥巴路。"
        "泥巴路有车辙水洼，路边有野草杂花，操场是磨损的黄泥地。"
    )
    spec = RulePromptParser().parse(GenerateRequest(prompt=prompt, map_size=(64, 64), seed=808))
    tilemap = MapGenerator().generate(spec)

    detail_ids = {
        TILE_ID_BY_NAME["mud_rut"],
        TILE_ID_BY_NAME["puddle"],
        TILE_ID_BY_NAME["wild_grass"],
        TILE_ID_BY_NAME["wild_flower"],
        TILE_ID_BY_NAME["worn_playground"],
    }
    detail_positions = [
        index
        for index, tile_id in enumerate(tilemap.layers["decoration"])
        if tile_id in detail_ids
    ]

    assert detail_positions
    assert all(tilemap.layers["collision"][index] == 0 for index in detail_positions)
    assert not any(obj.type in {"mud_rut", "puddle", "wild_grass", "wild_flower", "worn_playground"} for obj in tilemap.objects)
    assert Validator().validate(tilemap).passed


def test_school_prompt_preserves_unknown_elements_as_custom_objects():
    prompt = (
        "学校地图，有教学楼和操场。操场旁边增加3个红色水桶，"
        "教学楼门口贴着黑板报，宿舍旁边有广播室和花坛。"
    )

    spec = RulePromptParser().parse(GenerateRequest(prompt=prompt, map_size=(64, 64), seed=606))
    custom_specs = [obj for obj in spec.objects if obj.type == "custom_object"]
    labels = {obj.label for obj in custom_specs}

    assert labels >= {"红色水桶", "黑板报", "广播室", "花坛"}
    assert next(obj for obj in custom_specs if obj.label == "红色水桶").count == 3

    tilemap = MapGenerator().generate(spec)
    custom_objects = [obj for obj in tilemap.objects if obj.type == "custom_object"]
    generated_labels = [obj.properties.get("label") for obj in custom_objects]

    assert generated_labels.count("红色水桶") == 3
    assert {"黑板报", "广播室", "花坛"} <= set(generated_labels)
    assert all(obj.properties.get("source") == "prompt_fallback" for obj in custom_objects)
    assert Validator().validate(tilemap).passed
    assert TiledJsonValidator().validate(TiledExporter().to_dict(tilemap)).passed


def test_school_custom_object_labels_are_clean_for_sprite_generation():
    prompt = (
        "学校地图，教学楼正墙上增加一条绿色铁栏杆，"
        "顶楼写着同一个世界同一个梦想，操场边增加2个红色水桶。"
    )

    spec = RulePromptParser().parse(GenerateRequest(prompt=prompt, map_size=(64, 64), seed=707))
    labels = {obj.label for obj in spec.objects if obj.type == "custom_object"}

    assert "绿色铁栏杆" in labels
    assert "一条绿色铁栏杆" not in labels
    assert "同一个世界同一个梦想" not in labels
    assert "红色水桶" in labels
