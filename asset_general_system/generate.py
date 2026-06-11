#!/usr/bin/env python
"""
真实使用场景：用户输入描述，自动生成对应素材

使用方式：
    python generate.py "一只穿着盔甲的兔子战士"
    python generate.py "魔法森林中的发光蘑菇" --type object
    python generate.py "火球术特效" --type vfx
    python generate.py "一片雪地村庄，中间有篝火" --type map
"""

import argparse
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent))


SCENE_COMMANDS = {
    "scene-background-assets",
    "scene-background-plan",
    "scene-background-review",
    "scene-concept",
    "scene-map-build",
    "scene-images",
    "scene-pack",
    "scene-status",
    "scene-tilemap-blueprint",
    "scene-tilemap-candidates",
    "scene-tilemap-export-tiled",
    "scene-tilemap-family-plan",
    "scene-tilemap-mapping",
    "scene-tileset-generate",
    "scene-validate",
}


ASSET_TYPES = ("object", "character", "vfx", "map")
STYLE_VALUES = ("pixel_art", "hand_drawn", "low_poly", "realistic")
FOUR_DIRECTIONS = ["down", "left", "right", "up"]
EIGHT_DIRECTIONS = [
    "down",
    "down_left",
    "left",
    "up_left",
    "up",
    "up_right",
    "right",
    "down_right",
]


@dataclass
class AssetSpec:
    """用户确认后的素材生成规格。"""

    asset_type: str
    prompt: str
    profile: str
    style: str = "pixel_art"
    frame_size: tuple[int, int] | None = None
    frames: int | None = None
    fps: int | None = None
    directions: list[str] = field(default_factory=list)
    animations: list[str] = field(default_factory=list)
    footprint: tuple[int, int] | None = None
    tile_size: tuple[int, int] | None = None
    loop: bool | None = None
    blend: str | None = None
    category: str | None = None
    map_size: tuple[int, int] | None = None


@dataclass
class MapObjectAdditionSpec:
    """一次地图补充中的单类逻辑物件配置。"""

    name: str
    object_type: str
    description: str
    count: int
    footprint: tuple[int, int] = (1, 1)
    blocking: bool = True
    placement: str = "auto"
    target_region: str | None = None
    manual_positions: list[tuple[int, int]] = field(default_factory=list)


MAP_OBJECT_PRESETS = {
    "ping_pong_table": {
        "name": "乒乓球台",
        "keywords": ("乒乓球台", "乒乓桌", "ping pong table", "table tennis table"),
        "description": "学校操场里的水泥乒乓球台",
        "count": 2,
        "footprint": (2, 1),
        "blocking": True,
        "placement": "playground",
    },
    "flower_pot": {
        "name": "花盆",
        "keywords": ("花盆", "盆栽", "potted plant", "flower pot"),
        "description": "学校建筑旁的花盆盆栽",
        "count": 6,
        "footprint": (1, 1),
        "blocking": True,
        "placement": "school_entrance",
    },
    "bench": {
        "name": "长椅",
        "keywords": ("长椅", "椅子", "bench"),
        "description": "校园木质长椅",
        "count": 3,
        "footprint": (2, 1),
        "blocking": True,
        "placement": "random_walkable",
    },
    "basketball_hoop": {
        "name": "篮球架",
        "keywords": ("篮球架", "basketball hoop"),
        "description": "学校操场篮球架",
        "count": 2,
        "footprint": (1, 2),
        "blocking": True,
        "placement": "playground",
    },
}


def parse_size(value: str) -> tuple[int, int]:
    """解析 32x48 / 32,48 / 32 48 / 64 形式的尺寸。"""
    import re

    text = value.strip().lower()
    if not text:
        raise ValueError("尺寸不能为空")

    numbers = [int(item) for item in re.findall(r"\d+", text)]
    if len(numbers) == 1:
        width = height = numbers[0]
    elif len(numbers) >= 2:
        width, height = numbers[0], numbers[1]
    else:
        raise ValueError(f"无法解析尺寸: {value}")

    if width <= 0 or height <= 0:
        raise ValueError("尺寸必须大于 0")
    return width, height


def parse_csv(value: str) -> list[str]:
    """解析列表输入，保留英文短语内部空格。"""
    import re

    return [part.strip() for part in re.split(r"[,，、;；\n]+", value.strip()) if part.strip()]


def parse_bool(value: str) -> bool:
    text = value.strip().lower()
    if text in ("1", "y", "yes", "true", "t", "是", "对", "循环"):
        return True
    if text in ("0", "n", "no", "false", "f", "否", "不", "不循环"):
        return False
    raise ValueError(f"无法解析布尔值: {value}")


def directions_for_count(count: int) -> list[str]:
    if count == 4:
        return list(FOUR_DIRECTIONS)
    if count == 8:
        return list(EIGHT_DIRECTIONS)
    raise ValueError("方向数量只支持 4 或 8")


def direction_count_from_prompt(description: str) -> int:
    lower = description.lower()
    if any(token in lower for token in ("8方向", "8 方向", "八方向", "八向", "8-way", "8 way", "eight direction")):
        return 8
    return 4


def detect_asset_profile(description: str, asset_type: str) -> str:
    """识别更细的素材规则，用于决定后续要问哪些配置。"""
    lower = description.lower()
    if asset_type == "character":
        if any(token in lower for token in ("行走图", "走路", "行走", "walk sheet", "walking", "walkcycle", "walk cycle")):
            return "character_walk_sheet"
        return "character_basic_sheet"
    if asset_type == "vfx":
        return "vfx_sprite_sheet"
    if asset_type == "map":
        return "tilemap"
    return "object_sprite"


def infer_vfx_category_and_blend(description: str) -> tuple[str, str]:
    lower = description.lower()
    if any(k in lower for k in ["火", "雷", "冰", "斩", "fire", "thunder", "ice", "slash", "lightning"]):
        return "combat", "additive"
    if any(k in lower for k in ["治疗", "魔法", "传送", "heal", "magic", "teleport"]):
        return "magic", "additive"
    if any(k in lower for k in ["雨", "雪", "落叶", "rain", "snow", "leaves"]):
        return "environment", "normal"
    return "combat", "normal"


def build_default_asset_spec(description: str, asset_type: str | None = None) -> AssetSpec:
    """根据用户描述生成一份可逐项修改的默认规格。"""
    resolved_type = asset_type if asset_type and asset_type != "auto" else detect_asset_type(description)
    profile = detect_asset_profile(description, resolved_type)

    if resolved_type == "character":
        actions = ["walk"] if profile == "character_walk_sheet" else ["idle", "walk"]
        return AssetSpec(
            asset_type="character",
            prompt=description,
            profile=profile,
            frame_size=(32, 48),
            frames=4,
            fps=8,
            directions=directions_for_count(direction_count_from_prompt(description)),
            animations=actions,
        )

    if resolved_type == "vfx":
        category, blend = infer_vfx_category_and_blend(description)
        return AssetSpec(
            asset_type="vfx",
            prompt=description,
            profile=profile,
            frame_size=(64, 64),
            frames=8,
            fps=12,
            loop=False,
            blend=blend,
            category=category,
        )

    if resolved_type == "map":
        return AssetSpec(
            asset_type="map",
            prompt=description,
            profile=profile,
            map_size=(64, 64),
            tile_size=(32, 32),
        )

    return AssetSpec(
        asset_type="object",
        prompt=description,
        profile=profile,
        footprint=(1, 1),
        tile_size=(32, 32),
        frame_size=(32, 32),
    )


def image_style_from_value(value: str):
    from generator.assets.image_generation import ImageStyle

    return ImageStyle(value)


def format_size(size: tuple[int, int] | None) -> str:
    if not size:
        return "-"
    return f"{size[0]}x{size[1]}"


def print_spec_summary(spec: AssetSpec) -> None:
    print("\n生成规格：")
    print(f"  prompt: {spec.prompt}")
    print(f"  类型: {spec.asset_type}")
    print(f"  规则: {spec.profile}")
    if spec.asset_type != "map":
        print(f"  风格: {spec.style}")
    if spec.asset_type == "character":
        print(f"  动作: {', '.join(spec.animations)}")
        print(f"  方向: {len(spec.directions)} ({', '.join(spec.directions)})")
        print(f"  单帧尺寸: {format_size(spec.frame_size)}")
        print(f"  每动作帧数: {spec.frames}")
        print(f"  fps: {spec.fps}")
        print(f"  预计单帧生成次数: {len(spec.animations) * len(spec.directions) * (spec.frames or 0)}")
    elif spec.asset_type == "vfx":
        print(f"  单帧尺寸: {format_size(spec.frame_size)}")
        print(f"  帧数: {spec.frames}")
        print(f"  fps: {spec.fps}")
        print(f"  循环: {spec.loop}")
        print(f"  类别: {spec.category}")
        print(f"  blend: {spec.blend}")
    elif spec.asset_type == "object":
        print(f"  footprint: {format_size(spec.footprint)} tiles")
        print(f"  tile size: {format_size(spec.tile_size)}")
    elif spec.asset_type == "map":
        print(f"  地图尺寸: {format_size(spec.map_size)} tiles")
        print(f"  tile size: {format_size(spec.tile_size)}")


def prompt_text(
    title: str,
    default: str,
    input_func: Callable[[str], str] = input,
) -> str:
    value = input_func(f"{title} [{default}]: ").strip()
    return value or default


def prompt_required_text(
    title: str,
    input_func: Callable[[str], str] = input,
) -> str:
    while True:
        value = input_func(f"{title}: ").strip()
        if value:
            return value
        print("该项不能为空。")


