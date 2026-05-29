"""Load local AI service configuration.

Real credentials belong in tools/ai/config.local.json, which is ignored by git.
Use tools/ai/config.example.json as the shape reference.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


CONFIG_ENV = "CLASS_SIX_AI_CONFIG"
DEFAULT_CONFIG_PATH = Path(__file__).resolve().with_name("config.local.json")


def _config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    return Path(override).expanduser() if override else DEFAULT_CONFIG_PATH


def _load_config() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"Config root must be a JSON object: {path}")
    return data


def get_service_config(
    service_name: str,
    *,
    env_prefix: str,
    default_host: str,
    default_model: str,
) -> dict[str, str]:
    """Return api_host/api_key/model for a configured service."""

    data = _load_config()
    services = data.get("services", {})
    if services is None:
        services = {}
    if not isinstance(services, dict):
        raise RuntimeError("Config field 'services' must be a JSON object")

    service = services.get(service_name, {})
    if service is None:
        service = {}
    if not isinstance(service, dict):
        raise RuntimeError(f"Config service '{service_name}' must be a JSON object")

    api_host = (
        os.environ.get(f"{env_prefix}_API_HOST")
        or service.get("api_host")
        or default_host
    )
    api_key = os.environ.get(f"{env_prefix}_API_KEY") or service.get("api_key") or ""
    model = os.environ.get(f"{env_prefix}_MODEL") or service.get("model") or default_model

    if not api_key or api_key.startswith("put-"):
        path = _config_path()
        raise RuntimeError(
            f"Missing API key for '{service_name}'. Create {path} from "
            f"tools/ai/config.example.json, or set {env_prefix}_API_KEY."
        )

    return {
        "api_host": str(api_host),
        "api_key": str(api_key),
        "model": str(model),
    }
