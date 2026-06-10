from __future__ import annotations

import re


SCENE_OBJECT_CATEGORIES = {
    "building",
    "large_prop",
    "small_prop",
    "thin_prop",
    "npc",
    "facade_overlay",
    "text_sign",
}

CATEGORY_DEFAULTS: dict[str, dict[str, object]] = {
    "building": {"footprint": (8, 5), "blocking": True, "source_canvas": (256, 160), "anchor": "bottom_center"},
    "large_prop": {"footprint": (2, 1), "blocking": True, "source_canvas": (96, 64), "anchor": "center"},
    "small_prop": {"footprint": (1, 1), "blocking": False, "source_canvas": (64, 64), "anchor": "center"},
    "thin_prop": {"footprint": (1, 2), "blocking": True, "source_canvas": (64, 96), "anchor": "bottom_center"},
    "npc": {"footprint": (1, 1), "blocking": False, "source_canvas": (64, 64), "anchor": "center"},
    "facade_overlay": {"footprint": (3, 1), "blocking": False, "source_canvas": (96, 64), "anchor": "center"},
    "text_sign": {"footprint": (2, 1), "blocking": False, "source_canvas": (96, 64), "anchor": "center"},
}

FACING_VALUES = {"east_west", "north_south", "faces_south", "faces_player"}
ATTACHED_CATEGORIES = {"facade_overlay", "text_sign"}
OBJECT_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
FOOTPRINT_RE = re.compile(r"^([1-9][0-9]*)x([1-9][0-9]*)$")

STAGES = (
    "1_spec",
    "2_map",
    "3_style",
    "4_entities",
    "5_prompts",
    "6_images",
    "7_pack",
    "8_status",
)

