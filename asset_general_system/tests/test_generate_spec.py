from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from generate import (
    MapObjectAdditionSpec,
    apply_cli_overrides,
    build_default_asset_spec,
    build_map_art_request,
    configure_asset_spec,
    detect_asset_type,
    directions_for_count,
    export_refined_map,
    generate_map,
    infer_map_object_additions,
    parse_size,
    prepare_generated_map_output_dir,
    refine_map_with_objects,
    resolve_cli_description,
)
from generator.assets.image_generation import ImageStyle
from generator.export import TiledExporter, TiledJsonValidator
from generator.map import MapGenerator
from generator.models import GenerateRequest
from generator.parser import RulePromptParser
from generator.validation import Validator
from generator.vfx import VFXGenerationRequest, VFXGenerator


def test_walk_sheet_prompt_gets_rpg_character_defaults():
    spec = build_default_asset_spec("穿盔甲的兔子战士行走图")

    assert spec.asset_type == "character"
    assert spec.profile == "character_walk_sheet"
    assert spec.animations == ["walk"]
    assert spec.directions == ["down", "left", "right", "up"]
    assert spec.frame_size == (32, 48)
    assert spec.frames == 4
    assert spec.fps == 8


def test_prompt_can_request_8_direction_defaults():
    spec = build_default_asset_spec("八方向盔甲兔子战士行走图")

    assert spec.profile == "character_walk_sheet"
    assert len(spec.directions) == 8
    assert "down_left" in spec.directions
    assert "up_right" in spec.directions


def test_walk_sheet_type_wins_over_scene_words():
    assert detect_asset_type("村庄里的兔子战士行走图") == "character"


def test_configure_asset_spec_collects_each_character_rule():
    answers = iter([
        "",   # 素材类型：使用识别出的 character
        "",   # prompt：使用原描述
        "",   # style：pixel_art
        "",   # 角色素材规则：character_walk_sheet
        "",   # 动作规则：walk
        "2",  # 方向规则：8 方向
        "2",  # 单帧尺寸：48x64
        "3",  # 每动作帧数：6
        "4",  # fps：12
    ])

    spec = configure_asset_spec(
        "穿盔甲的兔子战士行走图",
        input_func=lambda _prompt: next(answers),
    )

    assert spec.asset_type == "character"
    assert spec.animations == ["walk"]
    assert spec.directions == directions_for_count(8)
    assert spec.frame_size == (48, 64)
    assert spec.frames == 6
    assert spec.fps == 12


def test_cli_overrides_update_spec_rules():
    spec = build_default_asset_spec("穿盔甲的兔子战士行走图", "character")
    args = SimpleNamespace(
        style="pixel_art",
        frame_size="64x96",
        frames=8,
        fps=10,
        directions="8",
        animations="idle,walk,attack",
        footprint=None,
        tile_size=None,
        map_size=None,
        loop=None,
        blend=None,
        category=None,
    )

    updated = apply_cli_overrides(spec, args)

    assert updated.frame_size == (64, 96)
    assert updated.frames == 8
    assert updated.fps == 10
    assert updated.directions == directions_for_count(8)
    assert updated.animations == ["idle", "walk", "attack"]


