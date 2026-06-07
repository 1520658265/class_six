"""
Asset library with semantic tag-based search.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from generator.models.asset_metadata import AssetMetadata


class AssetLibrary:
    """
    Asset library with tag-based search and synonym support.
    """

    # Synonym mappings for flexible search
    SYNONYMS = {
        "temple": ["temple", "shrine", "sanctuary", "altar"],
        "house": ["house", "building", "hut", "cottage", "dwelling"],
        "tree": ["tree", "oak", "pine", "palm", "willow"],
        "rock": ["rock", "stone", "boulder"],
        "chest": ["chest", "treasure", "box", "container"],
        "stall": ["stall", "shop", "booth", "stand"],
        "water": ["water", "river", "lake", "pond", "ocean", "sea"],
        "path": ["path", "road", "trail", "walkway"],
        "bridge": ["bridge", "crossing"],
        "door": ["door", "entrance", "gate", "portal"],
    }

    def __init__(self, library_dir: Path | None = None):
        """
        Initialize asset library.

        Args:
            library_dir: Directory containing asset metadata JSON files
        """
        self.library_dir = library_dir
        self.assets: dict[str, AssetMetadata] = {}
        if library_dir and library_dir.exists():
            self.load_from_directory(library_dir)

    def load_from_directory(self, directory: Path) -> None:
        """
        Load all asset metadata files from a directory.

        Args:
            directory: Directory to scan for .json files
        """
        for json_file in directory.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    metadata = AssetMetadata.from_dict(data)
                    self.assets[metadata.asset_id] = metadata
            except Exception as e:
                # Skip invalid files
                print(f"Warning: Failed to load {json_file}: {e}")

    def add_asset(self, metadata: AssetMetadata) -> None:
        """
        Add an asset to the library.

        Args:
            metadata: Asset metadata
        """
        self.assets[metadata.asset_id] = metadata

    def get_asset(self, asset_id: str) -> AssetMetadata | None:
        """
        Get asset by ID.

        Args:
            asset_id: Asset identifier

        Returns:
            Asset metadata or None if not found
        """
        return self.assets.get(asset_id)

    def search_by_tags(
        self,
        tags: list[str],
        match_all: bool = False,
        use_synonyms: bool = True,
    ) -> list[AssetMetadata]:
        """
        Search assets by tags.

        Args:
            tags: Tags to search for
            match_all: If True, require all tags; if False, match any tag
            use_synonyms: If True, expand search using synonym mappings

        Returns:
            List of matching assets, sorted by relevance
        """
        # Expand tags with synonyms
        if use_synonyms:
            expanded_tags = set()
            for tag in tags:
                tag_lower = tag.lower()
                expanded_tags.add(tag_lower)
                # Add synonyms
                for key, synonyms in self.SYNONYMS.items():
                    if tag_lower in synonyms:
                        expanded_tags.update(synonyms)
            search_tags = list(expanded_tags)
        else:
            search_tags = [t.lower() for t in tags]

        results = []
        for asset in self.assets.values():
            asset_tags = [t.lower() for t in asset.tags]

            if match_all:
                # All tags must match
                if all(any(st in at for at in asset_tags) for st in search_tags):
                    results.append(asset)
            else:
                # Any tag matches
                if any(any(st in at for at in asset_tags) for st in search_tags):
                    results.append(asset)

        # Sort by relevance (number of matching tags)
        def relevance_score(asset: AssetMetadata) -> int:
            asset_tags = [t.lower() for t in asset.tags]
            return sum(1 for st in search_tags if any(st in at for at in asset_tags))

        results.sort(key=relevance_score, reverse=True)
        return results

    def search_by_theme(
        self,
        themes: list[str],
        match_all: bool = False,
    ) -> list[AssetMetadata]:
        """
        Search assets by theme.

        Args:
            themes: Themes to search for
            match_all: If True, require all themes; if False, match any theme

        Returns:
            List of matching assets
        """
        themes_lower = [t.lower() for t in themes]
        results = []

        for asset in self.assets.values():
            asset_themes = [t.lower() for t in asset.theme]

            if match_all:
                if all(t in asset_themes for t in themes_lower):
                    results.append(asset)
            else:
                if any(t in asset_themes for t in themes_lower):
                    results.append(asset)

        return results

    def search(
        self,
        tags: list[str] | None = None,
        themes: list[str] | None = None,
        kind: str | None = None,
    ) -> list[AssetMetadata]:
        """
        Combined search by tags, themes, and kind.

        Args:
            tags: Tags to match (any)
            themes: Themes to match (any)
            kind: Asset kind to filter

        Returns:
            List of matching assets
        """
        results = list(self.assets.values())

        # Filter by tags
        if tags:
            tag_matches = self.search_by_tags(tags, match_all=False)
            tag_ids = {a.asset_id for a in tag_matches}
            results = [a for a in results if a.asset_id in tag_ids]

        # Filter by themes
        if themes:
            theme_matches = self.search_by_theme(themes, match_all=False)
            theme_ids = {a.asset_id for a in theme_matches}
            results = [a for a in results if a.asset_id in theme_ids]

        # Filter by kind
        if kind:
            results = [a for a in results if a.kind.value == kind]

        return results

    def find_missing_assets(
        self,
        required_tags: list[str],
    ) -> list[str]:
        """
        Find tags that have no matching assets.

        Args:
            required_tags: List of required asset tags

        Returns:
            List of tags with no matching assets
        """
        missing = []
        for tag in required_tags:
            matches = self.search_by_tags([tag], use_synonyms=True)
            if not matches:
                missing.append(tag)
        return missing

    def get_stats(self) -> dict[str, Any]:
        """
        Get library statistics.

        Returns:
            Dictionary with library stats
        """
        total = len(self.assets)
        by_kind: dict[str, int] = {}
        by_theme: dict[str, int] = {}
        all_tags: set[str] = set()

        for asset in self.assets.values():
            # Count by kind
            kind = asset.kind.value
            by_kind[kind] = by_kind.get(kind, 0) + 1

            # Count by theme
            for theme in asset.theme:
                by_theme[theme] = by_theme.get(theme, 0) + 1

            # Collect tags
            all_tags.update(asset.tags)

        return {
            "total_assets": total,
            "by_kind": by_kind,
            "by_theme": by_theme,
            "unique_tags": len(all_tags),
            "all_tags": sorted(all_tags),
        }

    def export_catalog(self, output_path: Path) -> None:
        """
        Export library as asset catalog JSON.

        Args:
            output_path: Path to output catalog file
        """
        catalog = {
            "library_id": "generated_objects",
            "version": "1.0",
            "objects": [asset.to_dict() for asset in self.assets.values()],
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)
