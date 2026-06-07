from __future__ import annotations


DEMO_CASES = [
    ("autumn_village", "examples/prompts/autumn_village.txt", 20260605),
    ("dungeon_demo", "examples/prompts/dungeon.txt", 20260606),
    ("snow_camp_demo", "examples/prompts/snow_camp.txt", 20260607),
    ("desert_ruins_demo", "examples/prompts/desert_ruins.txt", 20260609),
    ("seaside_village_demo", "examples/prompts/seaside_village.txt", 20260610),
]

DEMO_NAMES = tuple(name for name, _prompt_file, _seed in DEMO_CASES)

