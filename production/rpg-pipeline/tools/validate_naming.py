"""
RPG 素材命名规范校验器
规范: {角色}_{动作}_{方向}_{帧号}_{图层}.png

用法: python validate_naming.py <assets_directory>
"""
import sys
import re
from pathlib import Path

VALID_ACTIONS = [
    "walk", "idle", "walk-in", "attack", "charge", "skill",
    "guard", "dodge", "hurt", "critical-hurt", "low-hp",
    "dead", "victory", "expression", "face", "portrait"
]
VALID_DIRECTIONS = ["down", "left", "right", "up", "front", "side", "back"]
VALID_LAYERS = ["base", "weapon-.*", "armor-.*", "helm-.*", "accessory-.*"]

PATTERN = re.compile(
    r"^([a-z0-9]+)_([a-z\-]+)_([a-z]+)_(\d{2})_([a-z\-]+)\.png$"
)

def validate_file(filepath: Path) -> list[str]:
    errors = []
    name = filepath.name

    if name.startswith("."):
        return []

    match = PATTERN.match(name)
    if not match:
        errors.append(f"命名格式错误: {name}")
        return errors

    _, action, direction, frame, layer = match.groups()

    if action not in VALID_ACTIONS:
        errors.append(f"未知动作 '{action}': {name}")
    if direction not in VALID_DIRECTIONS:
        errors.append(f"未知方向 '{direction}': {name}")
    if not any(re.match(p, layer) for p in VALID_LAYERS):
        errors.append(f"未知图层 '{layer}': {name}")

    return errors

def main():
    if len(sys.argv) < 2:
        print("用法: python validate_naming.py <assets_directory>")
        sys.exit(1)

    target = Path(sys.argv[1])
    if not target.is_dir():
        print(f"错误: {target} 不是有效目录")
        sys.exit(1)

    all_errors = []
    for png in target.rglob("*.png"):
        errors = validate_file(png)
        all_errors.extend(errors)

    if all_errors:
        print(f"发现 {len(all_errors)} 个命名错误:")
        for e in all_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("所有文件命名规范检查通过")

if __name__ == "__main__":
    main()
