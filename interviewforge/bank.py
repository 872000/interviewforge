"""Question bank loading, validation and filtering."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

BANK_PATH = Path(__file__).with_name("data") / "questions.json"

VALID_DIFFICULTIES = ("easy", "medium", "hard")
REQUIRED_FIELDS = ("id", "topic", "difficulty", "question", "key_points", "model_answer")


@dataclass
class Question:
    id: str
    topic: str
    difficulty: str
    question: str
    key_points: list
    model_answer: str
    time_limit_s: int

    @classmethod
    def from_dict(cls, data: dict) -> "Question":
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            raise ValueError(f"Question {data.get('id', '?')} missing fields: {missing}")
        if data["difficulty"] not in VALID_DIFFICULTIES:
            raise ValueError(f"Question {data['id']} has invalid difficulty: {data['difficulty']}")
        if not data["key_points"]:
            raise ValueError(f"Question {data['id']} has no key points")
        return cls(
            id=data["id"],
            topic=data["topic"],
            difficulty=data["difficulty"],
            question=data["question"],
            key_points=list(data["key_points"]),
            model_answer=data["model_answer"],
            time_limit_s=int(data.get("time_limit_s", 120)),
        )


def load_bank(path: str | Path = BANK_PATH) -> list[Question]:
    """Load and validate the question bank from JSON."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    questions = [Question.from_dict(item) for item in raw["questions"]]
    ids = [q.id for q in questions]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate question ids in bank")
    return questions


def topics(questions: list[Question]) -> list[str]:
    """Sorted unique topic names in the bank."""
    return sorted({q.topic for q in questions})


def filter_questions(
    questions: list[Question],
    topic: str | None = None,
    difficulty: str | None = None,
) -> list[Question]:
    """Filter by topic and/or difficulty (None means 'any')."""
    result = questions
    if topic:
        result = [q for q in result if q.topic == topic]
    if difficulty:
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {difficulty!r} (choose from {VALID_DIFFICULTIES})")
        result = [q for q in result if q.difficulty == difficulty]
    return result


def pick_questions(questions: list[Question], n: int, seed: int | None = None) -> list[Question]:
    """Pick up to n questions, shuffled deterministically when seed is given."""
    rng = random.Random(seed)
    pool = list(questions)
    rng.shuffle(pool)
    return pool[: max(0, n)]
