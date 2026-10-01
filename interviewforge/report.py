"""Per-session reports: weak-spot analysis, trends, terminal + markdown output."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .store import Store
from .terminal import bottom, divider, row, top

WEAK_THRESHOLD = 60  # topics averaging below this are flagged as weak spots


def score_bar(score: int, width: int = 20) -> str:
    filled = int(round(score / 100 * width))
    return "█" * filled + "░" * (width - filled)


def weak_spots(aggregates: list[dict]) -> list[dict]:
    """Topics sorted weakest-first that fall below the weak threshold."""
    return [a for a in sorted(aggregates, key=lambda a: a["avg_score"]) if a["avg_score"] < WEAK_THRESHOLD]


def compute_trend(store: Store, session_id: int) -> dict[str, float]:
    """Per-topic score delta of this session vs the previous session (all-time)."""
    prev_id = store.previous_session_id(session_id)
    if prev_id is None:
        return {}
    prev = {a["topic"]: a["avg_score"] for a in store.topic_aggregates()}
    # rebuild previous-session aggregates from answers of prev session only
    prev_rows = {a["topic"]: a["avg_score"] for a in store.topic_aggregates(prev_id)}
    current = {a["topic"]: a["avg_score"] for a in store.topic_aggregates(session_id)}
    deltas = {}
    for topic, avg in current.items():
        if topic in prev_rows:
            deltas[topic] = round(avg - prev_rows[topic], 1)
    return deltas


def trend_arrow(delta: float) -> str:
    if delta > 0.5:
        return f"▲ +{delta}"
    if delta < -0.5:
        return f"▼ {delta}"
    return "▬ steady"


def render_terminal(
    session: dict,
    answers: list[dict],
    aggregates: list[dict],
    trend: dict[str, float],
    spots: list[dict],
) -> str:
    lines = []
    lines.append(top())
    lines.append(row(f"  INTERVIEWFORGE SESSION REPORT  #{session['id']}"))
    lines.append(divider())
    filt = " / ".join(f for f in (session["topic_filter"], session["difficulty_filter"]) if f) or "mixed"
    lines.append(row(f"  {session['started_at'][:19]}Z   {session['question_count']} questions · {filt}"))
    lines.append(row(f"  Average score: {session['avg_score']:>5} / 100"))
    lines.append(divider())
    lines.append(row("  PER-QUESTION RESULTS"))
    for i, a in enumerate(answers, 1):
        flag = " [timeout]" if a["timed_out"] else ""
        lines.append(row(f"  Q{i}. [{a['topic']}/{a['difficulty']}] {a['question_id']}{flag}"))
        lines.append(row(f"      {score_bar(a['score'])} {a['score']:>3}/100  "
                         f"({a['key_points_covered']}/{a['key_points_total']} key points)"))
    lines.append(divider())
    lines.append(row("  TOPIC BREAKDOWN"))
    for agg in sorted(aggregates, key=lambda a: -a["avg_score"]):
        t = trend.get(agg["topic"])
        tstr = f"  {trend_arrow(t)}" if t is not None else ""
        lines.append(row(f"  {agg['topic']:<16} {score_bar(int(agg['avg_score']), 14)} "
                         f"{agg['avg_score']:>5}{tstr}"))
    lines.append(divider())
    lines.append(row("  WEAK-SPOT ANALYSIS"))
    if spots:
        for s in spots:
            lines.append(row(f"  ! {s['topic']:<16} avg {s['avg_score']:>5} / "
                             f"{s['n']} answered — drill it"))
    else:
        lines.append(row("  No weak spots — every topic scored 60+."))
    lines.append(bottom())
    return "\n".join(lines)


def build_markdown(
    session: dict,
    answers: list[dict],
    aggregates: list[dict],
    trend: dict[str, float],
    spots: list[dict],
) -> str:
    md = [f"# InterviewForge Session #{session['id']} Report", ""]
    md.append(f"- **Date:** {session['started_at'][:19]}Z")
    md.append(f"- **Questions:** {session['question_count']} ({session['topic_filter'] or 'mixed topics'}, "
              f"{session['difficulty_filter'] or 'mixed difficulty'})")
    md.append(f"- **Average score:** {session['avg_score']}/100")
    md.append("")
    md.append("## Per-question results")
    md.append("")
    md.append("| # | Question | Topic | Difficulty | Score | Key points |")
    md.append("|---|----------|-------|------------|-------|------------|")
    for i, a in enumerate(answers, 1):
        flag = " ⏰" if a["timed_out"] else ""
        md.append(f"| {i} | {a['question_id']} | {a['topic']} | {a['difficulty']} | "
                  f"{a['score']}/100{flag} | {a['key_points_covered']}/{a['key_points_total']} |")
    md.append("")
    md.append("## Topic breakdown")
    md.append("")
    for agg in sorted(aggregates, key=lambda a: -a["avg_score"]):
        t = trend.get(agg["topic"])
        tstr = f" ({trend_arrow(t)} vs previous session)" if t is not None else ""
        md.append(f"- **{agg['topic']}**: {agg['avg_score']}/100 over {agg['n']} question(s){tstr}")
    md.append("")
    md.append("## Weak-spot analysis")
    md.append("")
    if spots:
        for s in spots:
            md.append(f"- ⚠️ **{s['topic']}** — averaging {s['avg_score']}/100. "
                      f"Recommended: run `python -m interviewforge interview --topic {s['topic']}` to drill it.")
    else:
        md.append("No weak spots — every topic scored 60+ this session. 🎉")
    md.append("")
    md.append("## Answer feedback")
    md.append("")
    for i, a in enumerate(answers, 1):
        md.append(f"### Q{i} — {a['question_id']} ({a['score']}/100)")
        md.append("")
        if a["answer_text"]:
            md.append(f"> {a['answer_text'][:400]}")
            md.append("")
    md.append("---")
    md.append("*Generated by InterviewForge — practice like it's the real thing.*")
    md.append("")
    return "\n".join(md)


def generate_report(store: Store, session_id: int, out_dir: str | Path = "reports") -> tuple[str, Path]:
    """Build the terminal + markdown report for a session; saves the markdown file."""
    session = store.get_session(session_id)
    if session is None:
        raise ValueError(f"No session #{session_id}")
    answers = store.session_answers(session_id)
    aggregates = store.topic_aggregates(session_id)
    trend = compute_trend(store, session_id)
    spots = weak_spots(aggregates)

    terminal = render_terminal(session, answers, aggregates, trend, spots)
    markdown = build_markdown(session, answers, aggregates, trend, spots)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out / f"session-{session_id}-{stamp}.md"
    path.write_text(markdown, encoding="utf-8")
    return terminal, path
