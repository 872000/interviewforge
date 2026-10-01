"""Timed mock-interview session runner."""

from __future__ import annotations

import select
import sys
import time

from .bank import Question
from .scoring import evaluate

DIFFICULTY_EMOJI = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}


def input_with_timeout(prompt: str, timeout_s: float) -> tuple[str, bool]:
    """Read a line of input with a hard deadline.

    Returns (text, timed_out). On POSIX systems the deadline is enforced while
    the user types; on other platforms we fall back to plain input().
    """
    print(prompt, end="", flush=True)
    if not hasattr(select, "select") or not sys.stdin.isatty():
        try:
            return input(), False
        except EOFError:
            return "", False
    deadline = time.monotonic() + timeout_s
    buf: list[str] = []
    timed_out = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        ready, _, _ = select.select([sys.stdin], [], [], min(remaining, 0.2))
        if ready:
            chunk = sys.stdin.readline()
            if not chunk:  # EOF
                break
            buf.append(chunk)
            if chunk.endswith("\n"):
                break
    if timed_out:
        print("\n⏰  Time's up! Moving on…")
    return "".join(buf).strip(), timed_out


def ask_question(q: Question, number: int, total: int, time_scale: float = 1.0) -> dict:
    """Ask one question with a countdown; evaluate and return the result dict."""
    limit = max(5, int(q.time_limit_s * time_scale))
    emoji = DIFFICULTY_EMOJI.get(q.difficulty, "⚪")
    print(f"\n{'─' * 64}")
    print(f"Question {number}/{total}  {emoji} {q.difficulty.upper()} · {q.topic}")
    print(f"⏱  You have {limit} seconds. Type 'skip' to skip.\n")
    print(f"  {q.question}\n")

    start = time.monotonic()
    answer, timed_out = input_with_timeout("Your answer: ", limit)
    elapsed = time.monotonic() - start

    if answer.strip().lower() == "skip":
        print("Skipped.")
        answer, timed_out = "", False

    result = evaluate(answer, q.key_points, timed_out=timed_out)
    print(f"\n  Score: {result.score}/100 ({result.grade})  ·  "
          f"key points {len(result.covered_points)}/{len(q.key_points)}  ·  "
          f"{result.word_count} words in {elapsed:.0f}s")
    for tip in result.feedback:
        print(f"    → {tip}")
    return {
        "question": q,
        "answer_text": answer,
        "score": result.score,
        "time_used_s": round(elapsed, 1),
        "timed_out": timed_out,
        "key_points_covered": len(result.covered_points),
        "key_points_total": len(q.key_points),
    }
