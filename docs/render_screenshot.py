"""Render a real `interviewforge demo` run as a terminal-style PNG screenshot.

The image content is the verbatim stdout of the program — no mock text.
Run:  python3 docs/render_screenshot.py   (from the project root)
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "docs" / "screenshot.png"

BG = "#0d1117"
FG = "#e6edf3"
DIM = "#8b949e"
CYAN = "#39c5cf"
AMBER = "#f0b429"
GREEN = "#3fb950"
RED = "#f85149"
YELLOW = "#d29922"


def capture_demo_output() -> list[str]:
    tmp = tempfile.mkdtemp(prefix="if-screenshot-")
    proc = subprocess.run(
        [sys.executable, "-m", "interviewforge", "demo", "--out-dir", tmp],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"demo failed:\n{proc.stderr}")
    lines = proc.stdout.splitlines()
    # Trim the trailing "Report saved" line (machine-specific tmp path); keep the rest verbatim.
    lines = [ln for ln in lines if not ln.startswith("📄")]
    return lines


def color_for(line: str) -> str:
    if "INTERVIEWFORGE" in line:
        return CYAN
    if line.startswith("── Question"):
        return AMBER
    if "WEAK-SPOT" in line:
        return RED
    if re.match(r"^\s*║\s+!\s", line):
        return YELLOW
    if re.search(r"→ score (\d+)", line):
        score = int(re.search(r"→ score (\d+)", line).group(1))
        return GREEN if score >= 70 else (YELLOW if score >= 40 else RED)
    if re.search(r"\d+/100", line) and ("█" in line or "░" in line):
        m = re.search(r"(\d+)/100", line)
        score = int(m.group(1))
        return GREEN if score >= 70 else (YELLOW if score >= 40 else RED)
    if set(line.strip()) <= set("+-| "):
        return DIM
    return FG


def sanitize(line: str) -> str:
    """Transliterate box-drawing glyphs to ASCII for pixel-perfect monospace
    alignment in the PNG (DejaVu Sans Mono gives box chars a slightly different
    advance than ASCII). Also replace emoji the font lacks.

    The program's real terminal output is untouched; this only affects the PNG.
    """
    table = str.maketrans({
        "╔": "+", "╗": "+", "╚": "+", "╝": "+",
        "╠": "+", "╣": "+", "║": "|",
        "═": "-", "─": "-",
    })
    return line.translate(table).replace("⏰", "[timeout]").replace("⏱", "[timer]").replace("📄", ">")


def main() -> None:
    lines = [sanitize(ln) for ln in capture_demo_output()]
    # Keep the screenshot focused: the question results + full report.
    start = next((i for i, ln in enumerate(lines) if "Question 1/" in ln), 0)
    lines = lines[start:]

    n = len(lines)
    fig_w, lh = 13.5, 0.30
    fig, ax = plt.subplots(figsize=(fig_w, max(4.0, n * lh + 0.9)))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.axis("off")

    # Title bar
    ax.text(
        0.5, 0.965, "● ● ●   parth@dev — interviewforge demo",
        transform=ax.transAxes, ha="center", va="top",
        fontsize=11, color=DIM, family="monospace",
    )

    y = 0.90
    step = 0.86 / max(n, 1)
    for line in lines:
        ax.text(
            0.03, y, line, transform=ax.transAxes, ha="left", va="top",
            fontsize=9.5, color=color_for(line), family="monospace",
        )
        y -= step

    fig.savefig(OUT_PATH, dpi=150, facecolor=BG, bbox_inches="tight", pad_inches=0.4)
    print(f"wrote {OUT_PATH} ({n} lines rendered)")


if __name__ == "__main__":
    main()
