from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models.base import read_json
from .tiled_validator import TiledJsonValidator


TILED_COMMANDS = ("tiled", "tiled.exe", "Tiled", "Tiled.exe")
TMXRASTERIZER_COMMANDS = ("tmxrasterizer", "tmxrasterizer.exe")
TILED_INSTALL_DIRS = (
    Path("D:/Soft/Tiled"),
    Path("C:/Program Files/Tiled"),
    Path("C:/Program Files (x86)/Tiled"),
)


@dataclass(frozen=True)
class TiledRuntimeStatus:
    available: bool
    executable: str | None
    version: str | None
    message: str


@dataclass(frozen=True)
class TiledDemoVerification:
    name: str
    map_path: str
    static_passed: bool
    runtime_status: str
    runtime_message: str
    runtime_output_path: str | None = None


def find_tiled(explicit_path: str | None = None) -> TiledRuntimeStatus:
    executable = explicit_path or _find_on_path() or _find_in_install_dirs(TILED_COMMANDS)
    if not executable:
        return TiledRuntimeStatus(
            available=False,
            executable=None,
            version=None,
            message="Tiled executable was not found. Install Tiled or pass --tiled-path.",
        )

    path = Path(executable)
    if explicit_path and not path.exists():
        return TiledRuntimeStatus(
            available=False,
            executable=explicit_path,
            version=None,
            message=f"Tiled executable does not exist: {explicit_path}",
        )

    version = _version(executable)
    return TiledRuntimeStatus(
        available=True,
        executable=executable,
        version=version,
        message="Tiled executable is available.",
    )


def find_tmxrasterizer(
    tiled_path: str | None = None,
    explicit_path: str | None = None,
) -> TiledRuntimeStatus:
    executable = (
        explicit_path
        or _rasterizer_next_to_tiled(tiled_path)
        or _find_on_path(TMXRASTERIZER_COMMANDS)
        or _find_in_install_dirs(TMXRASTERIZER_COMMANDS)
    )
    if not executable:
        return TiledRuntimeStatus(
            available=False,
            executable=None,
            version=None,
            message="tmxrasterizer executable was not found. Install Tiled or pass --tmxrasterizer-path.",
        )

    path = Path(executable)
    if explicit_path and not path.exists():
        return TiledRuntimeStatus(
            available=False,
            executable=explicit_path,
            version=None,
            message=f"tmxrasterizer executable does not exist: {explicit_path}",
        )

    version = _version(executable)
    return TiledRuntimeStatus(
        available=True,
        executable=executable,
        version=version,
        message="tmxrasterizer executable is available.",
    )


def verify_tiled_maps(
    map_paths: list[Path],
    tiled_path: str | None = None,
    tmxrasterizer_path: str | None = None,
    runtime_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    status = find_tiled(tiled_path)
    rasterizer_status = find_tmxrasterizer(status.executable, tmxrasterizer_path) if status.available else None
    validator = TiledJsonValidator()
    demos: list[TiledDemoVerification] = []

    for map_path in map_paths:
        tiled = read_json(map_path)
        static_report = validator.validate(tiled)
        runtime_output_path = None
        if not status.available:
            runtime_status = "skipped"
            runtime_message = status.message
        elif not static_report.passed:
            runtime_status = "skipped"
            runtime_message = "Static Tiled JSON validation failed, so runtime rasterization was skipped."
        elif rasterizer_status is None or not rasterizer_status.available:
            runtime_status = "skipped"
            runtime_message = rasterizer_status.message if rasterizer_status else "tmxrasterizer was not checked."
        else:
            output_path = _available_runtime_output_path(_runtime_output_path(map_path, runtime_output_dir))
            runtime_passed, runtime_message = _rasterize_map(rasterizer_status.executable, map_path, output_path)
            runtime_status = "passed" if runtime_passed else "failed"
            runtime_output_path = str(output_path) if runtime_passed else None
        demos.append(
            TiledDemoVerification(
                name=map_path.parent.name,
                map_path=str(map_path),
                static_passed=static_report.passed,
                runtime_status=runtime_status,
                runtime_message=runtime_message,
                runtime_output_path=runtime_output_path,
            )
        )

    runtime_statuses = [demo.runtime_status for demo in demos]
    all_runtime_passed = bool(demos) and all(status == "passed" for status in runtime_statuses)
    if not status.available:
        runtime_verification = "skipped_tiled_not_installed"
    elif rasterizer_status is None or not rasterizer_status.available:
        runtime_verification = "skipped_tmxrasterizer_not_found"
    elif all_runtime_passed:
        runtime_verification = "passed_tmxrasterizer"
    elif any(status == "failed" for status in runtime_statuses):
        runtime_verification = "failed_tmxrasterizer"
    elif any(status == "skipped" for status in runtime_statuses):
        runtime_verification = "skipped_runtime"
    else:
        runtime_verification = "not_run"

    return {
        "tiled_available": status.available,
        "tiled_executable": status.executable,
        "tiled_version": status.version,
        "tmxrasterizer_available": bool(rasterizer_status and rasterizer_status.available),
        "tmxrasterizer_executable": rasterizer_status.executable if rasterizer_status else None,
        "tmxrasterizer_version": rasterizer_status.version if rasterizer_status else None,
        "all_static_passed": all(demo.static_passed for demo in demos),
        "all_runtime_passed": all_runtime_passed,
        "runtime_verification": runtime_verification,
        "demos": [demo.__dict__ for demo in demos],
    }


def _find_on_path(commands: tuple[str, ...] = TILED_COMMANDS) -> str | None:
    for command in commands:
        found = shutil.which(command)
        if found:
            return found
    return None


def _find_in_install_dirs(commands: tuple[str, ...] = TILED_COMMANDS) -> str | None:
    for directory in TILED_INSTALL_DIRS:
        for command in commands:
            candidate = directory / command
            if candidate.exists():
                return str(candidate)
    return None


def _rasterizer_next_to_tiled(tiled_path: str | None) -> str | None:
    if not tiled_path:
        return None
    tiled = Path(tiled_path)
    if not tiled.exists():
        return None
    for name in ("tmxrasterizer.exe", "tmxrasterizer"):
        candidate = tiled.with_name(name)
        if candidate.exists():
            return str(candidate)
    return None


def _runtime_output_path(map_path: Path, runtime_output_dir: str | Path | None) -> Path:
    base_dir = Path(runtime_output_dir) if runtime_output_dir else Path("tmp") / "tiled_runtime_renders"
    return base_dir / f"{map_path.parent.name}.png"


def _available_runtime_output_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{index:03d}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"No available runtime render output path under {path.parent}.")


def _rasterize_map(rasterizer: str, map_path: Path, output_path: Path) -> tuple[bool, str]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [
                rasterizer,
                "--size",
                "256",
                "--ignore-visibility",
                str(map_path),
                str(output_path),
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return False, "tmxrasterizer timed out after 30 seconds."
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"tmxrasterizer failed to start: {exc}"

    output = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        return False, output or f"tmxrasterizer exited with code {completed.returncode}."
    if not output_path.exists() or output_path.stat().st_size <= 0:
        return False, "tmxrasterizer completed but did not create a non-empty image."
    return True, "tmxrasterizer loaded and rendered the map successfully."


def _version(executable: str) -> str | None:
    try:
        completed = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout or completed.stderr).strip()
    return output or None
