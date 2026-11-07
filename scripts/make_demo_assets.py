"""Regenerate demo_assets/ (dates relative to today). The API also does this automatically once per day.
Usage: backend/.venv/bin/python scripts/make_demo_assets.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.demo_content import generate  # noqa: E402

out = generate()
print("wrote", ", ".join(sorted(p.name for p in out.iterdir())))
