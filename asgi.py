"""Vercel entrypoint for the `api` service (see vercel.json): `asgi:app`.

Puts `src/` on the import path so the app loads whether or not the build installed the package.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tenderlens.api import app

__all__ = ["app"]
