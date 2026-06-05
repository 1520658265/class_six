from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_asset_catalog(catalog_id: str = "default_rpg_32") -> dict[str, Any]:
    path = Path(__file__).with_name(f"{catalog_id}.json")
    if not path.exists():
        raise FileNotFoundError(f"Unknown asset catalog: {catalog_id}")
    return json.loads(path.read_text(encoding="utf-8"))

