# Phase 2 Tiled Runtime Verification

Updated: 2026-06-05

## Local Installation

Tiled is installed at:

```text
D:\Soft\Tiled\tiled.exe
```

The installation also includes:

```text
D:\Soft\Tiled\tmxrasterizer.exe
```

`tmxrasterizer.exe` is used for automated runtime verification because it can load a Tiled map and render it to an image without launching the GUI editor.

## Verification Commands

Check local Tiled tools:

```bash
python -m generator.cli check-tiled --tiled-path "D:\Soft\Tiled\tiled.exe"
```

Verify standard demo exports:

```bash
python -m generator.cli verify-tiled-demos --outputs examples\outputs --tiled-path "D:\Soft\Tiled\tiled.exe" --output examples\outputs\tiled_demo_verification.json
```

## Latest Result

The standard five demo maps passed both static JSON validation and runtime Tiled toolchain loading/rendering.

```text
tiled_available=True
tmxrasterizer_available=True
tmxrasterizer_version=TmxRasterizer 1.0
all_static_passed=True
all_runtime_passed=True
runtime_verification=passed_tmxrasterizer
```

Runtime render outputs are written under:

```text
tmp\tiled_runtime_renders\
```

The `tmp/` directory is ignored by git.

## Scope

This verification proves that the exported `map.tiled.json` files can be loaded and rendered by the installed Tiled command-line toolchain. Manual GUI inspection can still be useful for visual review, but it is no longer blocking Phase 2 acceptance.
