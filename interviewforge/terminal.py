"""Tiny terminal-drawing helpers: fixed-width box rows."""

from __future__ import annotations

INNER_WIDTH = 62


def row(text: str = "", width: int = INNER_WIDTH) -> str:
    """A `║ text ║` row, padded/truncated so the box never breaks."""
    return "║" + text[:width].ljust(width) + "║"


def top(width: int = INNER_WIDTH) -> str:
    return "╔" + "═" * width + "╗"


def divider(width: int = INNER_WIDTH) -> str:
    return "╠" + "═" * width + "╣"


def bottom(width: int = INNER_WIDTH) -> str:
    return "╚" + "═" * width + "╝"
