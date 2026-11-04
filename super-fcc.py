#!/usr/bin/env python3
"""Run from a checkout without installing the orchestrator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from super_fcc.cli import main

if __name__ == "__main__":
    main()
