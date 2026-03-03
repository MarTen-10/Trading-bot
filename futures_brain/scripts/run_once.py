#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain.runner import run_once


if __name__ == "__main__":
    print(run_once())
