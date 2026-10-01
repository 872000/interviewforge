"""Tests for the heuristic scoring engine."""

from interviewforge.scoring import (
    evaluate,
    grade_for,
    length_score,
    phrase_covered,
    structure_score,
)

KEY_POINTS = [
    "arrays use contiguous memory and linked lists use nodes with pointers",
    "arrays give O(1) random access by index",
    "linked lists allow O(1) insertion and deletion",
]

STRONG_ANSWER = (
    "Arrays store elements in contiguous memory, which is why indexing an array is O(1) "
    "random access: the address is just base plus index times element size. Linked lists instead "
    "chain nodes together with pointers, so reaching element k requires traversal, but inserting "
    "or deleting at a known node is O(1) because only pointers are rewired. For example, a dynamic "
    "array gives cache-friendly reads, while a linked list avoids shifting elements on insert. "
    "Therefore I would choose an array for read-heavy workloads and a linked list when I expect "
    "frequent insertions and deletions in the middle."
)


def _tokens(text):
    from interviewforge.scoring import tokenize

    return set(tokenize(text))


def test_strong_answer_scores_high():
    ev = evaluate(STRONG_ANSWER, KEY_POINTS)
    assert ev.score >= 80, ev
    assert ev.grade in ("A", "B")
    assert ev.coverage == 1.0
    assert ev.missing_points == []


def test_empty_answer_scores_zero():
    ev = evaluate("", KEY_POINTS)
    assert ev.score == 0
    assert ev.grade == "F"
    assert ev.coverage == 0.0
    assert len(ev.missing_points) == len(KEY_POINTS)


def test_gibberish_scores_poorly():
    ev = evaluate("banana rocket ship purple elephant", KEY_POINTS)
    assert ev.score < 20
    assert ev.coverage == 0.0


def test_partial_answer_partial_credit():
    ev = evaluate("Arrays use contiguous memory.", KEY_POINTS)
    assert 0 < ev.coverage < 1.0
    assert ev.missing_points  # the uncovered points are named


def test_phrase_covered_verbatim_and_fuzzy():
    toks = _tokens("the hash function maps keys to bucket indices for O(1) lookups")
    assert phrase_covered("a hash function maps keys to bucket indices", "x", toks)
    assert not phrase_covered("completely unrelated concept about databases", "x", toks)


def test_length_score_shape():
    assert length_score(3) == 0.0
    assert length_score(100) == 1.0
    assert 0.0 < length_score(20) < 1.0
    assert length_score(10_000) < 1.0  # rambling is capped


def test_structure_score_detects_signals():
    assert structure_score("First I did X. Then Y. For example Z.") > structure_score("I did X Y Z.")
    assert structure_score("") == 0.0


def test_timeout_penalty_applies():
    normal = evaluate(STRONG_ANSWER, KEY_POINTS)
    late = evaluate(STRONG_ANSWER, KEY_POINTS, timed_out=True)
    assert late.score == normal.score - 5
    assert late.timed_out
    assert any("time" in f.lower() for f in late.feedback)


def test_grade_boundaries():
    assert grade_for(95) == "A"
    assert grade_for(75) == "B"
    assert grade_for(60) == "C"
    assert grade_for(45) == "D"
    assert grade_for(10) == "F"


def test_feedback_names_missing_points():
    ev = evaluate("nothing relevant here at all", KEY_POINTS)
    joined = " ".join(ev.feedback)
    assert "Consider mentioning" in joined
