from generator.export import find_tiled, find_tmxrasterizer
from generator.export.tiled_runtime import verify_tiled_maps


def test_find_tiled_reports_missing_explicit_path():
    status = find_tiled("Z:/definitely/not/installed/Tiled.exe")

    assert status.available is False
    assert status.executable == "Z:/definitely/not/installed/Tiled.exe"
    assert status.version is None
    assert "does not exist" in status.message


def test_verify_tiled_maps_skips_runtime_when_tiled_missing():
    result = verify_tiled_maps([], "Z:/definitely/not/installed/Tiled.exe")

    assert result["tiled_available"] is False
    assert result["all_static_passed"] is True
    assert result["runtime_verification"] == "skipped_tiled_not_installed"
    assert result["demos"] == []


def test_find_tmxrasterizer_reports_missing_explicit_path():
    status = find_tmxrasterizer(explicit_path="Z:/definitely/not/installed/tmxrasterizer.exe")

    assert status.available is False
    assert status.executable == "Z:/definitely/not/installed/tmxrasterizer.exe"
    assert status.version is None
    assert "does not exist" in status.message
