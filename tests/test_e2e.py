"""End-to-end tests: the scripted demo and the CLI wiring."""

import subprocess
import sys
from pathlib import Path

import pytest

from interviewforge.demo import DEMO_QUESTION_IDS, run_demo
from interviewforge.store import Store

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_demo_runs_end_to_end(tmp_path):
    session_id, terminal = run_demo(
        db_path=tmp_path / "demo.db", out_dir=tmp_path / "reports", verbose=False
    )
    assert session_id == 1
    assert "INTERVIEWFORGE SESSION REPORT" in terminal
    assert "WEAK-SPOT ANALYSIS" in terminal

    store = Store(tmp_path / "demo.db")
    try:
        answers = store.session_answers(session_id)
        assert len(answers) >= len(DEMO_QUESTION_IDS)
        assert any(a["timed_out"] for a in answers)  # demo includes a timeout case
        scores = [a["score"] for a in answers]
        assert min(scores) < max(scores)  # mixed answer quality shows a spread
        session = store.get_session(session_id)
        assert session["question_count"] == len(answers)
    finally:
        store.close()

    reports = list((tmp_path / "reports").glob("session-*.md"))
    assert len(reports) == 1


def test_demo_cli_subprocess(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-m", "interviewforge", "demo", "--out-dir", str(tmp_path / "r")],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "INTERVIEWFORGE" in proc.stdout
    assert list((tmp_path / "r").glob("session-*.md"))


def test_interview_list_only_cli():
    proc = subprocess.run(
        [sys.executable, "-m", "interviewforge", "interview",
         "--topic", "react", "--list-only", "-n", "2", "--seed", "3"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "react" in proc.stdout


def test_history_cli_empty_db(tmp_path, monkeypatch):
    monkeypatch.setenv("INTERVIEWFORGE_DB", str(tmp_path / "empty.db"))
    proc = subprocess.run(
        [sys.executable, "-m", "interviewforge", "history"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert "No sessions yet" in proc.stdout
