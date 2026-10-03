"""InterviewForge CLI.

Usage:
    python -m interviewforge interview [--topic TOPIC] [--difficulty LEVEL] [-n N]
    python -m interviewforge demo
    python -m interviewforge history
    python -m interviewforge stats
    python -m interviewforge report SESSION_ID
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

from . import __version__
from .bank import filter_questions, load_bank, pick_questions, topics
from .demo import run_demo
from .report import generate_report, score_bar
from .session import ask_question
from .store import Store
from .terminal import bottom, row, top


def cmd_interview(args: argparse.Namespace) -> int:
    questions = load_bank()
    pool = filter_questions(questions, topic=args.topic, difficulty=args.difficulty)
    if not pool:
        print("No questions match that topic/difficulty. Available topics:")
        for t in topics(questions):
            print(f"  - {t}")
        return 1
    picked = pick_questions(pool, args.num, seed=args.seed)
    if args.num > len(picked):
        print(f"  Note: only {len(picked)} matching question(s) available "
              f"— running all of them.")
    if args.list_only:
        for q in picked:
            print(f"[{q.id}] ({q.topic}/{q.difficulty}) {q.question}")
        return 0

    store = Store()
    session_id = store.create_session(topic_filter=args.topic, difficulty_filter=args.difficulty)
    print(top())
    print(row(f"  INTERVIEWFORGE mock interview — session #{session_id}"))
    print(bottom())
    print(f"  {len(picked)} questions · answer each before the timer runs out.\n")

    t0 = time.monotonic()
    try:
        for i, q in enumerate(picked, 1):
            res = ask_question(q, i, len(picked), time_scale=args.time_scale)
            store.record_answer(
                session_id, q.id, q.topic, q.difficulty, res["answer_text"],
                res["score"], res["time_used_s"], res["timed_out"],
                res["key_points_covered"], res["key_points_total"],
            )
    except KeyboardInterrupt:
        print("\n\nInterview interrupted — saving partial results…")
    store.finalize_session(session_id, time.monotonic() - t0)

    terminal, path = generate_report(store, session_id)
    store.close()
    print("\n" + terminal)
    print(f"\n📄 Full report saved to {path}")
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    # The demo uses an isolated throwaway database so it never touches real history.
    tmpdir = tempfile.mkdtemp(prefix="interviewforge-demo-")
    db_path = Path(tmpdir) / "demo.db"
    run_demo(db_path=db_path, out_dir=args.out_dir)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    store = Store()
    sessions = store.list_sessions(limit=args.limit)
    store.close()
    if not sessions:
        print("No sessions yet. Run `python -m interviewforge interview` to start one.")
        return 0
    print(f"{'ID':<5}{'Date':<21}{'Questions':<11}{'Avg':<7}Filters")
    print("─" * 64)
    for s in sessions:
        filt = " / ".join(f for f in (s["topic_filter"], s["difficulty_filter"]) if f) or "mixed"
        print(f"{s['id']:<5}{s['started_at'][:19]:<21}{s['question_count']:<11}"
              f"{s['avg_score']:<7}{filt}")
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    store = Store()
    aggs = store.topic_aggregates()
    store.close()
    if not aggs:
        print("No data yet. Run `python -m interviewforge interview` to start one.")
        return 0
    print("\n  ALL-TIME TOPIC PERFORMANCE\n")
    for a in sorted(aggs, key=lambda x: -x["avg_score"]):
        print(f"  {a['topic']:<16} {score_bar(int(a['avg_score']), 16)} "
              f"{a['avg_score']:>5}/100  ({a['n']} answered)")
    print()
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    store = Store()
    try:
        terminal, path = generate_report(store, args.session_id)
    except ValueError as exc:
        print(exc)
        return 1
    finally:
        store.close()
    print(terminal)
    print(f"\n📄 Full report saved to {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="interviewforge", description="Timed mock interviews with answer scoring.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    iv = sub.add_parser("interview", help="Start a timed mock interview.")
    iv.add_argument("--topic", default=None, help="Limit to one topic (see README).")
    iv.add_argument("--difficulty", default=None, choices=["easy", "medium", "hard"])
    iv.add_argument("-n", "--num", type=int, default=5, help="Number of questions (default 5).")
    iv.add_argument("--time-scale", type=float, default=1.0, help="Scale time limits (e.g. 0.1 for quick tests).")
    iv.add_argument("--seed", type=int, default=None, help="Random seed for question selection.")
    iv.add_argument("--list-only", action="store_true", help="Just list the selected questions.")
    iv.set_defaults(func=cmd_interview)

    d = sub.add_parser("demo", help="Run the scripted end-to-end demo (no input needed).")
    d.add_argument("--out-dir", default="reports", help="Where to save the demo report.")
    d.set_defaults(func=cmd_demo)

    h = sub.add_parser("history", help="List past sessions.")
    h.add_argument("--limit", type=int, default=20)
    h.set_defaults(func=cmd_history)

    s = sub.add_parser("stats", help="Show all-time topic performance.")
    s.set_defaults(func=cmd_stats)

    r = sub.add_parser("report", help="Regenerate the report for a session.")
    r.add_argument("session_id", type=int)
    r.set_defaults(func=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
