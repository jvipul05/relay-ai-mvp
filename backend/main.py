"""Compatibility entrypoint for existing command: uvicorn main:app --reload."""
from app.main import app

__all__ = ["app"]
