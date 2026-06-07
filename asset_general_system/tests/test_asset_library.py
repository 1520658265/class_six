"""
Test asset library search functionality.
"""

import tempfile
from pathlib import Path

from generator.assets.asset_library import AssetLibrary
from generator.models.asset_metadata import (
    AnchorPoint,
    AssetKind,
    AssetMetadata,
)


def create_test_library() -> AssetLibrary:
    """Create a test library with sample assets."""
    library = AssetLibrary()

    # Add some test assets
    library.add_asset(AssetMetadata(
        asset_id="tree_oak_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["tree", "oak", "forest", "blocking"],
        tile_size=(32, 32),
        theme=["forest", "village"],
        footprint=(1, 2),
    ))

    library.add_asset(AssetMetadata(
        asset_id="tree_pine_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["tree", "pine", "forest", "blocking"],
        tile_size=(32, 32),
        theme=["forest", "snow", "mountains"],
        footprint=(1, 2),
    ))

    library.add_asset(AssetMetadata(
        asset_id="rock_small_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["rock", "stone", "blocking"],
        tile_size=(32, 32),
        theme=["mountains", "desert"],
        footprint=(1, 1),
    ))

    library.add_asset(AssetMetadata(
        asset_id="temple_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["temple", "building", "blocking"],
        tile_size=(32, 32),
        theme=["village", "ruins"],
        footprint=(2, 2),
    ))

    library.add_asset(AssetMetadata(
        asset_id="chest_01",
        kind=AssetKind.TILE_OBJECT,
        tags=["chest", "treasure", "container", "blocking"],
        tile_size=(32, 32),
        theme=["dungeon", "ruins"],
        footprint=(1, 1),
    ))

    return library


def test_search_by_tags():
    """Test tag-based search."""
    library = create_test_library()

    # Search for trees
    results = library.search_by_tags(["tree"])
    assert len(results) == 2
    assert all("tree" in r.tags for r in results)

    # Search for blocking objects
    results = library.search_by_tags(["blocking"])
    assert len(results) == 5  # All test objects are blocking

    # Search with multiple tags (any match)
    results = library.search_by_tags(["tree", "chest"], match_all=False)
    assert len(results) == 3  # 2 trees + 1 chest

    # Search with multiple tags (all match)
    results = library.search_by_tags(["tree", "forest"], match_all=True)
    assert len(results) == 2  # Both trees


def test_search_by_theme():
    """Test theme-based search."""
    library = create_test_library()

    # Search for forest theme
    results = library.search_by_theme(["forest"])
    assert len(results) == 2  # oak and pine

    # Search for village theme
    results = library.search_by_theme(["village"])
    assert len(results) == 2  # oak and temple

    # Search with multiple themes (any)
    results = library.search_by_theme(["snow", "desert"], match_all=False)
    assert len(results) == 2  # pine (snow) and rock (desert)


def test_synonym_search():
    """Test search with synonym expansion."""
    library = create_test_library()

    # Search for "shrine" should find "temple" via synonyms
    results = library.search_by_tags(["shrine"], use_synonyms=True)
    assert len(results) == 1
    assert results[0].asset_id == "temple_01"

    # Search for "boulder" should find "rock" via synonyms
    results = library.search_by_tags(["boulder"], use_synonyms=True)
    assert len(results) == 1
    assert results[0].asset_id == "rock_small_01"

    # Without synonyms, should not find
    results = library.search_by_tags(["shrine"], use_synonyms=False)
    assert len(results) == 0


def test_combined_search():
    """Test combined search by tags, theme, and kind."""
    library = create_test_library()

    # Search for blocking objects in forest theme
    results = library.search(tags=["blocking"], themes=["forest"])
    assert len(results) == 2  # Both trees

    # Search for tile_object kind with chest tag
    results = library.search(tags=["chest"], kind="tile_object")
    assert len(results) == 1
    assert results[0].asset_id == "chest_01"


def test_find_missing_assets():
    """Test missing asset detection."""
    library = create_test_library()

    # These exist
    missing = library.find_missing_assets(["tree", "rock", "chest"])
    assert len(missing) == 0

    # These don't exist
    missing = library.find_missing_assets(["house", "bridge", "lamppost"])
    assert len(missing) == 3
    assert "house" in missing
    assert "bridge" in missing
    assert "lamppost" in missing


def test_library_stats():
    """Test library statistics."""
    library = create_test_library()

    stats = library.get_stats()
    assert stats["total_assets"] == 5
    assert stats["by_kind"]["tile_object"] == 5
    assert "forest" in stats["by_theme"]
    assert stats["by_theme"]["forest"] == 2
    assert stats["unique_tags"] > 0
    assert "tree" in stats["all_tags"]


def test_get_asset():
    """Test direct asset retrieval."""
    library = create_test_library()

    asset = library.get_asset("tree_oak_01")
    assert asset is not None
    assert asset.asset_id == "tree_oak_01"

    asset = library.get_asset("nonexistent")
    assert asset is None


if __name__ == "__main__":
    test_search_by_tags()
    test_search_by_theme()
    test_synonym_search()
    test_combined_search()
    test_find_missing_assets()
    test_library_stats()
    test_get_asset()
    print("All asset library tests passed!")
