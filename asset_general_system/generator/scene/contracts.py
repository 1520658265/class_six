from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from generator.models.base import read_json, write_json


@dataclass(frozen=True)
class ScenePaths:
    root: Path

    @property
    def scene_md(self) -> Path:
        return self.root / "scene.md"

    @property
    def map_spec(self) -> Path:
        return self.root / "map_spec.json"

    @property
    def map_data(self) -> Path:
        return self.root / "map_data.json"

    @property
    def art_request(self) -> Path:
        return self.root / "art_request.json"

    @property
    def preview(self) -> Path:
        return self.root / "preview.png"

    @property
    def concept_dir(self) -> Path:
        return self.root / "concept"

    @property
    def concept_prompt(self) -> Path:
        return self.concept_dir / "background_concept_prompt.txt"

    @property
    def concept_image(self) -> Path:
        return self.concept_dir / "background_concept.png"

    @property
    def background_plan(self) -> Path:
        return self.root / "background_plan.json"

    @property
    def background_review(self) -> Path:
        return self.root / "background_review.html"

    @property
    def background_tiles_dir(self) -> Path:
        return self.root / "background_tiles"

    @property
    def tilemap_blueprint(self) -> Path:
        return self.root / "tilemap_blueprint.json"

    @property
    def tile_family_plan(self) -> Path:
        return self.root / "tile_family_plan.json"

    @property
    def pixellab_tilesets_dir(self) -> Path:
        return self.root / "pixellab_tilesets"

    @property
    def tile_candidates_dir(self) -> Path:
        return self.root / "tile_candidates"

    @property
    def tile_candidates(self) -> Path:
        return self.root / "tile_candidates.json"

    @property
    def tilemap_mapping(self) -> Path:
        return self.root / "tilemap_mapping.json"

    @property
    def tiled_dir(self) -> Path:
        return self.root / "tiled"

    @property
    def style_profile(self) -> Path:
        return self.root / "style_profile.json"

    @property
    def entities(self) -> Path:
        return self.root / "entities.json"

    @property
    def prompts(self) -> Path:
        return self.root / "prompts.json"

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def manifest(self) -> Path:
        return self.root / "art_manifest.json"

    @property
    def progress(self) -> Path:
        return self.root / "progress.json"

    @property
    def error_log(self) -> Path:
        return self.root / "error.log"

    @property
    def final_dir(self) -> Path:
        return self.root / "final"


def scene_paths(scene_dir: str | Path) -> ScenePaths:
    return ScenePaths(Path(scene_dir))


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return read_json(path)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, data)
