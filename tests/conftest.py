"""Shared test fixtures."""

import sys
from pathlib import Path

# Add src directories to path
src_dirs = [
    Path(__file__).parent.parent / "lazy_core" / "src",
    Path(__file__).parent.parent / "lazy_pool" / "src",
    Path(__file__).parent.parent / "lazy_gate" / "src",
    Path(__file__).parent.parent / "lazy_master" / "src",
    Path(__file__).parent.parent / "lazy_view" / "src",
]

for src_dir in src_dirs:
    if src_dir.exists() and str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
