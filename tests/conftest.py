"""Pytest path setup.

The project is not packaged as an installable distribution, so we add the
repository root plus the ``scripts`` and ``kage_studio_hub`` directories to
``sys.path`` to allow importing the modules under test by their bare names.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for _candidate in (ROOT, ROOT / "scripts", ROOT / "kage_studio_hub"):
    _p = str(_candidate)
    if _p not in sys.path:
        sys.path.insert(0, _p)
