from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
TOOLS_AI = REPO / "tools" / "ai"
if str(TOOLS_AI) not in sys.path:
    sys.path.insert(0, str(TOOLS_AI))

from pixellab_v2_client import PixelLabV2Client, PixelLabV2Error, format_balance  # noqa: E402


def load_cases() -> dict:
    return json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-api", action="store_true", help="Actually call PixelLab create_tileset and spend quota")
    parser.add_argument("--case", action="append", default=[], help="Run only selected case_id; repeatable")
    parser.add_argument("--tile-size", type=int, default=None, choices=(16, 32), help="Override source tile size")
    args = parser.parse_args()

    config = load_cases()
    raw_dir = ROOT / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    selected = set(args.case)
    tile_size = args.tile_size or int(config.get("tile_size_source", 32))
    detail = str(config.get("detail", "highly detailed"))

    cases = [case for case in config["cases"] if not selected or case["case_id"] in selected]
    manifest = {
        "status": "pending" if not args.run_api else "running",
        "run_api": args.run_api,
        "tile_size_source": tile_size,
        "tile_size_target": int(config.get("tile_size_target", 64)),
        "upscale": str(config.get("upscale", "nearest_neighbor")),
        "detail": detail,
        "cases": [],
    }

    if not args.run_api:
        for case in cases:
            manifest["cases"].append({
                "case_id": case["case_id"],
                "status": "pending_api",
                "expected_raw_json": f"raw/{case['case_id']}.json",
            })
        (raw_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[pending] API not called. Re-run with --run-api after quota is available.")
        print(f"[pending] manifest: {raw_dir / 'manifest.json'}")
        return 0

    client = PixelLabV2Client(timeout=180)
    try:
        balance = client.get_balance()
        print(f"[balance] {format_balance(balance)}")
    except Exception as exc:
        print(f"[warn] balance check failed: {exc}")

    all_ok = True
    for case in cases:
        case_id = case["case_id"]
        print(f"[tileset] {case_id} tile_size={tile_size}")
        try:
            result = client.create_tileset(
                lower_description=case["lower_description"],
                upper_description=case["upper_description"],
                transition_description=case["transition_description"],
                tile_size=tile_size,
                transition_size=0.5,
                view="high top-down",
                outline="selective outline",
                detail=detail,
            )
        except PixelLabV2Error as exc:
            all_ok = False
            entry = {"case_id": case_id, "status": "failed", "error": str(exc)}
            print(f"[error] {case_id}: {exc}")
        else:
            out_path = raw_dir / f"{case_id}.json"
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            entry = {
                "case_id": case_id,
                "status": "ok",
                "raw_json": str(out_path.relative_to(ROOT)),
                "response_keys": sorted(result.keys()) if isinstance(result, dict) else [],
            }
            print(f"[ok] -> {out_path}")
        manifest["cases"].append(entry)

    manifest["status"] = "ok" if all_ok else "partial_failed"
    (raw_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
