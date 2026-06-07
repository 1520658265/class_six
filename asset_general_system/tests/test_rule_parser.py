from generator.models import GenerateRequest
from generator.parser import RulePromptParser


def test_rule_parser_detects_autumn_village_regions():
    request = GenerateRequest(
        prompt="生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙",
        seed=20260605,
    )

    spec = RulePromptParser().parse(request)

    assert spec.theme == "autumn_forest_village"
    assert spec.map.width == 64
    assert spec.map.height == 64
    assert {region.type for region in spec.regions} >= {"river", "market", "temple"}
    assert any(entity.type == "player_spawn" for entity in spec.entities)


def test_rule_parser_detects_dungeon_theme():
    request = GenerateRequest(
        prompt="生成一个小型地下城，入口在左下角，中心有大厅，右上角有 boss 房间",
        seed=20260606,
    )

    spec = RulePromptParser().parse(request)

    assert spec.theme == "dungeon"
    assert {region.type for region in spec.regions} >= {"entrance", "hall", "boss_room"}

