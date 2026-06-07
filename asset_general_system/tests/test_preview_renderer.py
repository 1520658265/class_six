from generator.map import MapGenerator
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.render import PreviewRenderer


def test_preview_renderer_builds_preview_image():
    spec = RulePromptParser().parse(
        GenerateRequest(
            prompt="生成一个雪地营地，四周是松树，中间有篝火和三间木屋",
            seed=20260607,
        )
    )
    tilemap = MapGenerator().generate(spec)

    image = PreviewRenderer().render_image(tilemap)

    assert image.size == (64 * 32, 64 * 32)
    assert image.getbbox() is not None
    image.close()
