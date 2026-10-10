"""Typed, zero-dependency get/set/delete/has on nested dicts and lists by dotted path."""

from __future__ import annotations

from ._core import delete, get, has, set

__version__ = "0.1.0"

__all__ = ["delete", "get", "has", "set"]