def test_cli_description_can_be_loaded_from_prompt_file(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("带“中文引号”的校园地图 prompt", encoding="utf-8")
    args = SimpleNamespace(description=None, prompt_file=prompt_file)

    assert resolve_cli_description(args) == "带“中文引号”的校园地图 prompt"


def test_cli_description_rejects_prompt_file_and_positional_prompt(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("校园地图", encoding="utf-8")
    args = SimpleNamespace(description="另一个 prompt", prompt_file=prompt_file)

    try:
        resolve_cli_description(args)
    except ValueError as exc:
        assert "不能同时传" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_parse_size_accepts_common_forms():
    assert parse_size("32x48") == (32, 48)
    assert parse_size("64") == (64, 64)
    assert parse_size("96, 128") == (96, 128)


def test_parse_csv_preserves_english_phrases():
    from generate import parse_csv

    assert parse_csv("gray tiled roof, brick chimney, visible entrance") == [
        "gray tiled roof",
        "brick chimney",
        "visible entrance",
    ]


def test_vfx_prompt_respects_non_pixel_style():
    generator = object.__new__(VFXGenerator)
    request = VFXGenerationRequest(
        vfx_type="spark",
        description="blue spark effect",
        style=ImageStyle.HAND_DRAWN,
    )

    prompt = generator._build_frame_prompt(request, 0)

    assert "hand-drawn 2D game effect" in prompt
    assert "pixel art" not in prompt


def test_map_refine_prompt_detects_common_school_objects():
    additions = infer_map_object_additions("增加2个乒乓球台和4个花盆")

    by_type = {item.object_type: item for item in additions}

    assert by_type["ping_pong_table"].count == 2
    assert by_type["ping_pong_table"].footprint == (2, 1)
    assert by_type["ping_pong_table"].placement == "playground"
    assert by_type["flower_pot"].count == 4
    assert by_type["flower_pot"].footprint == (1, 1)
    assert by_type["flower_pot"].placement == "school_entrance"


def test_map_refine_adds_objects_without_breaking_school_map(tmp_path):
    spec = RulePromptParser().parse(
        GenerateRequest(prompt="学校地图，有教学楼和操场", map_size=(64, 64), seed=123)
    )
    tilemap = MapGenerator().generate(spec)
    additions = [
        MapObjectAdditionSpec(
            name="乒乓球台",
            object_type="ping_pong_table",
            description="校园乒乓球台",
            count=2,
            footprint=(2, 1),
            blocking=True,
            placement="playground",
        ),
        MapObjectAdditionSpec(
            name="花盆",
            object_type="flower_pot",
            description="校园花盆",
            count=4,
            footprint=(1, 1),
            blocking=True,
            placement="school_entrance",
        ),
    ]

    refined, placed, _assets = refine_map_with_objects(
        tilemap,
        additions,
        tmp_path,
        use_gemini=False,
        seed=7,
    )

    assert len(placed) == 6
    assert sum(1 for obj in refined.objects if obj.type == "ping_pong_table") == 2
    assert sum(1 for obj in refined.objects if obj.type == "flower_pot") == 4
    assert all(obj.properties["blocking"] for obj in placed)
    assert all(refined.layers["collision"][obj.y * refined.map.width + obj.x] == 1 for obj in placed)
    assert Validator().validate(refined).passed
    assert TiledJsonValidator().validate(TiledExporter().to_dict(refined)).passed


def test_prepare_generated_map_output_dir_removes_stale_generated_files(tmp_path):
    output_dir = tmp_path / "map_run"
    stale_object = output_dir / "objects" / "stale.png"
    stale_temp = output_dir / "_temp" / "old.png"
    stale_godot = output_dir / "godot" / "scene.tscn"
    unrelated = output_dir / "notes.txt"
    stale_object.parent.mkdir(parents=True)
    stale_temp.parent.mkdir(parents=True)
    stale_godot.parent.mkdir(parents=True)
    stale_object.write_text("old", encoding="utf-8")
    stale_temp.write_text("old", encoding="utf-8")
    stale_godot.write_text("old", encoding="utf-8")
    (output_dir / "preview.png").write_text("old", encoding="utf-8")
    unrelated.write_text("keep", encoding="utf-8")

    prepare_generated_map_output_dir(output_dir)

    assert not stale_object.exists()
    assert not stale_temp.exists()
    assert not stale_godot.exists()
    assert not (output_dir / "preview.png").exists()
    assert unrelated.read_text(encoding="utf-8") == "keep"


def test_export_refined_map_writes_expected_package(tmp_path):
    spec = RulePromptParser().parse(
        GenerateRequest(prompt="学校地图，有教学楼和操场", map_size=(64, 64), seed=123)
    )
    tilemap = MapGenerator().generate(spec)
    additions = [
        MapObjectAdditionSpec(
            name="花盆",
            object_type="flower_pot",
            description="校园花盆",
            count=1,
            footprint=(1, 1),
            blocking=True,
            placement="school_entrance",
        ),
    ]
    refined, placed, _assets = refine_map_with_objects(tilemap, additions, tmp_path, use_gemini=False, seed=9)

    export_refined_map(refined, tmp_path / "refined", {"placed_count": len(placed)})

    assert (tmp_path / "refined" / "map_data.json").exists()
    assert (tmp_path / "refined" / "preview.png").exists()
    assert (tmp_path / "refined" / "map.tiled.json").exists()
    assert (tmp_path / "refined" / "map_refine_report.json").exists()


def test_build_map_art_request_exports_logic_contract_for_external_art_skill():
    request = GenerateRequest(
        prompt="学校地图，有教学楼、操场、学生宿舍、小卖部、食堂、乒乓球台和篮球架",
        map_size=(64, 64),
        seed=20260609,
    )
    tilemap = MapGenerator().generate(RulePromptParser().parse(request))

    art_request = build_map_art_request(tilemap, request.prompt)

    assert art_request["kind"] == "logical_map_art_request"
    assert art_request["map_size"] == [64, 64]
    assert art_request["tile_size"] == [32, 32]
    assert art_request["canvas_size"] == [2048, 2048]
    assert {"terrain", "path", "building", "decoration", "collision"} <= set(art_request["layers"])
    dormitory = next(item for item in art_request["objects"] if item["type"] == "dormitory")
    assert dormitory["footprint"] == [10, 6]
    assert dormitory["runtime_size"] == [320, 192]
    assert dormitory["anchor"] == "bottom_center"
    assert dormitory["facing"] == "faces_south"
    assert dormitory["pixel_bounds"][2:] == [320, 192]


def test_generate_map_outputs_logic_package_without_ai_art_side_effects(tmp_path):
    tilemap = generate_map(
        "学校地图，有教学楼、操场、学生宿舍、小卖部、食堂、乒乓球台和篮球架",
        tmp_path,
        use_gemini=True,
        seed=20260609,
        spec=build_default_asset_spec(
            "学校地图，有教学楼、操场、学生宿舍、小卖部、食堂、乒乓球台和篮球架",
            "map",
        ),
    )

    assert (tmp_path / "map_data.json").exists()
    assert (tmp_path / "map.tiled.json").exists()
    assert (tmp_path / "preview.png").exists()
    assert (tmp_path / "preview_debug.png").exists()
    assert (tmp_path / "art_request.json").exists()
    assert not (tmp_path / "map_object_sprite_report.json").exists()
    assert not (tmp_path / "ground_detail_tileset_report.json").exists()
    assert not (tmp_path / "map_asset_generation_specs.json").exists()
    assert not (tmp_path / "objects").exists()
    assert not (tmp_path / "_temp").exists()
    assert all(obj.sprite_path is None and obj.sprite_ref is None for obj in tilemap.objects)
