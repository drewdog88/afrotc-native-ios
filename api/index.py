"""Vercel serverless entrypoint for the FastAPI backend.

Vercel's `@vercel/python` runtime detects the module-level ASGI ``app`` and
serves it. The backend package lives in ``../backend``, so we prepend it to
``sys.path`` before importing. ``vercel.json`` rewrites ``/api/*`` here; the
ASGI app receives the original request path (its router is mounted at
``/api/v1``), so routing works unchanged.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app  # noqa: E402

__all__ = ["app"]
