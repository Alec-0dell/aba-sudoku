"""Compatibility entrypoint for running the FastAPI app.

Use:
    uvicorn backend.main:app --reload
"""

from backend.app.main import app

__all__ = ["app"]

