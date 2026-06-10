from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from generator.assets.image_generation import ImageGenerationRequest, ImageStyle, TransparencyMode
from generator.assets.pixai_generator import PixAIImageGenerator, _pixen_generation_size
from generator.models.base import read_json
from generator.scene.background_plan import build_background_plan, extract_background_tiles, write_background_review_html
from generator.scene.cli import main as scene_cli_main
from generator.scene.concept import generate_scene_concept
from generator.scene.images import generate_scene_images
from generator.scene.map_build import build_scene_map
from generator.scene.pack import pack_scene
from generator.scene.validation import validate_scene_file


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "scenes" / "dingbu_primary_school_1998"
RICE_FIELD_EXAMPLE = ROOT / "examples" / "scenes" / "rice_field_test"
TEST_WORK = ROOT / "tmp" / "test_scene_pipeline"


def copy_scene(name: str) -> Path:
    scene = TEST_WORK / f"{name}_{os.getpid()}_{uuid.uuid4().hex}"
    scene.mkdir(parents=True)
    for name in ["scene.md", "map_spec.json", "style_profile.json", "entities.json", "prompts.json"]:
        shutil.copyfile(EXAMPLE / name, scene / name)
    return scene


def test_scene_validate_accepts_example():
    scene = copy_scene("validate_accepts_example")

    assert not [issue for issue in validate_scene_file(scene, "spec") if issue.severity == "error"]


def test_scene_validate_rejects_unknown_category():
    scene = copy_scene("rejects_unknown_category")
    spec = read_json(scene / "map_spec.json")
    spec["objects"][0]["type"] = "custom_object"
    (scene / "map_spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")

    issues = validate_scene_file(scene, "spec")

    assert any("unknown category" in issue.message for issue in issues)


def test_scene_map_build_writes_art_request_with_source_canvas():
    scene = copy_scene("map_build_art_request")

    build_scene_map(scene, force=True)
    art_request = read_json(scene / "art_request.json")

    objects = {item["id"]: item for item in art_request["objects"]}
    assert objects["ping_pong_table_01"]["category"] == "large_prop"
    assert objects["ping_pong_table_01"]["footprint"] == [3, 2]
    assert objects["ping_pong_table_01"]["source_canvas"] == [128, 96]
    assert objects["notice_board_01"]["attached_to"] == "school_01"


def test_scene_images_target_and_pack_emit_sprite2d_and_label():
    scene = copy_scene("images_target_pack")
    build_scene_map(scene, force=True)

    generated = generate_scene_images(scene, force=True, target="notice_board_01")
    manifest = pack_scene(scene, force=True)
    tscn = (scene / "final" / "scene.tscn").read_text(encoding="utf-8")

    assert generated == ["notice_board_01"]
    assert (scene / "images" / "notice_board_01.png").exists()
    assert manifest["metadata"]["generated_count"] == 1
    assert 'type="Sprite2D"' in tscn
    assert 'name="TextLabel" type="Label"' in tscn
    assert 'metadata/text = "通知"' in tscn


def test_scene_images_cli_accepts_pixai_backend_for_cached_target():
    scene = copy_scene("images_cli_pixai_cached")
    build_scene_map(scene, force=True)
    generate_scene_images(scene, force=True, target="notice_board_01")

    code = scene_cli_main([
        "scene-images",
        str(scene),
        "--pixai",
        "--target",
        "notice_board_01",
    ])

    assert code == 0


def test_pixai_backend_defaults_to_v2_script_and_legal_pixen_sizes():
    assert PixAIImageGenerator.default_script_path().name == "pixellab_v2_client.py"
    assert _pixen_generation_size((64, 64)) == (64, 64)
    assert _pixen_generation_size((576, 576)) == (512, 512)
    assert _pixen_generation_size((576, 448)) == (512, 400)
    assert _pixen_generation_size((16, 16)) == (32, 32)


def test_pixai_backend_loads_v2_client_and_resizes_large_result():
    work_dir = TEST_WORK / f"pixai_backend_{os.getpid()}_{uuid.uuid4().hex}"
    work_dir.mkdir(parents=True)
    script = work_dir / "fake_pixellab_v2_client.py"
    script.write_text(
        "\n".join(
            [
                "from dataclasses import dataclass",
                "from PIL import Image",
                "",
                "@dataclass",
                "class GenerationResult:",
                "    image: object",
                "    usage: dict",
                "",
                "class PixelLabV2Client:",
                "    def __init__(self, timeout=120):",
                "        self.timeout = timeout",
                "",
                "    def create_pixen(self, description, width, height, no_background, outline, detail, view, direction):",
                "        assert (width, height) == (512, 400)",
                "        return GenerationResult(Image.new('RGBA', (width, height), (10, 20, 30, 255)), {'ok': True})",
            ]
        ),
        encoding="utf-8",
    )
    generator = PixAIImageGenerator(work_dir / "out", script_path=script)
    response = generator.generate(
        ImageGenerationRequest(
            prompt="large coherent road source",
            style=ImageStyle.PIXEL_ART,
            size=(576, 448),
            transparency=TransparencyMode.OPAQUE,
            metadata={"target_id": "large_source", "category": "composite_source"},
        )
    )

    assert response.success
    assert response.metadata["api"] == "create_pixen"
    assert response.metadata["generation_size"] == [512, 400]
    assert response.metadata["requested_size"] == [576, 448]
    assert response.metadata["resized"] is True
    from PIL import Image

    with Image.open(response.image_path) as image:
        assert image.size == (576, 448)


def test_scene_background_concept_plan_review_and_extract():
    scene = TEST_WORK / f"background_plan_rice_{os.getpid()}_{uuid.uuid4().hex}"
    scene.mkdir(parents=True)
    for name in ["scene.md", "map_spec.json", "style_profile.json", "entities.json", "prompts.json"]:
        shutil.copyfile(RICE_FIELD_EXAMPLE / name, scene / name)
    build_scene_map(scene, force=True)

    concept = generate_scene_concept(scene, force=True)
    plan = build_background_plan(scene, force=True)
    html_path = write_background_review_html(scene, force=True)

    assert Path(concept["image"]).exists()
    assert (scene / "background_plan.json").exists()
    assert html_path.exists()
    assert plan["kind"] == "background_plan"
    assert any(item["kind"] == "base_terrain" for item in plan["review_items"])
    assert "Background Tile Review" in html_path.read_text(encoding="utf-8")

    plan["review_items"][0]["method"] = "extract_from_concept"
    plan["review_items"][0]["crop_rect"] = [0, 0, 128, 128]
    (scene / "background_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    written = extract_background_tiles(scene, force=True)

    assert written == [plan["review_items"][0]["asset_id"]]
    assert (scene / "background_tiles" / f"{written[0]}.png").exists()