def prompt_choice(
    title: str,
    options: list[tuple[str, str]],
    default: str,
    input_func: Callable[[str], str] = input,
) -> str:
    option_values = {value for value, _ in options}
    default_index = next((idx for idx, (value, _) in enumerate(options, 1) if value == default), 1)

    while True:
        print(f"\n{title}:")
        for idx, (value, label) in enumerate(options, 1):
            marker = " *" if value == default else ""
            print(f"  {idx}. {label} ({value}){marker}")
        raw = input_func(f"请选择 [默认 {default_index}]: ").strip()
        if not raw:
            return default
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1][0]
        if raw in option_values:
            return raw
        print("输入无效，请输入编号或括号中的值。")


def prompt_choice_or_custom(
    title: str,
    options: list[tuple[str, str]],
    default: str,
    input_func: Callable[[str], str] = input,
    custom_prompt: str | None = None,
    custom_label: str = "手动输入其他值",
    allow_direct_custom: bool = False,
) -> str:
    """Prompt with known production-safe options while keeping a manual escape hatch."""
    expanded_options = list(options)
    option_values = {value for value, _ in expanded_options}
    if default and default not in option_values:
        expanded_options.insert(0, (default, f"当前值：{default}"))

    custom_value = "custom"
    if custom_value in {value for value, _ in expanded_options}:
        custom_value = "__custom__"
    expanded_options.append((custom_value, custom_label))

    default_value = default or expanded_options[0][0]
    default_index = next((idx for idx, (value, _) in enumerate(expanded_options, 1) if value == default_value), 1)
    option_values = {value for value, _ in expanded_options}

    while True:
        print(f"\n{title}:")
        for idx, (value, label) in enumerate(expanded_options, 1):
            marker = " *" if value == default_value else ""
            print(f"  {idx}. {label} ({value}){marker}")
        raw = input_func(f"请选择 [默认 {default_index}]: ").strip()
        if not raw:
            return default_value
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(expanded_options):
                selected = expanded_options[index - 1][0]
                if selected == custom_value:
                    return prompt_text(custom_prompt or title, default, input_func)
                return selected
        if raw in option_values:
            if raw == custom_value:
                return prompt_text(custom_prompt or title, default, input_func)
            return raw
        if raw.lower() in {"custom", "自定义", "手动"}:
            return prompt_text(custom_prompt or title, default, input_func)
        if allow_direct_custom:
            return raw
        print("输入无效，请输入编号、括号中的值，或选择手动输入。")



def prompt_int_choice(
    title: str,
    options: list[tuple[int, str]],
    default: int,
    input_func: Callable[[str], str] = input,
) -> int:
    string_options = [(str(value), label) for value, label in options]
    return int(prompt_choice(title, string_options, str(default), input_func))


def prompt_size_choice(
    title: str,
    options: list[tuple[tuple[int, int], str]],
    default: tuple[int, int],
    input_func: Callable[[str], str] = input,
) -> tuple[int, int]:
    string_options = [(format_size(value), label) for value, label in options]
    default_text = format_size(default)

    while True:
        print(f"\n{title}:")
        for idx, (value, label) in enumerate(string_options, 1):
            marker = " *" if value == default_text else ""
            print(f"  {idx}. {label} ({value}){marker}")
        print("  custom. 手动输入，例如 32x48")
        raw = input_func(f"请选择 [默认 {default_text}]: ").strip()
        if not raw:
            return default
        if raw.isdigit():
            index = int(raw)
            if 1 <= index <= len(options):
                return options[index - 1][0]
        if raw.lower() == "custom":
            raw = input_func("请输入尺寸: ").strip()
        try:
            return parse_size(raw)
        except ValueError as exc:
            print(f"{exc}，请重新输入。")


def prompt_bool_choice(
    title: str,
    default: bool,
    input_func: Callable[[str], str] = input,
) -> bool:
    default_text = "是" if default else "否"
    while True:
        raw = input_func(f"{title} [默认 {default_text}]: ").strip()
        if not raw:
            return default
        try:
            return parse_bool(raw)
        except ValueError as exc:
            print(f"{exc}，请重新输入。")


