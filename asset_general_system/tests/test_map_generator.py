from generator.map import MapGenerator
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.validation import Validator


PROMPTS = [
    (
        "生成一个秋季森林村庄，左侧有河流，中间有集市，右上角有神庙，村民可以在道路上行走",
        20260605,
        "autumn_forest_village",
    ),
    (
        "生成一个小型地下城，入口在左下角，中心有大厅，右上角有 boss 房间，还有一个宝箱",
        20260606,
        "dungeon",
    ),
    (
        "生成一个雪地营地，四周是松树，中间有篝火和三间木屋，安排巡逻 NPC",
        20260607,
        "snow_camp",
    ),
]


def test_map_generator_outputs_valid_core_theme_maps():
    parser = RulePromptParser()
    generator = MapGenerator()
    validator = Validator()

    for prompt, seed, theme in PROMPTS:
        spec = parser.parse(GenerateRequest(prompt=prompt, seed=seed))
        tilemap = generator.generate(spec)
        report = validator.validate(tilemap)

        assert spec.theme == theme
        assert report.passed, report.model_dump()
        assert tilemap.map.width == 64
        assert tilemap.map.height == 64
        assert set(tilemap.layers) == {"terrain", "path", "building", "decoration", "collision"}
        assert all(len(layer) == 64 * 64 for layer in tilemap.layers.values())
        assert tilemap.events
        assert tilemap.regions

