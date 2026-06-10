from __future__ import annotations

from pathlib import Path

from .contracts import scene_paths
from .progress import load_progress


def scene_status_text(scene_dir: str | Path) -> str:
    paths = scene_paths(scene_dir)
    progress = load_progress(paths.root)
    lines = [
        f"Scene: {paths.root.name}",
        f"Current Stage: {progress.get('current_stage') or '-'}",
        "",
        "Completed:",
    ]
    completed = progress.get("completed") or []
    if completed:
        lines.extend(f"  - {item}" for item in completed)
    else:
        lines.append("  - none")
    in_progress = progress.get("in_progress")
    if in_progress:
        lines.extend(["", "In Progress:", f"  - {in_progress.get('stage')} ({in_progress.get('current_item') or '-'})"])
    errors = progress.get("errors") or []
    if errors:
        lines.append("")
        lines.append("Errors:")
        for error in errors:
            target = f"{error.get('item')}: " if error.get("item") else ""
            lines.append(f"  - {target}{error.get('message')}")
    return "\n".join(lines)

