from __future__ import annotations

import os
import tempfile
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

TMP_ROOT = PROJECT_ROOT / ".pytest_tmp"
TMP_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("TMPDIR", str(TMP_ROOT))
os.environ.setdefault("TEMP", str(TMP_ROOT))
os.environ.setdefault("TMP", str(TMP_ROOT))
tempfile.tempdir = str(TMP_ROOT)

_OriginalTemporaryDirectory = tempfile.TemporaryDirectory


class _PermissionTolerantTemporaryDirectory(_OriginalTemporaryDirectory):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("dir", str(TMP_ROOT))
        kwargs.setdefault("ignore_cleanup_errors", True)
        super().__init__(*args, **kwargs)


tempfile.TemporaryDirectory = _PermissionTolerantTemporaryDirectory
