from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import load_json, save_json, scene_paths


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_progress(scene_dir: str | Path) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    data = load_json(paths.progress, default=None)
    if isinstance(data, dict):
        return data
    return {
        "current_stage": "",
        "completed": [],
        "in_progress": None,
        "last_updated": utc_now(),
        "errors": [],
    }


def save_progress(scene_dir: str | Path, progress: dict[str, Any]) -> dict[str, Any]:
    progress["last_updated"] = utc_now()
    save_json(scene_paths(scene_dir).progress, progress)
    return progress


def mark_in_progress(scene_dir: str | Path, stage: str, total: int | None = None, current_item: str | None = None) -> dict[str, Any]:
    progress = load_progress(scene_dir)
    progress["current_stage"] = stage
    progress["errors"] = [item for item in progress.get("errors", []) if item.get("stage") != stage]
    progress["in_progress"] = {
        "stage": stage,
        "total": total,
        "completed": 0,
        "failed": 0,
        "current_item": current_item,
    }
    return save_progress(scene_dir, progress)


def mark_completed(scene_dir: str | Path, stage: str) -> dict[str, Any]:
    progress = load_progress(scene_dir)
    completed = list(progress.get("completed") or [])
    if stage not in completed:
        completed.append(stage)
    progress["completed"] = completed
    progress["current_stage"] = stage
    progress["in_progress"] = None
    progress.pop("current_item", None)
    return save_progress(scene_dir, progress)


def record_error(scene_dir: str | Path, stage: str, item: str | None, message: str) -> dict[str, Any]:
    paths = scene_paths(scene_dir)
    progress = load_progress(scene_dir)
    entry = {
        "stage": stage,
        "item": item,
        "message": message,
        "timestamp": utc_now(),
    }
    errors = list(progress.get("errors") or [])
    errors.append(entry)
    progress["errors"] = errors
    paths.error_log.parent.mkdir(parents=True, exist_ok=True)
    with paths.error_log.open("a", encoding="utf-8") as f:
        target = f" {item}" if item else ""
        f.write(f"[{entry['timestamp']}] {stage}{target}: {message}\n")
    return save_progress(scene_dir, progress)
