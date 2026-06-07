from __future__ import annotations

from typing import Any

from pydantic import Field

from ..config import VERSION
from .base import StrictModel


class ValidationIssue(StrictModel):
    code: str
    severity: str = "error"
    message: str
    position: list[int] | None = None
    target: str | None = None


class ValidationReport(StrictModel):
    passed: bool
    errors: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[ValidationIssue] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class GenerationReport(StrictModel):
    version: str = VERSION
    prompt: str
    seed: int
    theme: str
    map_size: list[int]
    tile_size: list[int]
    tileset_id: str
    elapsed_ms: int
    output_files: list[str]
    validation_passed: bool
    retries: list[dict[str, Any]] = Field(default_factory=list)
