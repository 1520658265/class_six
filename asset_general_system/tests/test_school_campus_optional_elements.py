from generator.map import MapGenerator
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
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

