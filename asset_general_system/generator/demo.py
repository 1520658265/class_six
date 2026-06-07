from __future__ import annotations

from pathlib import Path

from .cli import generate_command
from .demo_cases import DEMO_CASES


class _Args:
    def __init__(self, prompt_file: str, output: str, seed: int) -> None:
        self.prompt = None
        self.prompt_file = prompt_file
        self.theme = None
        self.size = "64x64"
        self.seed = seed
        self.tileset = "default_rpg_32"
        self.output = output
        self.debug_preview = True


def main() -> None:
    root = Path.cwd()
    for name, prompt_file, seed in DEMO_CASES:
        generate_command(_Args(str(root / prompt_file), str(root / "examples" / "outputs" / name), seed))


if __name__ == "__main__":
    main()
