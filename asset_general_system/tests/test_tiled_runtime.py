from generator.export import find_tiled, find_tmxrasterizer
from generator.export.tiled_runtime import verify_tiled_maps
import generator.export.tiled_runtime as tiled_runtime


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


def test_find_tiled_checks_known_install_dirs(monkeypatch, tmp_path):
    install_dir = tmp_path / "Tiled"
    install_dir.mkdir()
    tiled = install_dir / "tiled.exe"
    tiled.write_text("", encoding="utf-8")

    monkeypatch.setattr(tiled_runtime, "TILED_INSTALL_DIRS", (install_dir,))
    monkeypatch.setattr(tiled_runtime, "_find_on_path", lambda commands=tiled_runtime.TILED_COMMANDS: None)
    monkeypatch.setattr(tiled_runtime, "_version", lambda executable: "Tiled test")

    status = find_tiled()

    assert status.available is True
    assert status.executable == str(tiled)
    assert status.version == "Tiled test"


def test_find_tmxrasterizer_checks_known_install_dirs(monkeypatch, tmp_path):
    install_dir = tmp_path / "Tiled"
    install_dir.mkdir()
    rasterizer = install_dir / "tmxrasterizer.exe"
    rasterizer.write_text("", encoding="utf-8")

    monkeypatch.setattr(tiled_runtime, "TILED_INSTALL_DIRS", (install_dir,))
    monkeypatch.setattr(tiled_runtime, "_find_on_path", lambda commands=tiled_runtime.TMXRASTERIZER_COMMANDS: None)
    monkeypatch.setattr(tiled_runtime, "_version", lambda executable: "TmxRasterizer test")

    status = find_tmxrasterizer()

    assert status.available is True
    assert status.executable == str(rasterizer)
    assert status.version == "TmxRasterizer test"
