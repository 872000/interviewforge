"""Bundled scripted demo: runs a full mock interview end-to-end with no input.

The demo answers are deliberately mixed quality (strong, partial, weak) so the
report shows interesting scoring, topic breakdowns and weak-spot analysis.
"""

from __future__ import annotations

import time

from .bank import load_bank, pick_questions
from .report import generate_report
from .scoring import evaluate
from .store import Store
from .terminal import bottom, row, top

# (question_id, scripted answer, simulated seconds used, timed_out)
DEMO_ANSWERS: dict[str, tuple[str, float, bool]] = {
    "dsa-002": (
        "A hash map uses a hash function to map each key to a bucket index, which gives "
        "average O(1) lookups. Collisions happen when two keys hash to the same bucket and are "
        "resolved with chaining, where each bucket holds a linked list, or open addressing. "
        "When the load factor gets too high the table resizes and rehashes everything. "
        "In the worst case with many collisions lookups degrade to O(n).",
        74.0,
        False,
    ),
    "java-003": (
        "Streams let you process collections. You can filter and map things. "
        "They are useful for data processing pipelines.",
        41.0,
        False,
    ),
    "react-001": (
        "idk",
        12.0,
        False,
    ),
    "beh-003": (
        "At my last internship our checkout page started throwing 500 errors for some users. "
        "First I reproduced it with a specific test account, then I checked the logs and used the "
        "debugger to trace it to a race condition where two requests updated the same cart row. "
        "I fixed it by adding a database transaction with row-level locking, then verified with "
        "load tests and added a regression test. Afterward I documented the pattern so the team "
        "would avoid it. I learned to always reproduce first and to think about concurrency early.",
        150.0,
        True,  # ran out of time mid-answer — shows the timeout path
    ),
}

DEMO_QUESTION_IDS = ["dsa-002", "java-003", "react-001", "beh-003"]


def run_demo(db_path=None, out_dir: str = "reports", verbose: bool = True) -> tuple[int, str]:
    """Run the scripted demo interview. Returns (session_id, terminal_report)."""
    questions = {q.id: q for q in load_bank()}
    picked = [questions[qid] for qid in DEMO_QUESTION_IDS]
    # sprinkle in one more deterministic pick so the demo isn't fully hard-coded
    extra = [q for q in pick_questions(list(questions.values()), 1, seed=42)
             if q.id not in DEMO_QUESTION_IDS][:1]
    picked = picked + extra

    store = Store(db_path)
    session_id = store.create_session(topic_filter="demo", difficulty_filter="mixed")

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    log(top())
    log(row("  INTERVIEWFORGE — scripted demo interview"))
    log(bottom())

    t0 = time.monotonic()
    for i, q in enumerate(picked, 1):
        answer, used, timed_out = DEMO_ANSWERS.get(q.id, ("", 5.0, False))
        if q.id not in DEMO_ANSWERS:
            answer = ("A solid answer would cover: " + "; ".join(q.key_points[:2]) + ".")
            used, timed_out = 30.0, False
        result = evaluate(answer, q.key_points, timed_out=timed_out)
        store.record_answer(
            session_id, q.id, q.topic, q.difficulty, answer, result.score,
            used, timed_out, len(result.covered_points), len(q.key_points),
        )
        log(f"\n── Question {i}/{len(picked)} [{q.topic}/{q.difficulty}] ──")
        log(f"   {q.question}")
        log(f"   → score {result.score}/100 ({result.grade}), "
            f"{len(result.covered_points)}/{len(q.key_points)} key points"
            + (" [timeout]" if timed_out else ""))
    store.finalize_session(session_id, time.monotonic() - t0)

    terminal, path = generate_report(store, session_id, out_dir=out_dir)
    store.close()
    if verbose:
        print("\n" + terminal)
        print(f"\n📄 Report saved to {path}")
    return session_id, terminal
