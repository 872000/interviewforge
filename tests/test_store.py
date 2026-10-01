"""Tests for SQLite persistence."""

import pytest

from interviewforge.store import Store


@pytest.fixture()
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


def _answer(store, session_id, topic="java", score=70):
    store.record_answer(
        session_id, "java-001", topic, "easy", "an answer", score,
        30.0, False, 3, 4,
    )


def test_create_and_finalize_session(store):
    sid = store.create_session(topic_filter="java", difficulty_filter="easy")
    _answer(store, sid, score=80)
    _answer(store, sid, score=60)
    store.finalize_session(sid, 120.5)

    session = store.get_session(sid)
    assert session["question_count"] == 2
    assert session["avg_score"] == 70.0
    assert session["duration_s"] == 120
    assert session["topic_filter"] == "java"


def test_list_sessions_newest_first(store):
    s1 = store.create_session()
    s2 = store.create_session()
    ids = [s["id"] for s in store.list_sessions()]
    assert ids == [s2, s1]


def test_topic_aggregates(store):
    sid = store.create_session()
    _answer(store, sid, topic="java", score=90)
    _answer(store, sid, topic="java", score=70)
    _answer(store, sid, topic="react", score=40)
    aggs = {a["topic"]: a for a in store.topic_aggregates(sid)}
    assert aggs["java"]["avg_score"] == 80.0
    assert aggs["java"]["n"] == 2
    assert aggs["react"]["avg_score"] == 40.0


def test_all_time_aggregates_span_sessions(store):
    s1 = store.create_session()
    _answer(store, s1, topic="java", score=100)
    s2 = store.create_session()
    _answer(store, s2, topic="java", score=50)
    aggs = {a["topic"]: a for a in store.topic_aggregates()}
    assert aggs["java"]["avg_score"] == 75.0


def test_previous_session_id(store):
    s1 = store.create_session()
    s2 = store.create_session()
    assert store.previous_session_id(s2) == s1
    assert store.previous_session_id(s1) is None


def test_get_missing_session_returns_none(store):
    assert store.get_session(9999) is None


def test_timed_out_flag_persisted(store):
    sid = store.create_session()
    store.record_answer(sid, "q", "java", "easy", "", 0, 60.0, True, 0, 3)
    answers = store.session_answers(sid)
    assert answers[0]["timed_out"] == 1
