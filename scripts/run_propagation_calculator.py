#!/usr/bin/env python
"""Propagation calculator - Run ITU-R P.1812-6 propagation analysis on terrain profiles."""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from propagation import batch_process


if __name__ == "__main__":
    print("Starting MST-GIS Propagation Calculator")
    print("=" * 50)
    batch_process()
    print("=" * 50)
    print("✅ Propagation calculations complete")
