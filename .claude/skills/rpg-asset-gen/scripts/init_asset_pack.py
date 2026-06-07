"""Initialize an RPG asset pack directory.

Usage:
    python init_asset_pack.py <output_dir> --type character --style q_chibi --name hero01
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    parser.add_argument("--type", required=True)
    parser.add_argument("--style", default="")
    parser.add_argument("--name", default="")
    args = parser.parse_args()

    root = Path(args.output_dir)
    for rel in ("inputs", "references", "prompts", "raw", "raw/rejected", "final", "qa"):
        (root / rel).mkdir(parents=True, exist_ok=True)

    manifest = {
        "schema": "rpg-asset-gen.v1",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "type": args.type,
        "style": args.style,
        "name": args.name,
        "status": "draft",
        "references": [],
        "outputs": [],
        "qa": {
            "status": "not_run",
            "report": "qa/report.json",
        },
    }
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(root.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
