"""Tests for question bank loading, validation and filtering."""

import pytest

from interviewforge.bank import (
    VALID_DIFFICULTIES,
    filter_questions,
    load_bank,
    pick_questions,
    topics,
)


@pytest.fixture(scope="module")
def bank():
    return load_bank()


def test_bank_loads_expected_size(bank):
    assert len(bank) == 28


def test_bank_covers_dsa_and_behavioral(bank):
    ts = topics(bank)
    assert "data-structures" in ts
    assert "algorithms" in ts
    assert "behavioral" in ts
    assert "java" in ts and "spring-boot" in ts and "react" in ts


def test_all_questions_valid(bank):
    for q in bank:
        assert q.id and q.topic and q.question and q.model_answer
        assert q.difficulty in VALID_DIFFICULTIES
        assert len(q.key_points) >= 3
        assert q.time_limit_s >= 60


def test_ids_unique(bank):
    ids = [q.id for q in bank]
    assert len(set(ids)) == len(ids)


def test_filter_by_topic(bank):
    dsa = filter_questions(bank, topic="data-structures")
    assert dsa and all(q.topic == "data-structures" for q in dsa)


def test_filter_by_difficulty(bank):
    hard = filter_questions(bank, difficulty="hard")
    assert hard and all(q.difficulty == "hard" for q in hard)


def test_filter_invalid_difficulty_raises(bank):
    with pytest.raises(ValueError):
        filter_questions(bank, difficulty="impossible")


def test_filter_no_match_returns_empty(bank):
    assert filter_questions(bank, topic="cobol") == []


def test_pick_questions_deterministic_with_seed(bank):
    first = pick_questions(bank, 5, seed=7)
    second = pick_questions(bank, 5, seed=7)
    assert [q.id for q in first] == [q.id for q in second]


def test_pick_questions_caps_at_pool_size(bank):
    assert len(pick_questions(bank, 10_000, seed=1)) == len(bank)