def prompt_positive_int(
    title: str,
    default: int,
    input_func: Callable[[str], str] = input,
) -> int:
    while True:
        raw = input_func(f"{title} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("请输入正整数。")
            continue
        if value > 0:
            return value
        print("请输入大于 0 的数量。")


def parse_positions(value: str) -> list[tuple[int, int]]:
    """解析 10,12;14,12 或 10 12;14 12 形式的地图格坐标。"""
    import re

    positions: list[tuple[int, int]] = []
    for part in re.split(r"[;；|]", value.strip()):
        if not part.strip():
            continue
        numbers = [int(item) for item in re.findall(r"\d+", part)]
        if len(numbers) < 2:
            raise ValueError(f"坐标不完整: {part}")
        positions.append((numbers[0], numbers[1]))
    if not positions:
        raise ValueError("至少需要一个坐标")
    return positions


def prompt_positions(
    title: str,
    default: list[tuple[int, int]],
    input_func: Callable[[str], str] = input,
) -> list[tuple[int, int]]:
    default_text = ";".join(f"{x},{y}" for x, y in default) if default else ""
    while True:
        raw = input_func(f"{title} [{default_text}]: ").strip()
        if not raw and default:
            return default
        try:
            return parse_positions(raw)
        except ValueError as exc:
            print(f"{exc}，请重新输入。")


def prompt_animations(
    default: list[str],
    input_func: Callable[[str], str] = input,
) -> list[str]:
    options = [
        ("walk", "行走图，只生成 walk"),
        ("idle,walk", "基础角色，idle + walk"),
        ("idle,walk,run", "移动角色，idle + walk + run"),
        ("idle,walk,attack,cast", "战斗角色，idle + walk + attack + cast"),
    ]
    chosen = prompt_choice("动作规则", options, ",".join(default), input_func)
    return parse_csv(chosen)


def prompt_directions(
    default: list[str],
    input_func: Callable[[str], str] = input,
) -> list[str]:
    default_count = 8 if len(default) == 8 else 4
    chosen = prompt_choice(
        "方向规则",
        [
            ("4", "4 方向：down / left / right / up"),
            ("8", "8 方向：含四个斜向"),
            ("custom", "手动输入方向列表"),
        ],
        str(default_count),
        input_func,
    )
    if chosen in ("4", "8"):
        return directions_for_count(int(chosen))

    while True:
        raw = input_func("请输入方向列表，例如 down,left,right,up: ").strip()
        values = parse_csv(raw)
        invalid = [value for value in values if value not in EIGHT_DIRECTIONS]
        if values and not invalid:
            return values
        print(f"方向无效: {invalid}，可用值: {', '.join(EIGHT_DIRECTIONS)}")


def configure_asset_spec(
    description: str,
    asset_type: str | None = None,
    input_func: Callable[[str], str] = input,
) -> AssetSpec:
    """逐项询问用户生成规则，返回最终规格。"""
    inferred_type = asset_type if asset_type and asset_type != "auto" else detect_asset_type(description)
    print(f"\n系统识别类型: {inferred_type}")

    selected_type = prompt_choice(
        "素材类型",
        [
            ("character", "角色 / 行走图 / NPC / 怪物"),
            ("object", "地图物件 / 道具 / 装饰物"),
            ("vfx", "技能 / 粒子 / 特效动画"),
            ("map", "RPG 地图 / 场景 / 关卡"),
        ],
        inferred_type,
        input_func,
    )

    spec = build_default_asset_spec(description, selected_type)
    spec.prompt = prompt_text("生成 prompt", spec.prompt, input_func)
    if spec.asset_type != "map":
        spec.style = prompt_choice(
            "视觉风格",
            [
                ("pixel_art", "像素风 RPG 默认"),
                ("hand_drawn", "手绘 2D"),
                ("low_poly", "低多边形"),
                ("realistic", "写实"),
            ],
            spec.style,
            input_func,
        )

    if spec.asset_type == "character":
        spec.profile = prompt_choice(
            "角色素材规则",
            [
                ("character_walk_sheet", "行走图 sprite sheet"),
                ("character_basic_sheet", "基础角色 sprite sheet"),
            ],
            spec.profile,
            input_func,
        )
        if spec.profile == "character_walk_sheet" and spec.animations != ["walk"]:
            spec.animations = ["walk"]
        spec.animations = prompt_animations(spec.animations, input_func)
        spec.directions = prompt_directions(spec.directions, input_func)
        spec.frame_size = prompt_size_choice(
            "角色单帧尺寸",
            [
                ((32, 48), "常规 RPG 角色"),
                ((48, 64), "更高细节角色"),
                ((64, 64), "方形高分辨率角色"),
                ((64, 96), "高角色 / Boss"),
            ],
            spec.frame_size or (32, 48),
            input_func,
        )
        spec.frames = prompt_int_choice(
            "每个动作的帧数",
            [
                (3, "最省成本，动画较硬"),
                (4, "常规 RPG 默认"),
                (6, "更顺滑"),
                (8, "高流畅度，生成成本高"),
            ],
            spec.frames or 4,
            input_func,
        )
        spec.fps = prompt_int_choice(
            "动画播放 fps",
            [
                (6, "偏慢"),
                (8, "行走图常规"),
                (10, "略快"),
                (12, "流畅动作"),
            ],
            spec.fps or 8,
            input_func,
        )

    elif spec.asset_type == "vfx":
        spec.frame_size = prompt_size_choice(
            "特效单帧尺寸",
            [
                ((32, 32), "小型命中特效"),
                ((64, 64), "常规技能特效"),
                ((96, 96), "爆炸 / 大型技能"),
                ((128, 128), "天气 / 大范围环境特效"),
            ],
            spec.frame_size or (64, 64),
            input_func,
        )
        spec.frames = prompt_int_choice(
            "特效帧数",
            [(4, "短促"), (6, "中等"), (8, "常规"), (10, "更细腻"), (12, "高流畅度")],
            spec.frames or 8,
            input_func,
        )
        spec.fps = prompt_int_choice(
            "特效 fps",
            [(8, "慢速"), (10, "中速"), (12, "常规"), (15, "快速"), (20, "打击感强")],
            spec.fps or 12,
            input_func,
        )
        spec.loop = prompt_bool_choice("是否循环播放", bool(spec.loop), input_func)
        spec.category = prompt_choice(
            "特效类别",
            [
                ("combat", "战斗"),
                ("magic", "魔法"),
                ("environment", "环境"),
                ("ambient", "氛围"),
                ("interaction", "交互反馈"),
            ],
            spec.category or "combat",
            input_func,
        )
        spec.blend = prompt_choice(
            "混合模式",
            [
                ("normal", "普通"),
                ("additive", "发光叠加"),
                ("screen", "滤色"),
                ("multiply", "正片叠底"),
            ],
            spec.blend or "normal",
            input_func,
        )

    elif spec.asset_type == "object":
        spec.tile_size = prompt_size_choice(
            "地图 tile 尺寸",
            [((16, 16), "低分辨率"), ((32, 32), "常规 RPG"), ((48, 48), "高清"), ((64, 64), "高分辨率")],
            spec.tile_size or (32, 32),
            input_func,
        )
        spec.footprint = prompt_size_choice(
            "物件占用格数 footprint",
            [
                ((1, 1), "小物件 / 道具"),
                ((1, 2), "树 / 路灯 / 竖向物件"),
                ((2, 1), "长条物件 / 长椅"),
                ((2, 2), "建筑小件 / 喷泉"),
                ((3, 2), "较大建筑"),
            ],
            spec.footprint or (1, 1),
            input_func,
        )
        spec.frame_size = (
            (spec.tile_size or (32, 32))[0] * (spec.footprint or (1, 1))[0],
            (spec.tile_size or (32, 32))[1] * (spec.footprint or (1, 1))[1],
        )

    elif spec.asset_type == "map":
        spec.map_size = prompt_size_choice(
            "地图尺寸（格数）",
            [((32, 32), "小地图"), ((64, 64), "常规地图"), ((96, 96), "大地图"), ((128, 128), "大型场景")],
            spec.map_size or (64, 64),
            input_func,
        )
        spec.tile_size = prompt_size_choice(
            "地图 tile 尺寸",
            [((16, 16), "低分辨率"), ((32, 32), "常规 RPG"), ((48, 48), "高清"), ((64, 64), "高分辨率")],
            spec.tile_size or (32, 32),
            input_func,
        )

    print_spec_summary(spec)
    return spec


def apply_cli_overrides(spec: AssetSpec, args: argparse.Namespace) -> AssetSpec:
    """把命令行参数覆盖到默认规格上。"""
    if args.style:
        spec.style = args.style
    if args.frame_size:
        spec.frame_size = parse_size(args.frame_size)
    if args.frames:
        spec.frames = args.frames
    if args.fps:
        spec.fps = args.fps
    if args.directions:
        if args.directions in ("4", "8"):
            spec.directions = directions_for_count(int(args.directions))
        else:
            spec.directions = parse_csv(args.directions)
    if args.animations:
        spec.animations = parse_csv(args.animations)
    if args.footprint:
        spec.footprint = parse_size(args.footprint)
    if args.tile_size:
        spec.tile_size = parse_size(args.tile_size)
    if args.map_size:
        spec.map_size = parse_size(args.map_size)
    if args.loop is not None:
        spec.loop = args.loop
    if args.blend:
        spec.blend = args.blend
    if args.category:
        spec.category = args.category
    return spec


def slugify(text: str, max_words: int = 3) -> str:
    """把描述转换为文件名友好的 slug。

    优先提取英文词，其次拼音，最后用 hash。
    """
    import re

    # 1. 提取英文单词
    english_words = re.findall(r'[a-zA-Z]+', text)
    if english_words:
        slug = "_".join(w.lower() for w in english_words[:max_words])
        return slug if slug else "asset"

    # 2. 中文：使用关键词映射
    # 优先级：主体名词 > 修饰词 > 类别
    primary_keywords = {
        # 角色（主体）
        "战士": "warrior", "骑士": "knight", "法师": "mage", "弓箭手": "archer",
        "村民": "villager", "商人": "merchant", "国王": "king", "公主": "princess",
        "怪物": "monster", "敌人": "enemy", "勇者": "hero", "盗贼": "rogue",
        "兔子": "rabbit", "猫": "cat", "狗": "dog", "龙": "dragon", "精灵": "elf",
        "矮人": "dwarf", "兽人": "orc", "骷髅": "skeleton", "僵尸": "zombie",
        "史莱姆": "slime", "幽灵": "ghost",
        # 装备/对象（主体）
        "盔甲": "armor", "宝箱": "chest", "水晶": "crystal", "蘑菇": "mushroom",
        "树": "tree", "石头": "rock", "花": "flower", "草": "grass",
        "房子": "house", "城堡": "castle", "神庙": "temple", "塔": "tower",
        "桥": "bridge", "门": "door", "墙": "wall", "井": "well",
        "灯": "lamp", "雕像": "statue", "喷泉": "fountain", "篝火": "campfire",
        "桶": "barrel", "箱子": "crate", "标志": "sign", "椅子": "bench",
        # 特效（主体）
        "火球": "fireball", "斩击": "slash", "爆炸": "explosion", "治疗": "heal",
        "传送": "teleport", "闪电": "lightning", "冰": "ice", "雷": "thunder",
        # 地图（主体）
        "村庄": "village", "城市": "city", "森林": "forest", "沙漠": "desert",
        "雪地": "snow", "海边": "seaside", "山": "mountain", "地牢": "dungeon",
        "营地": "camp", "遗迹": "ruins",
    }

    modifier_keywords = {
        # 颜色
        "金色": "gold", "银色": "silver", "蓝色": "blue", "红色": "red",
        "绿色": "green", "紫色": "purple", "白色": "white", "黑色": "black",
        # 风格
        "魔法的": "magic", "古老的": "ancient", "发光的": "glowing", "神秘的": "mystic",
        "邪恶的": "evil", "可爱的": "cute", "巨大的": "giant", "小": "small",
        "魔法": "magic", "发光": "glowing", "古老": "ancient", "神秘": "mystic",
        # 主题
        "圣诞": "christmas", "万圣": "halloween",
    }

    # 先找主体词（最多 2 个，物种 + 角色）
    primaries = []
    for cn, en in primary_keywords.items():
        if cn in text and en not in primaries:
            primaries.append(en)
            if len(primaries) >= 2:
                break

    # 再找修饰词（最多 1 个，避免太长）
    modifiers = []
    for cn, en in modifier_keywords.items():
        if cn in text and en not in modifiers:
            modifiers.append(en)
            if len(modifiers) >= max_words - len(primaries):
                break

    # 组合：modifier + primary（更易理解）
    parts = modifiers + primaries

    if parts:
        return "_".join(parts[:max_words])

    # 3. 兜底：用 hash
    return f"asset_{abs(hash(text)) % 100000:05d}"


def extract_tags(description: str, max_tags: int = 5) -> list[str]:
    """从描述中提取语义标签。"""
    import re

    # 提取英文词
    english_words = [w.lower() for w in re.findall(r'[a-zA-Z]+', description)]

    # 从中文映射提取
    keyword_map = {
        "战士": "warrior", "骑士": "knight", "法师": "mage", "弓箭手": "archer",
        "兔子": "rabbit", "猫": "cat", "龙": "dragon", "精灵": "elf",
        "矮人": "dwarf", "兽人": "orc", "骷髅": "skeleton", "僵尸": "zombie",
        "史莱姆": "slime", "幽灵": "ghost", "村民": "villager", "商人": "merchant",
        "国王": "king", "公主": "princess", "勇者": "hero",
        "盔甲": "armor", "宝箱": "chest", "水晶": "crystal", "蘑菇": "mushroom",
        "树": "tree", "石头": "rock", "魔法": "magic", "发光": "glowing",
        "火球": "fireball", "爆炸": "explosion", "治疗": "heal", "闪电": "lightning",
        "村庄": "village", "森林": "forest", "雪地": "snow", "沙漠": "desert",
        "古老": "ancient", "神秘": "mystic", "金色": "gold", "蓝色": "blue",
        "红色": "red", "绿色": "green", "白色": "white", "黑色": "black",
        "紫色": "purple", "黄色": "yellow",
        "帽子": "hat", "帽": "hat", "斗篷": "cloak", "披风": "cape",
        "圣诞": "christmas", "万圣": "halloween", "新年": "newyear",
        "戴": "wearing", "穿": "wearing",
    }

    chinese_tags = [en for cn, en in keyword_map.items() if cn in description]

    # 合并去重
    all_tags = []
    for tag in english_words + chinese_tags:
        if tag and tag not in all_tags:
            all_tags.append(tag)

    return all_tags[:max_tags]


def detect_asset_type(description: str) -> str:
    """从描述中自动判断素材类型。

    判断优先级（从高到低）：
    1. 地图 - 整体场景描述
    2. 角色 - 有生命体征的实体
    3. VFX - 动态视觉效果
    4. 对象 - 静态物品（默认）
    """
    desc_lower = description.lower()

    explicit_character_keywords = [
        "行走图", "走路图", "walk sheet", "walking sprite", "walk cycle", "character sprite sheet",
    ]
    if any(kw in desc_lower for kw in explicit_character_keywords):
        return "character"

    # 地图关键词（最高优先级 - 整体场景）
    map_keywords = [
        "地图", "村庄", "城市", "场景", "关卡", "地牢", "营地", "遗迹",
        "广场", "村落", "小镇", "城堡内", "整片", "整个",
        "map", "village", "city", "scene", "level", "dungeon", "camp",
        "ruins", "town", "plaza",
    ]

    # 角色关键词（实体生物）
    character_keywords = [
        "行走图", "走路图", "行走", "主角", "战士", "兔子", "人物", "角色", "村民", "商人", "怪物", "敌人",
        "国王", "公主", "骑士", "法师", "弓箭手", "盗贼", "牧师", "npc", "nps",
        "精灵", "矮人", "兽人", "骷髅", "僵尸", "史莱姆", "幽灵", "龙",
        "猫", "狗", "牛", "马", "羊", "鸡", "鸭",
        "walk sheet", "walking sprite", "walk cycle", "warrior", "character", "person", "knight", "wizard", "merchant",
        "monster", "enemy", "hero", "villager", "king", "princess", "rogue",
        "priest", "npc", "mage", "archer", "guard", "elf", "dwarf", "orc",
        "skeleton", "zombie", "slime", "ghost", "dragon",
    ]

    # VFX 关键词（动作/特效，必须明确是"特效"或动作）
    # 注意：必须包含"特效"或动作动词，避免误判（"魔法蘑菇" -> 不是 vfx）
    vfx_action_keywords = [
        "特效", "技能", "动画", "粒子",
        "vfx", "effect", "animation", "particle",
    ]
    vfx_effect_types = [
        "火球术", "斩击", "爆炸效果", "治疗光环", "传送阵效果", "闪电链",
        "fireball", "slash", "explosion", "heal", "teleport", "sparkle",
    ]
    weather_keywords = ["下雨", "下雪", "落叶飘", "rain falling", "snowing"]

    if any(kw in desc_lower for kw in vfx_action_keywords):
        return "vfx"
    if any(kw in desc_lower for kw in vfx_effect_types):
        return "vfx"
    if any(kw in desc_lower for kw in weather_keywords) and not any(kw in desc_lower for kw in map_keywords):
        return "vfx"

    # 1. 检查地图（最优先）
    if any(kw in desc_lower for kw in map_keywords):
        # 但要排除"村民"这种角色词
        if not any(kw in desc_lower for kw in ["村民", "商人", "村长"]):
            return "map"

    # 2. 检查角色
    if any(kw in desc_lower for kw in character_keywords):
        return "character"

    # 3. 检查 VFX（需要明确的特效词）
    if any(kw in desc_lower for kw in weather_keywords):
        return "vfx"

    # 4. 默认作为对象（树、石头、蘑菇、宝箱等静态物品）
    return "object"


def directions_to_model(values: list[str]):
    from generator.models.sprite_sheet import Direction

    return [Direction(value) for value in values]


def generate_object(
    description: str,
    output_dir: Path,
    use_gemini: bool,
    seed: int = None,
    spec: AssetSpec | None = None,
):
    """生成单个对象素材。"""
    from generator.assets.object_generator import (
        ObjectGenerator,
        ObjectGenerationRequest,
    )

    spec = spec or build_default_asset_spec(description, "object")
    image_gen = create_image_generator(output_dir / "_temp", use_gemini)
    obj_gen = ObjectGenerator(image_gen, output_dir / "objects")

    # 使用 slug 作为对象类型（英文友好）
    object_type = slugify(spec.prompt, max_words=2)
    tags = extract_tags(spec.prompt)

    request = ObjectGenerationRequest(
        object_type=object_type,
        description=spec.prompt,
        style=image_style_from_value(spec.style),
        footprint=spec.footprint or (1, 1),
        tile_size=spec.tile_size or (32, 32),
        tags=tags,
        seed=seed or hash(spec.prompt) % 10000,
    )

    print(f"正在生成对象: {spec.prompt}")
    print(f"  asset slug: {object_type}")
    print(f"  footprint: {request.footprint}, tile size: {request.tile_size}")
    print(f"  提取标签: {tags}")
    if use_gemini:
        print("  使用 Gemini AI（约 5-10 秒）...")
    else:
        print("  使用 Mock 模式（即时）...")

    result = obj_gen.generate(request)

    if result.success:
        print(f"\n[成功] 对象生成完成")
        print(f"  asset_id: {result.asset_id}")
        print(f"  图像: {result.sprite_path}")
        print(f"  metadata: {result.metadata_path}")
        print(f"  尺寸: {result.metadata.tile_size}")
        print(f"  占格: {result.metadata.footprint}")
        return result
    else:
        print(f"\n[失败] {result.error}")
        return None


def generate_character(
    description: str,
    output_dir: Path,
    use_gemini: bool,
    seed: int = None,
    spec: AssetSpec | None = None,
):
    """生成角色 sprite sheet。"""
    from generator.characters import CharacterGenerator, CharacterGenerationRequest

    spec = spec or build_default_asset_spec(description, "character")
    image_gen = create_image_generator(output_dir / "_temp", use_gemini)
    char_gen = CharacterGenerator(image_gen, output_dir / "characters")

    # 使用 slug 作为角色类型
    char_type = slugify(spec.prompt, max_words=3)
    tags = extract_tags(spec.prompt)

    request = CharacterGenerationRequest(
        character_type=char_type,
        description=spec.prompt,
        style=image_style_from_value(spec.style),
        frame_size=spec.frame_size or (32, 48),
        directions=directions_to_model(spec.directions or FOUR_DIRECTIONS),
        animations=spec.animations or ["idle", "walk"],
        frames_per_animation=spec.frames or 4,
        fps=spec.fps,
        seed=seed or hash(spec.prompt) % 10000,
        tags=tags,
    )

    print(f"正在生成角色: {spec.prompt}")
    print(f"  asset slug: {char_type}")
    print(f"  规则: {spec.profile}")
    print(f"  单帧尺寸: {request.frame_size}")
    print(f"  动作: {request.animations}")
    print(f"  方向: {[d.value for d in request.directions]}")
    print(f"  每动作帧数: {request.frames_per_animation}, fps: {request.fps or 'auto'}")
    print(f"  提取标签: {tags}")
    if use_gemini:
        print("  使用 Gemini AI...")
        print(
            "  注意："
            f"{len(request.directions)} 方向 × {len(request.animations)} 动作 × "
            f"{request.frames_per_animation} 帧 = "
            f"{len(request.directions) * len(request.animations) * request.frames_per_animation} 张图"
        )
        print("  预计时间: 2-5 分钟")
    else:
        print("  使用 Mock 模式（即时）...")

    result = char_gen.generate(request)

    if result.success:
        print(f"\n[成功] 角色生成完成")
        print(f"  asset_id: {result.asset_id}")
        print(f"  sprite sheet: {result.sheet_path}")
        print(f"  metadata: {result.metadata_path}")
        print(f"  动画数: {len(result.metadata.animations)}")
        print(f"  方向: {[d.value for d in result.metadata.directions]}")
        print(f"  单帧尺寸: {result.metadata.frame_size}")
        return result
    else:
        print(f"\n[失败] {result.error}")
        return None


def generate_vfx(
    description: str,
    output_dir: Path,
    use_gemini: bool,
    seed: int = None,
    spec: AssetSpec | None = None,
):
    """生成 VFX sprite sheet。"""
    from generator.vfx import VFXGenerator, VFXGenerationRequest
    from generator.models.vfx import BlendMode, VFXCategory

    spec = spec or build_default_asset_spec(description, "vfx")
    image_gen = create_image_generator(output_dir / "_temp", use_gemini)
    vfx_gen = VFXGenerator(image_gen, output_dir / "vfx")

    vfx_type = slugify(spec.prompt, max_words=2)
    tags = extract_tags(spec.prompt)
    category = VFXCategory(spec.category or "combat")
    blend = BlendMode(spec.blend or "normal")

    request = VFXGenerationRequest(
        vfx_type=vfx_type,
        description=spec.prompt,
        frame_size=spec.frame_size or (64, 64),
        style=image_style_from_value(spec.style),
        frames=spec.frames or 8,
        fps=spec.fps or 12,
        loop=bool(spec.loop),
        blend=blend,
        category=category,
        seed=seed or hash(spec.prompt) % 10000,
        tags=tags,
    )

    print(f"正在生成特效: {spec.prompt}")
    print(f"  asset slug: {vfx_type}")
    print(f"  单帧尺寸: {request.frame_size}")
    print(f"  类别: {category.value}, blend: {blend.value}")
    print(f"  帧数: {request.frames} @ {request.fps}fps, loop={request.loop}")
    print(f"  提取标签: {tags}")
    if use_gemini:
        print(f"  使用 Gemini AI（{request.frames} 帧，约 1-2 分钟）...")
    else:
        print("  使用 Mock 模式（即时）...")

    result = vfx_gen.generate(request)

    if result.success:
        print(f"\n[成功] 特效生成完成")
        print(f"  asset_id: {result.asset_id}")
        print(f"  sprite sheet: {result.sheet_path}")
        print(f"  类别: {result.metadata.category.value}")
        print(f"  帧数: {result.metadata.frames} @ {result.metadata.fps}fps")
        print(f"  blend: {result.metadata.blend.value}")
        return result
    else:
        print(f"\n[失败] {result.error}")
        return None


def prepare_generated_map_output_dir(output_dir: Path) -> None:
    """Remove stale generated files from a map output package before a new run."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_dirs = ["objects", "_temp", "godot", "tilesets"]
    generated_files = [
        "art_request.json",
        "map_asset_generation_specs.json",
        "map_spec.json",
        "map_data.json",
        "validation_report.json",
        "tiled_validation_report.json",
        "map_object_sprite_report.json",
        "ground_detail_tileset_report.json",
        "map.tiled.json",
        "preview.png",
        "preview_debug.png",
    ]
    for name in generated_dirs:
        target = output_dir / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for name in generated_files:
        target = output_dir / name
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)


def build_map_art_request(tilemap, description: str) -> dict:
    """Export the logical map contract expected by an external art pipeline."""
    tile_w, tile_h = tilemap.map.tile_width, tilemap.map.tile_height
    return {
        "version": "1.0",
        "kind": "logical_map_art_request",
        "description": description,
        "theme": str(tilemap.metadata.get("theme", "")),
        "seed": int(tilemap.metadata.get("seed", 0) or 0),
        "map_size": [tilemap.map.width, tilemap.map.height],
        "tile_size": [tile_w, tile_h],
        "canvas_size": [tilemap.map.width * tile_w, tilemap.map.height * tile_h],
        "tileset": {
            "id": tilemap.tileset.id,
            "image": tilemap.tileset.image,
            "columns": tilemap.tileset.columns,
            "tile_count": tilemap.tileset.tile_count,
        },
        "layers": {
            name: {
                "semantic": name,
                "width": tilemap.map.width,
                "height": tilemap.map.height,
                "visible_by_default": name != "collision",
            }
            for name in ("terrain", "path", "building", "decoration", "collision")
        },
        "regions": [
            {
                "id": region.id,
                "type": region.type,
                "bounds": region.bounds,
                "pixel_bounds": [
                    region.bounds[0] * tile_w,
                    region.bounds[1] * tile_h,
                    region.bounds[2] * tile_w,
                    region.bounds[3] * tile_h,
                ],
                "center": region.center,
                "access": region.access,
                "priority": region.priority,
            }
            for region in tilemap.regions
        ],
        "objects": [map_object_art_request_item(obj, tile_w, tile_h) for obj in tilemap.objects],
        "events": [
            {
                "id": event.id,
                "type": event.type,
                "x": event.x,
                "y": event.y,
                "pixel_position": [event.x * tile_w, event.y * tile_h],
                "properties": {
                    key: value
                    for key, value in sorted((event.properties or {}).items())
                    if isinstance(value, (str, int, float, bool))
                },
            }
            for event in tilemap.events
        ],
    }


def map_object_art_request_item(obj, tile_w: int, tile_h: int) -> dict:
    props = obj.properties or {}
    display_name = object_display_name(obj)
    category = infer_map_art_category(obj)
    placement_zone, relative_position, facing = infer_map_art_placement(obj, category)
    anchor = infer_map_art_anchor(obj, category)
    blocking = bool(props.get("blocking", False))
    return {
        "id": obj.id,
        "type": obj.type,
        "display_name": display_name,
        "category": category,
        "x": obj.x,
        "y": obj.y,
        "footprint": [obj.width, obj.height],
        "pixel_bounds": [obj.x * tile_w, obj.y * tile_h, obj.width * tile_w, obj.height * tile_h],
        "runtime_size": [obj.width * tile_w, obj.height * tile_h],
        "placement_zone": placement_zone,
        "relative_position": relative_position,
        "facing": facing,
        "anchor": anchor,
        "blocking": blocking,
        "text": props.get("text"),
        "activity": props.get("activity"),
        "source_clause": props.get("source_clause"),
        "properties": {
            key: value
            for key, value in sorted(props.items())
            if isinstance(value, (str, int, float, bool))
        },
    }


def generate_map(
    description: str,
    output_dir: Path,
    use_gemini: bool,
    seed: int = None,
    spec: AssetSpec | None = None,
    confirm_asset_specs: bool = False,
    input_func: Callable[[str], str] = input,
):
    """Generate the logical map package only.

    The map generator owns topology, semantic layers, object placement,
    collision, validation, and engine exports. Pixel-art production is handled
    by an external art pipeline that consumes art_request.json.
    """
    from generator.models import GenerateRequest
    from generator.parser import RulePromptParser
    from generator.map import MapGenerator
    from generator.export import GodotExporter, TiledExporter, TiledJsonValidator
    from generator.models.base import write_json, write_model_json
    from generator.render import PreviewRenderer
    from generator.validation import Validator

    spec = spec or build_default_asset_spec(description, "map")
    print(f"正在生成地图: {spec.prompt}")

    # 解析
    parser = RulePromptParser()
    request = GenerateRequest(
        prompt=spec.prompt,
        map_size=spec.map_size or (64, 64),
        tile_size=spec.tile_size or (32, 32),
        seed=seed,
    )
    map_spec = parser.parse(request)

    # 生成
    generator = MapGenerator()
    tilemap = generator.generate(map_spec)

    print(f"  地图尺寸: {tilemap.map.width}x{tilemap.map.height}")
    print(f"  tile size: {tilemap.map.tile_width}x{tilemap.map.tile_height}")
    print(f"  区域数: {len(tilemap.regions)}")
    print(f"  对象数: {len(tilemap.objects)}")
    if use_gemini:
        print("  注意: 地图生成器只输出逻辑地图，不调用 Gemini 生成美术。")
    if confirm_asset_specs:
        print("  注意: 地图对象美术规格确认已移出地图生成流程，请使用 art_request.json 对接外部美术 skill。")

    prepare_generated_map_output_dir(output_dir)
    renderer = PreviewRenderer()
    renderer.ensure_tileset_png(output_dir / "tilesets" / "default_rpg_32.png")

    # 预览和标准逻辑数据包
    preview_path = output_dir / "preview.png"
    renderer.render(tilemap, preview_path)
    print(f"  预览图: {preview_path}")
    debug_preview_path = output_dir / "preview_debug.png"
    renderer.render(tilemap, debug_preview_path, debug=True)

    tiled = TiledExporter().export(tilemap, output_dir / "map.tiled.json")
    validation_report = Validator().validate(tilemap)
    tiled_validation_report = TiledJsonValidator().validate(tiled)
    art_request = build_map_art_request(tilemap, spec.prompt)
    write_model_json(output_dir / "map_spec.json", map_spec)
    write_model_json(output_dir / "map_data.json", tilemap)
    write_model_json(output_dir / "validation_report.json", validation_report)
    write_model_json(output_dir / "tiled_validation_report.json", tiled_validation_report)
    write_json(output_dir / "art_request.json", art_request)
    print(f"  map_data: {output_dir / 'map_data.json'}")
    print(f"  Tiled JSON: {output_dir / 'map.tiled.json'}")
    print(f"  美术请求: {output_dir / 'art_request.json'}")

    # 导出 Godot
    GodotExporter().export(tilemap, output_dir / "godot", "scene")
    print(f"  Godot 场景: {output_dir}/godot/scene.tscn")

    print(f"\n[成功] 地图生成完成")
    return tilemap


SCHOOL_PLACEMENT_BY_TYPE = {
    "dormitory": ("upper_left", "left of school shop and north of playground", "faces_south"),
    "school_shop": ("upper_right", "right of dormitory and near dining hall", "faces_south"),
    "dining_hall": ("upper_right", "south of school shop and north of playground", "faces_south"),
    "laundry_line": ("near:dormitory_01", "attached to dormitory facade", "faces_south"),
    "shop_goods": ("near:school_shop_01", "inside school shop counter", "front_visible"),
    "chimney_smoke": ("near:dining_hall_01", "above dining hall chimney", "vertical_up"),
    "lunch_box_stack": ("near:dining_hall_01", "beside dining hall entrance", "front_visible"),
    "coal_pile": ("near:dining_hall_01", "beside dining hall wall", "front_visible"),
    "firewood_pile": ("near:dining_hall_01", "beside dining hall wall", "front_visible"),
    "rice_washing_pool": ("near:dining_hall_01", "left-front of dining hall", "axis_east_west"),
    "student_rice_washing": ("near:rice_washing_pool_01", "beside rice washing pool", "faces_pool"),
    "school_sign": ("school_facade", "attached to main teaching building front facade", "faces_south"),
    "school_slogan_banner": ("school_facade", "attached to main teaching building front facade", "faces_south"),
    "rail_bell": ("school_facade", "under teaching building eaves", "faces_south"),
    "olympic_poster": ("school_facade", "attached to front corridor wall", "faces_south"),
    "flag_pole": ("school_front", "in front of teaching building", "faces_south"),
    "basketball_hoop": ("playground", "on playground edge facing play area", "hoop_faces_play_area"),
    "horizontal_bar": ("playground", "on playground activity area", "axis_east_west"),
    "parallel_bars": ("playground", "on playground activity area", "axis_east_west"),
    "ping_pong_table": ("playground", "in playground with long side east-west", "axis_east_west"),
    "power_pole_speaker": ("playground", "speaker faces playground crowd area", "speaker_faces_playground"),
    "water_well": ("playground", "near playground activity area", "front_visible"),
    "student_activity": ("playground", "in playground activity area", "faces_player_access"),
    "bicycle": ("mud_road", "parked along dirt road edge", "axis_east_west"),
    "dog": ("mud_road", "walking along dirt road", "follows_path_axis"),
    "chicken": ("mud_road", "pecking along dirt road edge", "follows_path_axis"),
}


def object_display_name(obj) -> str:
    props = obj.properties or {}
    return str(props.get("display_name") or props.get("label") or obj.type)


def infer_map_art_category(obj) -> str:
    display_name = object_display_name(obj)
    footprint = (obj.width, obj.height)
    area = footprint[0] * footprint[1]
    object_type = obj.type
    if object_type in {"school_sign", "school_slogan_banner"} or any(word in display_name for word in ("标语", "招牌", "牌匾", "牌")):
        return "text_sign"
    if object_type in {"olympic_poster", "rail_bell"} or any(word in display_name for word in ("海报", "黑板报", "走廊", "墙面")):
        return "facade_overlay"
    if object_type in {"dormitory", "school_shop", "dining_hall"} or area >= 12:
        return "building"
    if object_type in {"basketball_hoop", "power_pole_speaker", "flag_pole", "horizontal_bar", "parallel_bars", "laundry_line"}:
        return "thin_prop"
    if any(word in display_name for word in ("电线杆", "喇叭", "篮球架", "旗杆", "单杠", "双杠", "晾衣绳", "栏杆")):
        return "thin_prop"
    if footprint[0] > 1 or footprint[1] > 1:
        return "large_prop"
    return "small_prop"


def infer_map_art_placement(obj, category: str) -> tuple[str, str, str]:
    props = obj.properties or {}
    placement = str(props.get("placement") or "")
    if obj.type in SCHOOL_PLACEMENT_BY_TYPE:
        default_zone, default_relative, default_facing = SCHOOL_PLACEMENT_BY_TYPE[obj.type]
    else:
        default_zone, default_relative, default_facing = "auto", "unspecified", "front_visible"

    placement_zone = placement or default_zone
    source_clause = str(props.get("source_clause") or "")
    relative_position = source_clause[:120] if source_clause else default_relative
    facing = str(props.get("facing") or default_facing)

    if category == "building" and facing == "front_visible":
        facing = "faces_south"
    if category == "text_sign":
        facing = "faces_south"
    if category == "facade_overlay" and placement_zone == "school_facade":
        facing = "faces_south"

    return placement_zone, relative_position, facing


def infer_map_art_anchor(obj, category: str) -> str:
    if category in {"building", "thin_prop"}:
        return "bottom_center"
    if category in {"facade_overlay", "text_sign"}:
        return "center"
    if obj.height > 1:
        return "bottom_center"
    return "center"


def infer_map_object_additions(description: str) -> list[MapObjectAdditionSpec]:
    """从补充描述里识别待追加物件；识别不到时降级为一个自定义物件。"""
    import re

    lower = description.lower()
    additions: list[MapObjectAdditionSpec] = []
    for object_type, preset in MAP_OBJECT_PRESETS.items():
        keywords = preset["keywords"]
        matched_keyword = next((keyword for keyword in keywords if keyword.lower() in lower), None)
        if not matched_keyword:
            continue
        count = int(preset["count"])
        count_match = re.search(rf"(\d+)\s*个?\s*{re.escape(matched_keyword)}", description, re.IGNORECASE)
        if not count_match:
            count_match = re.search(rf"{re.escape(matched_keyword)}\s*(\d+)\s*个?", description, re.IGNORECASE)
        if count_match:
            count = int(count_match.group(1))
        additions.append(
            MapObjectAdditionSpec(
                name=str(preset["name"]),
                object_type=object_type,
                description=str(preset["description"]),
                count=count,
                footprint=tuple(preset["footprint"]),
                blocking=bool(preset["blocking"]),
                placement=str(preset["placement"]),
            )
        )

    if additions:
        return additions

    name = description.strip()
    cleaned = re.sub(r"^(增加|添加|加上|放置|补充|加入)\s*", "", name)
    cleaned = cleaned.strip(" ，,。")
    return [
        MapObjectAdditionSpec(
            name=cleaned or "自定义物件",
            object_type=slugify(cleaned or description, max_words=2),
            description=cleaned or description,
            count=1,
            footprint=(1, 1),
            blocking=True,
            placement="random_walkable",
        )
    ]


def configure_map_object_additions(
    description: str,
    tilemap,
    input_func: Callable[[str], str] = input,
) -> list[MapObjectAdditionSpec]:
    additions = infer_map_object_additions(description)
    print("\n识别到要补充的物件：")
    for index, item in enumerate(additions, 1):
        print(f"  {index}. {item.name} ({item.object_type})")

    configured: list[MapObjectAdditionSpec] = []
    region_options = _region_choice_options(tilemap)
    for index, item in enumerate(additions, 1):
        print(f"\n配置物件 {index}/{len(additions)}：{item.name}")
        item.name = prompt_text("显示名称", item.name, input_func)
        item.object_type = prompt_text("内部类型 slug", item.object_type, input_func)
        item.description = prompt_text("逻辑描述", item.description, input_func)
        item.count = prompt_positive_int("放置数量", item.count, input_func)
        item.footprint = prompt_size_choice(
            "占用格数 footprint",
            [
                ((1, 1), "小装饰 / 道具"),
                ((1, 2), "竖向物件 / 路灯"),
                ((2, 1), "长条物件 / 乒乓球台 / 长椅"),
                ((2, 2), "大装饰 / 花坛"),
                ((3, 2), "较大设施"),
            ],
            item.footprint,
            input_func,
        )
        item.blocking = prompt_bool_choice("是否阻挡行走", item.blocking, input_func)
        placement = prompt_choice(
            "放置区域规则",
            [
                ("auto", "自动按物件类型推断"),
                ("playground", "操场 / 运动区域"),
                ("school_entrance", "教学楼入口附近"),
                ("random_walkable", "随机可行走区域"),
                ("region", "选择已有地图区域"),
                ("manual", "手动输入格子坐标"),
            ],
            item.placement if item.placement in {"auto", "playground", "school_entrance", "random_walkable", "region", "manual"} else "auto",
            input_func,
        )
        item.placement = placement
        item.target_region = None
        item.manual_positions = []
        if placement == "region":
            item.target_region = prompt_choice("目标地图区域", region_options, region_options[0][0], input_func)
        elif placement == "manual":
            item.manual_positions = prompt_positions("手动坐标，例 12,18;15,18", [], input_func)
            item.count = len(item.manual_positions)

        configured.append(item)

    print_map_refine_summary(configured)
    return configured


def print_map_refine_summary(additions: list[MapObjectAdditionSpec]) -> None:
    print("\n地图补充规格：")
    for item in additions:
        target = item.target_region or item.placement
        print(
            f"  - {item.name}: type={item.object_type}, count={item.count}, "
            f"footprint={format_size(item.footprint)}, blocking={item.blocking}, placement={target}"
        )


def load_tilemap_from_path(path: Path):
    from generator.models import TilemapData
    from generator.models.base import read_json

    resolved = path / "map_data.json" if path.is_dir() else path
    if not resolved.exists():
        raise FileNotFoundError(f"找不到 map_data.json: {resolved}")
    return TilemapData.model_validate(read_json(resolved)), resolved


def refine_map_with_objects(
    tilemap,
    additions: list[MapObjectAdditionSpec],
    output_dir: Path,
    use_gemini: bool,
    seed: int | None = None,
):
    from generator.models import ObjectData

    if use_gemini:
        print("  注意: 地图补充只更新逻辑对象，不调用 Gemini 生成 sprite。")

    result = tilemap.model_copy(deep=True)
    rng = Random(seed if seed is not None else int(result.metadata.get("seed", 0)) + 101)
    placed_objects: list[ObjectData] = []

    for item in additions:
        positions = choose_object_positions(result, item, rng)
        for position in positions:
            object_id = next_object_id(result, item.object_type)
            obj = ObjectData(
                id=object_id,
                type=item.object_type,
                x=position[0],
                y=position[1],
                width=item.footprint[0],
                height=item.footprint[1],
                properties={
                    "source": "interactive_map_refine",
                    "display_name": item.name,
                    "blocking": item.blocking,
                    "placement": item.target_region or item.placement,
                    "description": item.description,
                },
            )
            result.objects.append(obj)
            placed_objects.append(obj)

    refresh_collision_with_objects(result)
    history = list(result.metadata.get("map_refine_history", []))
    history.append(
        {
            "operation": "add_objects",
            "objects": [
                {
                    "type": item.object_type,
                    "name": item.name,
                    "count": item.count,
                    "footprint": list(item.footprint),
                    "blocking": item.blocking,
                    "placement": item.target_region or item.placement,
                }
                for item in additions
            ],
            "placed_count": len(placed_objects),
        }
    )
    result.metadata["map_refine_history"] = history[-20:]
    return result, placed_objects, {}


def choose_object_positions(tilemap, item: MapObjectAdditionSpec, rng: Random) -> list[tuple[int, int]]:
    if item.manual_positions:
        valid = [pos for pos in item.manual_positions if is_clear_for_object(tilemap, pos[0], pos[1], item.footprint)]
        if len(valid) < len(item.manual_positions):
            print(f"[警告] {item.name} 有 {len(item.manual_positions) - len(valid)} 个手动坐标不可放置，已跳过。")
        return valid[: item.count]

    candidates = candidate_positions_for_item(tilemap, item)
    rng.shuffle(candidates)
    positions: list[tuple[int, int]] = []
    reserved: list[tuple[int, int, int, int]] = []
    for x, y in candidates:
        if len(positions) >= item.count:
            break
        if overlaps_reserved(x, y, item.footprint, reserved):
            continue
        if is_clear_for_object(tilemap, x, y, item.footprint):
            positions.append((x, y))
            reserved.append((x, y, item.footprint[0], item.footprint[1]))

    if len(positions) < item.count:
        print(f"[警告] {item.name} 计划放置 {item.count} 个，实际找到 {len(positions)} 个可用位置。")
    return positions


def candidate_positions_for_item(tilemap, item: MapObjectAdditionSpec) -> list[tuple[int, int]]:
    placement = item.placement
    if placement == "auto":
        placement = auto_placement_for_item(item)
    if placement == "region" and item.target_region:
        if item.target_region == "all":
            return walkable_positions(tilemap)
        return positions_from_regions(tilemap, [item.target_region], by_id=True)
    if placement == "playground":
        candidates = positions_from_regions(tilemap, ["playground"])
        if candidates:
            return candidates
    if placement == "school_entrance":
        candidates = school_entrance_positions(tilemap)
        if candidates:
            return candidates
    return walkable_positions(tilemap)


def auto_placement_for_item(item: MapObjectAdditionSpec) -> str:
    if item.object_type in {"ping_pong_table", "basketball_hoop"}:
        return "playground"
    if item.object_type in {"flower_pot"}:
        return "school_entrance"
    return "random_walkable"


def _region_choice_options(tilemap) -> list[tuple[str, str]]:
    if not tilemap.regions:
        return [("all", "全图")]
    return [
        (region.id, f"{region.type} {region.id} bounds={region.bounds}")
        for region in tilemap.regions
    ]


def positions_from_regions(tilemap, targets: list[str], by_id: bool = False) -> list[tuple[int, int]]:
    candidates: list[tuple[int, int]] = []
    for region in tilemap.regions:
        matches = region.id in targets if by_id else region.type in targets or region.id in targets
        if not matches:
            continue
        x, y, width, height = region.bounds
        for yy in range(y, y + height):
            for xx in range(x, x + width):
                candidates.append((xx, yy))
    return candidates


def school_entrance_positions(tilemap) -> list[tuple[int, int]]:
    school = next((region for region in tilemap.regions if region.type == "school"), None)
    if not school:
        return []
    ax, ay = school.access
    points: list[tuple[int, int]] = []
    for radius in range(1, 9):
        for yy in range(ay - radius, ay + radius + 1):
            for xx in range(ax - radius, ax + radius + 1):
                if abs(xx - ax) + abs(yy - ay) <= radius:
                    points.append((xx, yy))
    return points


def walkable_positions(tilemap) -> list[tuple[int, int]]:
    width, height = tilemap.map.width, tilemap.map.height
    return [(x, y) for y in range(height) for x in range(width)]


def is_clear_for_object(tilemap, x: int, y: int, footprint: tuple[int, int]) -> bool:
    width, height = tilemap.map.width, tilemap.map.height
    obj_w, obj_h = footprint
    if x < 0 or y < 0 or x + obj_w > width or y + obj_h > height:
        return False
    for yy in range(y, y + obj_h):
        for xx in range(x, x + obj_w):
            index = yy * width + xx
            if tilemap.layers["collision"][index] != 0:
                return False
            if tilemap.layers.get("path", [])[index] != 0:
                return False
            if tilemap.layers.get("building", [])[index] != 0:
                return False
            if tilemap.layers.get("decoration", [])[index] != 0:
                return False
            if is_protected_map_point(tilemap, xx, yy):
                return False
    return not overlaps_existing_object(tilemap, x, y, footprint)


def is_protected_map_point(tilemap, x: int, y: int) -> bool:
    if any(region.access == [x, y] for region in tilemap.regions):
        return True
    return any(event.x == x and event.y == y for event in tilemap.events)


def overlaps_existing_object(tilemap, x: int, y: int, footprint: tuple[int, int]) -> bool:
    return any(rects_overlap((x, y, footprint[0], footprint[1]), (obj.x, obj.y, obj.width, obj.height)) for obj in tilemap.objects)


def overlaps_reserved(x: int, y: int, footprint: tuple[int, int], reserved: list[tuple[int, int, int, int]]) -> bool:
    return any(rects_overlap((x, y, footprint[0], footprint[1]), rect) for rect in reserved)


def rects_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def next_object_id(tilemap, object_type: str) -> str:
    existing = {obj.id for obj in tilemap.objects}
    index = 1
    while True:
        candidate = f"{object_type}_{index:02d}"
        if candidate not in existing:
            return candidate
        index += 1


def refresh_collision_with_objects(tilemap) -> None:
    from generator.config import BLOCKING_TILE_IDS, PATH_TILE_IDS

    width, height = tilemap.map.width, tilemap.map.height
    collision = tilemap.layers["collision"]
    for y in range(height):
        for x in range(width):
            index = y * width + x
            blocked = False
            if tilemap.layers["terrain"][index] in BLOCKING_TILE_IDS:
                blocked = True
            if tilemap.layers["building"][index] in BLOCKING_TILE_IDS:
                blocked = True
            if tilemap.layers["decoration"][index] in BLOCKING_TILE_IDS:
                blocked = True
            if tilemap.layers["path"][index] in PATH_TILE_IDS:
                blocked = False
            collision[index] = 1 if blocked else 0

    for obj in tilemap.objects:
        blocking = bool(obj.properties.get("blocking", False)) or obj.type in {"chest", "market_stall"}
        if obj.type == "door":
            set_collision(tilemap, obj.x, obj.y, 0)
            if obj.y > 0:
                set_collision(tilemap, obj.x, obj.y - 1, 0)
            continue
        if not blocking:
            continue
        for yy in range(obj.y, obj.y + obj.height):
            for xx in range(obj.x, obj.x + obj.width):
                set_collision(tilemap, xx, yy, 1)

    for event in tilemap.events:
        if event.type == "player_spawn":
            set_collision(tilemap, event.x, event.y, 0)


def set_collision(tilemap, x: int, y: int, value: int) -> None:
    if 0 <= x < tilemap.map.width and 0 <= y < tilemap.map.height:
        tilemap.layers["collision"][y * tilemap.map.width + x] = value


def export_refined_map(tilemap, output_dir: Path, report: dict) -> None:
    from generator.export import TiledExporter, TiledJsonValidator
    from generator.models.base import write_json, write_model_json
    from generator.render import PreviewRenderer
    from generator.validation import Validator

    output_dir.mkdir(parents=True, exist_ok=True)
    renderer = PreviewRenderer()
    renderer.ensure_tileset_png(output_dir / "tilesets" / "default_rpg_32.png")
    renderer.render(tilemap, output_dir / "preview.png")
    renderer.render(tilemap, output_dir / "preview_debug.png", debug=True)
    tiled = TiledExporter().export(tilemap, output_dir / "map.tiled.json")
    validation_report = Validator().validate(tilemap)
    tiled_validation_report = TiledJsonValidator().validate(tiled)
    report["validation_passed"] = validation_report.passed
    report["tiled_validation_passed"] = tiled_validation_report.passed
    write_model_json(output_dir / "map_data.json", tilemap)
    write_model_json(output_dir / "validation_report.json", validation_report)
    write_model_json(output_dir / "tiled_validation_report.json", tiled_validation_report)
    write_json(output_dir / "map_refine_report.json", report)


def run_map_refine_interactive(
    output_dir: Path,
    use_gemini: bool,
    input_func: Callable[[str], str] = input,
) -> None:
    source_text = prompt_required_text("已有地图路径（map_data.json 或其所在目录）", input_func)
    tilemap, source_path = load_tilemap_from_path(Path(source_text))
    print(f"已读取地图: {source_path}")
    print(f"  尺寸: {tilemap.map.width}x{tilemap.map.height}, 区域数: {len(tilemap.regions)}, 对象数: {len(tilemap.objects)}")

    description = prompt_required_text("要补充的内容，例如 增加乒乓球台和花盆", input_func)
    additions = configure_map_object_additions(description, tilemap, input_func)
    default_output = output_dir / f"{source_path.parent.name}_refined"
    target_output = Path(prompt_text("输出目录", str(default_output), input_func))

    seed_text = input_func("随机种子（留空自动）: ").strip()
    seed = int(seed_text) if seed_text else None
    refined, placed_objects, _assets = refine_map_with_objects(tilemap, additions, target_output, use_gemini, seed)
    report = {
        "source_map": str(source_path),
        "prompt": description,
        "placed_objects": [
            {
                "id": obj.id,
                "type": obj.type,
                "x": obj.x,
                "y": obj.y,
                "width": obj.width,
                "height": obj.height,
            }
            for obj in placed_objects
        ],
    }
    export_refined_map(refined, target_output, report)
    print("\n[成功] 地图补充完成")
    print(f"  新 map_data: {target_output / 'map_data.json'}")
    print(f"  预览图: {target_output / 'preview.png'}")
    print(f"  Tiled JSON: {target_output / 'map.tiled.json'}")


def create_image_generator(output_dir: Path, use_gemini: bool):
    """创建图像生成器。"""
    if use_gemini:
        try:
            from generator.assets.gemini_generator import GeminiImageGenerator
            return GeminiImageGenerator(output_dir)
        except Exception as e:
            raise RuntimeError(f"Gemini 初始化失败，已停止生成，避免误用 Mock 占位图: {e}") from e

    from generator.assets.image_generation import MockImageGenerator
    return MockImageGenerator(output_dir)


def run_spec(
    spec: AssetSpec,
    output_dir: Path,
    use_gemini: bool,
    seed: int = None,
    confirm_asset_specs: bool = False,
    input_func: Callable[[str], str] = input,
):
    """按最终规格运行一次生成并返回结果。"""
    generators = {
        "object": generate_object,
        "character": generate_character,
        "vfx": generate_vfx,
        "map": generate_map,
    }
    func = generators.get(spec.asset_type)
    if not func:
        print(f"[错误] 不支持的类型: {spec.asset_type}")
        return None
    if spec.asset_type == "map":
        return func(spec.prompt, output_dir, use_gemini, seed, spec, confirm_asset_specs, input_func)
    return func(spec.prompt, output_dir, use_gemini, seed, spec)


def run_one(
    description: str,
    asset_type: str,
    output_dir: Path,
    use_gemini: bool,
    seed: int = None,
    confirm_asset_specs: bool = False,
):
    """按默认规则运行一次生成并返回结果。"""
    spec = build_default_asset_spec(description, asset_type)
    print_spec_summary(spec)
    return run_spec(spec, output_dir, use_gemini, seed, confirm_asset_specs=confirm_asset_specs)


def run_batch(batch_file: Path, output_dir: Path, use_gemini: bool):
    """批量生成：从文件读取描述，每行一个。

    支持格式：
        描述                       - 自动判断类型
        type: 描述                 - 显式指定类型，如 character: 兔子战士
        # 注释行                   - 以 # 开头的行被跳过
        空行                       - 跳过
    """
    if not batch_file.exists():
        print(f"[错误] 文件不存在: {batch_file}")
        return

    print(f"读取批量文件: {batch_file}")
    lines = batch_file.read_text(encoding="utf-8").splitlines()

    tasks = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 检查显式类型
        if ":" in line:
            type_part, _, desc = line.partition(":")
            type_part = type_part.strip().lower()
            if type_part in ("object", "character", "vfx", "map"):
                tasks.append((desc.strip(), type_part))
                continue

        # 自动判断
        tasks.append((line, detect_asset_type(line)))

    print(f"共 {len(tasks)} 个任务\n")

    success = 0
    failed = 0
    for i, (desc, asset_type) in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {desc} ({asset_type})")
        print("-" * 60)
        try:
            result = run_one(desc, asset_type, output_dir, use_gemini)
            if result:
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[错误] {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"批量完成: 成功 {success}, 失败 {failed}")
    print("=" * 60)


def run_interactive(output_dir: Path, use_gemini: bool):
    """交互模式：循环接收用户输入，并逐项确认素材规格。"""
    print("\n" + "=" * 60)
    print("交互模式 - 生成素材或补充已有地图（输入 quit/q 退出）")
    print("=" * 60)
    print(f"输出目录: {output_dir.absolute()}")
    print(f"模式: {'Gemini AI' if use_gemini else 'Mock'}")
    print()
    print("特殊命令：")
    print("  quit / q       - 退出")
    print("  refine         - 补充已有地图元素")
    print("  type:auto      - 切换为自动判断（默认）")
    print("  type:object    - 强制作为对象生成")
    print("  type:character - 强制作为角色生成")
    print("  type:vfx       - 强制作为特效生成")
    print("  type:map       - 强制作为地图生成")
    print()

    forced_type = "auto"

    while True:
        try:
            text = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[退出]")
            break

        if not text:
            continue

        if text.lower() in ("quit", "q", "exit"):
            print("[退出]")
            break

        if text.lower() in ("refine", "map-refine", "补充地图", "地图补充"):
            try:
                run_map_refine_interactive(output_dir, use_gemini)
            except Exception as e:
                print(f"[错误] {e}")
            print()
            continue

        # 切换类型
        if text.startswith("type:"):
            new_type = text[5:].strip().lower()
            if new_type in ("auto", "object", "character", "vfx", "map"):
                forced_type = new_type
                print(f"[已切换] 类型 -> {forced_type}")
                continue
            else:
                print(f"[错误] 未知类型: {new_type}")
                continue

        # 生成
        try:
            spec = configure_asset_spec(text, forced_type)
            run_spec(spec, output_dir, use_gemini, confirm_asset_specs=(spec.asset_type == "map"))
        except Exception as e:
            print(f"[错误] {e}")
        print()


def resolve_cli_description(args: argparse.Namespace) -> str | None:
    description = args.description
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file:
        if description:
            raise ValueError("不能同时传 description 和 --prompt-file")
        if not prompt_file.exists():
            raise ValueError(f"prompt 文件不存在: {prompt_file}")
        description = prompt_file.read_text(encoding="utf-8").strip()
        if not description:
            raise ValueError(f"prompt 文件为空: {prompt_file}")
    return description


def main():
    if len(sys.argv) > 1 and sys.argv[1] in SCENE_COMMANDS:
        from generator.scene.cli import main as scene_main

        sys.exit(scene_main(sys.argv[1:]))

    parser = argparse.ArgumentParser(
        description="AI RPG 素材生成器 - 输入描述，生成素材",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：

  # 默认会进入逐项规格向导
  python generate.py "一只穿着盔甲的兔子战士"

  # 跳过向导，使用 RPG 默认规则或命令行覆盖
  python generate.py "盔甲兔战士行走图" --type character --yes
  python generate.py "盔甲兔战士行走图" --type character --directions 8 --frame-size 48x64 --frames 6 --fps 10 --yes
  python generate.py "火球术爆炸特效" --type vfx --frame-size 96x96 --frames 10 --fps 15 --yes
  python generate.py "蓝色水晶" --type object --footprint 1x1 --tile-size 32x32 --yes

  # 使用真实 AI 生成（需要配置 Gemini）
  python generate.py "盔甲兔战士行走图" --gemini

  # 指定输出目录和种子
  python generate.py "魔法树" --output my_assets --seed 42 --yes

  # PowerShell 下复杂中文 prompt 推荐用单引号，或使用 --prompt-file 避免引号被截断
  python generate.py --type map --gemini --output output/gemini_school_smoke --seed 20260608 --prompt-file prompts/school_map.txt

注意：
  - Mock 模式：即时生成纯色块占位图（用于测试流程）
  - Gemini 模式：真实 AI 生成像素画（需要 5-30 秒）
  - 角色和 VFX 因为是多帧，时间会更长
""",
    )

    parser.add_argument(
        "description",
        nargs="?",
        default=None,
        help="素材描述（不传时进入交互模式）",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="从 UTF-8 文本文件读取素材描述，适合很长或包含引号的 prompt",
    )
    parser.add_argument(
        "--type", "-t",
        choices=["auto", *ASSET_TYPES],
        default="auto",
        help="素材类型（默认自动判断）",
    )
    parser.add_argument(
        "--gemini", "-g",
        action="store_true",
        help="使用 Gemini AI 真实生成（默认 Mock 模式）",
    )
    parser.add_argument(
        "--output", "-o",
        default="output/generated",
        help="输出目录（默认 output/generated）",
    )
    parser.add_argument(
        "--seed", "-s",
        type=int,
        help="随机种子（用于复现）",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="跳过逐项向导，直接使用默认规则和命令行覆盖",
    )
    parser.add_argument(
        "--style",
        choices=STYLE_VALUES,
        help="视觉风格",
    )
    parser.add_argument(
        "--frame-size",
        help="单帧尺寸，如 32x48、64x64",
    )
    parser.add_argument(
        "--frames",
        type=int,
        help="每个动作或特效的帧数",
    )
    parser.add_argument(
        "--fps",
        type=int,
        help="动画播放帧率",
    )
    parser.add_argument(
        "--directions",
        help="角色方向规则：4、8，或 down,left,right,up",
    )
    parser.add_argument(
        "--animations",
        help="角色动作列表，如 walk 或 idle,walk,attack",
    )
    parser.add_argument(
        "--footprint",
        help="物件占用格数，如 1x1、1x2、2x2",
    )
    parser.add_argument(
        "--tile-size",
        help="地图 tile 尺寸，如 32x32",
    )
    parser.add_argument(
        "--map-size",
        help="地图格数尺寸，如 64x64",
    )
    parser.add_argument(
        "--loop",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="特效是否循环播放，可用 --loop / --no-loop",
    )
    parser.add_argument(
        "--blend",
        choices=["normal", "additive", "multiply", "screen"],
        help="VFX 混合模式",
    )
    parser.add_argument(
        "--category",
        choices=["combat", "magic", "environment", "ambient", "interaction"],
        help="VFX 类别",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互模式（不传 description 时自动启用）",
    )
    parser.add_argument(
        "--batch", "-b",
        type=Path,
        help="批量模式：从文件读取描述（每行一个）",
    )
    args = parser.parse_args()

    try:
        args.description = resolve_cli_description(args)
    except ValueError as e:
        parser.error(str(e))

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 批量模式
    if args.batch:
        run_batch(args.batch, output_dir, args.gemini)
        return

    # 交互模式（显式或没传 description）
    if args.interactive or not args.description:
        run_interactive(output_dir, args.gemini)
        return

    # 单次模式：默认先逐项配置；--yes 用于自动化直接生成。
    asset_type = args.type if args.type != "auto" else detect_asset_type(args.description)

    print("="*60)
    print("AI RPG 素材生成器")
    print("="*60)
    print(f"描述: {args.description}")
    print(f"类型: {asset_type}")
    print(f"模式: {'Gemini AI' if args.gemini else 'Mock'}")
    print(f"输出: {output_dir.absolute()}")
    print()

    try:
        if args.yes:
            spec = build_default_asset_spec(args.description, asset_type)
            spec = apply_cli_overrides(spec, args)
            print_spec_summary(spec)
        else:
            spec = configure_asset_spec(args.description, args.type)
            spec = apply_cli_overrides(spec, args)
        run_spec(
            spec,
            output_dir,
            args.gemini,
            args.seed,
            confirm_asset_specs=(spec.asset_type == "map" and not args.yes),
        )
        print()
        print(f"输出目录: {output_dir.absolute()}")
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
