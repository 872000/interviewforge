"""Tests for report generation, weak-spot analysis and trends."""

import pytest

from interviewforge.report import (
    compute_trend,
    generate_report,
    score_bar,
    weak_spots,
)
from interviewforge.store import Store


@pytest.fixture()
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


def _fill(store, sid, rows):
    for topic, score in rows:
        store.record_answer(sid, f"{topic}-1", topic, "easy", "answer", score,
                            30.0, False, 2, 4)
    store.finalize_session(sid, 60.0)


def test_score_bar_shape():
    assert score_bar(100, 10) == "█" * 10
    assert score_bar(0, 10) == "░" * 10
    assert len(score_bar(55, 20)) == 20


def test_weak_spots_flags_low_topics():
    aggs = [
        {"topic": "java", "avg_score": 85.0, "n": 2},
        {"topic": "react", "avg_score": 35.0, "n": 2},
    ]
    spots = weak_spots(aggs)
    assert [s["topic"] for s in spots] == ["react"]


def test_weak_spots_empty_when_all_strong():
    aggs = [{"topic": "java", "avg_score": 90.0, "n": 1}]
    assert weak_spots(aggs) == []


def test_compute_trend_compares_previous_session(store):
    s1 = store.create_session()
    _fill(store, s1, [("java", 50), ("react", 80)])
    s2 = store.create_session()
    _fill(store, s2, [("java", 70), ("react", 60)])
    trend = compute_trend(store, s2)
    assert trend["java"] == 20.0
    assert trend["react"] == -20.0


def test_compute_trend_empty_for_first_session(store):
    s1 = store.create_session()
    _fill(store, s1, [("java", 50)])
    assert compute_trend(store, s1) == {}


def test_generate_report_saves_markdown_and_terminal(store, tmp_path):
    s1 = store.create_session()
    _fill(store, s1, [("java", 90), ("react", 30)])
    s2 = store.create_session()
    _fill(store, s2, [("java", 95), ("react", 35)])

    terminal, path = generate_report(store, s2, out_dir=tmp_path / "reports")

    assert path.exists()
    md = path.read_text(encoding="utf-8")
    assert f"Session #{s2}" in md
    assert "## Weak-spot analysis" in md
    assert "react" in md  # weak topic called out

    assert "INTERVIEWFORGE SESSION REPORT" in terminal
    assert "WEAK-SPOT ANALYSIS" in terminal
    assert "react" in terminal


def test_terminal_report_box_lines_have_uniform_width(store, tmp_path):
    s1 = store.create_session()
    _fill(store, s1, [("java", 90), ("react", 30), ("spring-boot", 100)])
    terminal, _ = generate_report(store, s1, out_dir=tmp_path)
    for line in terminal.splitlines():
        assert len(line) == 64, f"box row has wrong width ({len(line)}): {line!r}"


def test_generate_report_unknown_session_raises(store, tmp_path):
    with pytest.raises(ValueError):
        generate_report(store, 4242, out_dir=tmp_path)
