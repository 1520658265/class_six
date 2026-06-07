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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


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

    # 地图关键词（最高优先级 - 整体场景）
    map_keywords = [
        "地图", "村庄", "城市", "场景", "关卡", "地牢", "营地", "遗迹",
        "广场", "村落", "小镇", "城堡内", "整片", "整个",
        "map", "village", "city", "scene", "level", "dungeon", "camp",
        "ruins", "town", "plaza",
    ]

    # 角色关键词（实体生物）
    character_keywords = [
        "战士", "兔子", "人物", "角色", "村民", "商人", "怪物", "敌人",
        "国王", "公主", "骑士", "法师", "弓箭手", "盗贼", "牧师", "nps",
        "精灵", "矮人", "兽人", "骷髅", "僵尸", "史莱姆", "幽灵", "龙",
        "猫", "狗", "牛", "马", "羊", "鸡", "鸭",
        "warrior", "character", "person", "knight", "wizard", "merchant",
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

    # 1. 检查地图（最优先）
    if any(kw in desc_lower for kw in map_keywords):
        # 但要排除"村民"这种角色词
        if not any(kw in desc_lower for kw in ["村民", "商人", "村长"]):
            return "map"

    # 2. 检查角色
    if any(kw in desc_lower for kw in character_keywords):
        return "character"

    # 3. 检查 VFX（需要明确的特效词）
    if any(kw in desc_lower for kw in vfx_action_keywords):
        return "vfx"
    if any(kw in desc_lower for kw in vfx_effect_types):
        return "vfx"
    if any(kw in desc_lower for kw in weather_keywords):
        return "vfx"

    # 4. 默认作为对象（树、石头、蘑菇、宝箱等静态物品）
    return "object"


def generate_object(description: str, output_dir: Path, use_gemini: bool, seed: int = None):
    """生成单个对象素材。"""
    from generator.assets.object_generator import (
        ObjectGenerator,
        ObjectGenerationRequest,
    )

    image_gen = create_image_generator(output_dir / "_temp", use_gemini)
    obj_gen = ObjectGenerator(image_gen, output_dir / "objects")

    # 使用 slug 作为对象类型（英文友好）
    object_type = slugify(description, max_words=2)
    tags = extract_tags(description)

    request = ObjectGenerationRequest(
        object_type=object_type,
        description=description,
        footprint=(1, 1),
        tags=tags,
        seed=seed or hash(description) % 10000,
    )

    print(f"正在生成对象: {description}")
    print(f"  asset slug: {object_type}")
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
        return result
    else:
        print(f"\n[失败] {result.error}")
        return None


def generate_character(description: str, output_dir: Path, use_gemini: bool, seed: int = None):
    """生成角色 sprite sheet。"""
    from generator.characters import CharacterGenerator, CharacterGenerationRequest

    image_gen = create_image_generator(output_dir / "_temp", use_gemini)
    char_gen = CharacterGenerator(image_gen, output_dir / "characters")

    # 使用 slug 作为角色类型
    char_type = slugify(description, max_words=3)
    tags = extract_tags(description)

    request = CharacterGenerationRequest(
        character_type=char_type,
        description=description,
        seed=seed or hash(description) % 10000,
        tags=tags,
    )

    print(f"正在生成角色: {description}")
    print(f"  asset slug: {char_type}")
    print(f"  提取标签: {tags}")
    if use_gemini:
        print("  使用 Gemini AI...")
        print("  注意：4 方向 × 2 动作 × 4 帧 = 32 张图")
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
        return result
    else:
        print(f"\n[失败] {result.error}")
        return None


def generate_vfx(description: str, output_dir: Path, use_gemini: bool, seed: int = None):
    """生成 VFX sprite sheet。"""
    from generator.vfx import VFXGenerator, VFXGenerationRequest
    from generator.models.vfx import BlendMode, VFXCategory

    image_gen = create_image_generator(output_dir / "_temp", use_gemini)
    vfx_gen = VFXGenerator(image_gen, output_dir / "vfx")

    vfx_type = slugify(description, max_words=2)
    tags = extract_tags(description)

    # 自动判断类别
    desc_lower = description.lower()
    if any(k in desc_lower for k in ["火", "雷", "冰", "斩", "fire", "thunder", "ice", "slash", "lightning"]):
        category = VFXCategory.COMBAT
        blend = BlendMode.ADDITIVE
    elif any(k in desc_lower for k in ["治疗", "魔法", "传送", "heal", "magic", "teleport"]):
        category = VFXCategory.MAGIC
        blend = BlendMode.ADDITIVE
    elif any(k in desc_lower for k in ["雨", "雪", "落叶", "rain", "snow", "leaves"]):
        category = VFXCategory.ENVIRONMENT
        blend = BlendMode.NORMAL
    else:
        category = VFXCategory.COMBAT
        blend = BlendMode.NORMAL

    request = VFXGenerationRequest(
        vfx_type=vfx_type,
        description=description,
        frames=8,
        fps=12,
        loop=False,
        blend=blend,
        category=category,
        seed=seed or hash(description) % 10000,
    )

    print(f"正在生成特效: {description}")
    print(f"  asset slug: {vfx_type}")
    print(f"  类别: {category.value}, blend: {blend.value}")
    print(f"  提取标签: {tags}")
    if use_gemini:
        print(f"  使用 Gemini AI（8 帧，约 1-2 分钟）...")
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


def generate_map(description: str, output_dir: Path, use_gemini: bool, seed: int = None):
    """生成完整地图。"""
    from generator.models import GenerateRequest
    from generator.parser import RulePromptParser
    from generator.map import MapGenerator
    from generator.export import GodotExporter
    from generator.render import PreviewRenderer

    print(f"正在生成地图: {description}")

    # 解析
    parser = RulePromptParser()
    request = GenerateRequest(prompt=description, seed=seed)
    spec = parser.parse(request)

    # 生成
    generator = MapGenerator()
    tilemap = generator.generate(spec)

    print(f"  地图尺寸: {tilemap.map.width}x{tilemap.map.height}")
    print(f"  区域数: {len(tilemap.regions)}")
    print(f"  对象数: {len(tilemap.objects)}")

    # 预览
    preview_path = output_dir / "preview.png"
    PreviewRenderer().render(tilemap, preview_path)
    print(f"  预览图: {preview_path}")

    # 导出 Godot
    GodotExporter().export(tilemap, output_dir / "godot", "scene")
    print(f"  Godot 场景: {output_dir}/godot/scene.tscn")

    print(f"\n[成功] 地图生成完成")
    return tilemap


def create_image_generator(output_dir: Path, use_gemini: bool):
    """创建图像生成器。"""
    if use_gemini:
        try:
            from generator.assets.gemini_generator import GeminiImageGenerator
            return GeminiImageGenerator(output_dir)
        except Exception as e:
            print(f"[警告] Gemini 初始化失败: {e}")
            print("[警告] 自动切换到 Mock 模式")

    from generator.assets.image_generation import MockImageGenerator
    return MockImageGenerator(output_dir)


def run_one(description: str, asset_type: str, output_dir: Path, use_gemini: bool, seed: int = None):
    """运行一次生成并返回结果。"""
    generators = {
        "object": generate_object,
        "character": generate_character,
        "vfx": generate_vfx,
        "map": generate_map,
    }
    func = generators.get(asset_type)
    if not func:
        print(f"[错误] 不支持的类型: {asset_type}")
        return None
    return func(description, output_dir, use_gemini, seed)


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
    """交互模式：循环接收用户输入。"""
    print("\n" + "=" * 60)
    print("交互模式 - 输入描述生成素材（输入 quit/q 退出）")
    print("=" * 60)
    print(f"输出目录: {output_dir.absolute()}")
    print(f"模式: {'Gemini AI' if use_gemini else 'Mock'}")
    print()
    print("特殊命令：")
    print("  quit / q       - 退出")
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
        asset_type = forced_type if forced_type != "auto" else detect_asset_type(text)
        print(f"[类型: {asset_type}]")
        try:
            run_one(text, asset_type, output_dir, use_gemini)
        except Exception as e:
            print(f"[错误] {e}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="AI RPG 素材生成器 - 输入描述，生成素材",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：

  # 自动判断类型（默认 Mock 模式，快速测试）
  python generate.py "一只穿着盔甲的兔子战士"
  python generate.py "魔法森林中的发光蘑菇"
  python generate.py "火球术爆炸特效"
  python generate.py "雪地村庄，中间有篝火"

  # 显式指定类型
  python generate.py "盔甲兔战士" --type character
  python generate.py "蓝色水晶" --type object
  python generate.py "闪电链" --type vfx
  python generate.py "山间小镇" --type map

  # 使用真实 AI 生成（需要配置 Gemini）
  python generate.py "盔甲兔战士" --gemini

  # 指定输出目录和种子
  python generate.py "魔法树" --output my_assets --seed 42

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
        "--type", "-t",
        choices=["auto", "object", "character", "vfx", "map"],
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

    # 单次模式
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
        run_one(args.description, asset_type, output_dir, args.gemini, args.seed)
        print()
        print(f"输出目录: {output_dir.absolute()}")
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
