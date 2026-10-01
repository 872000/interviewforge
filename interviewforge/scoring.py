"""Heuristic answer evaluation.

No external APIs, no network, no models — the answer is scored against the
question's model-answer key points with a transparent rubric:

* 70% — key-concept coverage: fraction of key points mentioned
* 15% — length sanity: too short is penalized, reasonable length is rewarded
* 15% — structure signals: explanations, examples, sequencing words
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

STOPWORDS = frozenset(
    """
    a an the and or but of to in on for with as by at from is are was were be been
    being it its this that these those i you he she we they them his her our your
    their my me him us do does did done have has had having will would can could
    should shall may might must not no yes so such than then there here when where
    which who whom what how why if else because while during about into over under
    between through each other more most very just also only own same any all both
    """.split()
)

# Words/phrases that signal a structured, reasoned answer.
STRUCTURE_SIGNALS = (
    "because",
    "therefore",
    "however",
    "for example",
    "e.g.",
    "for instance",
    "first",
    "then",
    "finally",
    "in contrast",
    "compared to",
    "trade-off",
    "tradeoff",
    "step 1",
    "1.",
    "2.",
    "- ",
    "* ",
    "in other words",
    "specifically",
)

_WORD_RE = re.compile(r"[a-z0-9]+")

# Longest-first so e.g. "insertion" stems to "insert" like "inserting" does.
_STEM_SUFFIXES = ("ization", "sion", "ion", "ing", "ied", "ies", "ed", "es", "s", "ly")


def stem(word: str) -> str:
    """Tiny stemmer — consistency between the two compared sides matters more
    than linguistic perfection."""
    changed = True
    while changed:
        changed = False
        for suffix in _STEM_SUFFIXES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                changed = True
                break
    return word


def tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def normalize(text: str) -> str:
    return " ".join(tokenize(text))


def phrase_covered(phrase: str, answer_text: str, answer_tokens: set[str]) -> bool:
    """A key point counts as covered if its normalized form appears verbatim,
    or if at least half of its significant (stemmed) words appear in the answer."""
    norm_phrase = normalize(phrase)
    if norm_phrase and norm_phrase in normalize(answer_text):
        return True
    stemmed_answer = {stem(w) for w in answer_tokens}
    words = [stem(w) for w in tokenize(phrase) if w not in STOPWORDS and len(w) > 1]
    if not words:
        return False
    hits = sum(1 for w in words if w in stemmed_answer)
    return hits >= max(1, math.ceil(0.5 * len(words)))


def length_score(word_count: int) -> float:
    """0..1 — penalizes one-liners, rewards substantive answers, caps rambling."""
    if word_count < 10:
        return 0.0
    if word_count < 30:
        return (word_count - 10) / 20 * 0.7  # 0.0 -> 0.7
    if word_count <= 220:
        return 1.0
    # gentle decay for very long answers
    return max(0.6, 1.0 - (word_count - 220) / 400)


def structure_score(answer_text: str) -> float:
    lowered = answer_text.lower()
    found = sum(1 for sig in STRUCTURE_SIGNALS if sig in lowered)
    return min(1.0, found / 3)


def grade_for(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


@dataclass
class Evaluation:
    score: int
    grade: str
    coverage: float
    covered_points: list[str] = field(default_factory=list)
    missing_points: list[str] = field(default_factory=list)
    word_count: int = 0
    timed_out: bool = False
    feedback: list[str] = field(default_factory=list)


def evaluate(answer: str, key_points: list[str], timed_out: bool = False) -> Evaluation:
    """Score an answer against model-answer key points. Returns 0..100."""
    answer = (answer or "").strip()
    tokens = set(tokenize(answer))
    word_count = len(tokenize(answer))

    covered, missing = [], []
    for point in key_points:
        (covered if phrase_covered(point, answer, tokens) else missing).append(point)

    coverage = len(covered) / len(key_points) if key_points else 0.0
    raw = 0.70 * coverage + 0.15 * length_score(word_count) + 0.15 * structure_score(answer)
    score = int(round(100 * raw))
    if timed_out and score > 0:
        score = max(0, score - 5)  # small penalty for running out of time

    feedback: list[str] = []
    if not answer:
        feedback.append("No answer given — even a partial answer scores points.")
    elif word_count < 15:
        feedback.append(f"Only {word_count} words — aim for a fuller explanation (30+ words).")
    for point in missing[:3]:
        feedback.append(f"Consider mentioning: {point}.")
    if coverage >= 0.8 and word_count >= 30:
        feedback.append("Strong coverage of the key concepts — nice work.")
    if timed_out:
        feedback.append("You ran out of time — practice giving the headline answer first.")

    return Evaluation(
        score=score,
        grade=grade_for(score),
        coverage=round(coverage, 2),
        covered_points=covered,
        missing_points=missing,
        word_count=word_count,
        timed_out=timed_out,
        feedback=feedback,
    )
