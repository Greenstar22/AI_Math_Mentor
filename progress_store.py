"""Owner-scoped storage and pure adapters; guest data lives only in session memory."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from typing import Protocol
from uuid import uuid4, UUID

import pandas as pd

from math_mentor import (PROBLEM_BANK, StudentProfile, FeedbackBandit, FEEDBACK_STYLES,
                         run_mentor_attempt, weakness_summary, recommend_next_problem)

TOPICS = sorted({p.topic for p in PROBLEM_BANK})
PROFILE_FIELDS = {"display_name", "grade_band", "school_class", "preferred_feedback",
                  "accessibility_notes", "theme", "current_levels"}


def now():
    return datetime.now(timezone.utc).isoformat()


def default_profile(guest=False):
    return dict(display_name="Guest" if guest else "Student", grade_band="Grades 9-12",
                school_class="", preferred_feedback="socratic", accessibility_notes="",
                theme="Dark", current_levels={t: "beginner" for t in TOPICS})


def validate_profile(profile):
    if set(profile) != PROFILE_FIELDS:
        raise ValueError("Profile contains unsupported fields.")
    for name, maximum in [("display_name", 80), ("school_class", 120), ("accessibility_notes", 1000), ("grade_band", 80)]:
        if not isinstance(profile[name], str) or len(profile[name]) > maximum:
            raise ValueError(f"Invalid {name.replace('_', ' ')}.")
    if not profile["display_name"].strip():
        raise ValueError("Enter a display name.")
    if profile["theme"] not in {"Dark", "Light"} or profile["preferred_feedback"] not in FEEDBACK_STYLES:
        raise ValueError("Invalid theme or feedback style.")
    levels = profile["current_levels"]
    if not isinstance(levels, dict) or set(levels) != set(TOPICS) or any(v not in {"beginner", "intermediate", "advanced"} for v in levels.values()):
        raise ValueError("Invalid topic levels.")
    return deepcopy(profile)


def student_profile(owner, profile):
    return StudentProfile(owner, profile["display_name"], profile["grade_band"],
                          deepcopy(profile["current_levels"]), profile["preferred_feedback"],
                          profile["accessibility_notes"])


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def validate_payload(payload):
    required = {"attempt_id", "problem_id", "problem_version", "topic", "concept", "difficulty",
                "scoring_version", "step_accuracy", "coverage", "overall_score", "submitted_at",
                "problem_snapshot", "evaluations", "ratings"}
    if set(payload) != required:
        raise ValueError("Invalid attempt fields.")
    UUID(payload["attempt_id"])
    if datetime.fromisoformat(payload["submitted_at"]).tzinfo is None:
        raise ValueError("Attempt timestamp needs a timezone.")
    if payload["topic"] not in TOPICS or type(payload["difficulty"]) is not int or payload["difficulty"] not in {1, 2, 3} or payload["scoring_version"] != "v1":
        raise ValueError("Invalid attempt metadata.")
    for field, upper in [("step_accuracy", 1), ("coverage", 1), ("overall_score", 100)]:
        if not isinstance(payload[field], (int, float)) or not 0 <= payload[field] <= upper:
            raise ValueError("Invalid score.")
    snapshot = payload["problem_snapshot"]
    if set(snapshot) != {"problem_id", "topic", "concept", "grade_band", "difficulty", "prompt", "expected_steps", "final_answer", "hints"}:
        raise ValueError("Invalid problem snapshot.")
    if any(not isinstance(snapshot[k], str) for k in ("problem_id", "topic", "concept", "grade_band", "prompt", "final_answer")):
        raise ValueError("Invalid problem text.")
    if not isinstance(snapshot["expected_steps"], list) or not snapshot["expected_steps"]:
        raise ValueError("Invalid expected steps.")
    if any(set(step) != {"math", "skill", "explanation"} or any(not isinstance(v, str) for v in step.values()) for step in snapshot["expected_steps"]):
        raise ValueError("Invalid expected step fields.")
    if not isinstance(snapshot["hints"], list) or any(not isinstance(hint, str) for hint in snapshot["hints"]):
        raise ValueError("Invalid problem hints.")
    if hashlib.sha256(canonical(snapshot).encode()).hexdigest() != payload["problem_version"]:
        raise ValueError("Problem version mismatch.")
    for key in ("problem_id", "topic", "concept", "difficulty"):
        if payload[key] != snapshot[key]:
            raise ValueError("Problem metadata mismatch.")
    evaluations = payload["evaluations"]
    indices = [e["student_step_index"] for e in evaluations]
    if not indices or len(set(indices)) != len(indices) or any(type(i) is not int or i < 1 for i in indices):
        raise ValueError("Invalid step indices.")
    for e in evaluations:
        if set(e) != {"student_step_index", "student_step", "expected_step", "matched_expected_index",
                      "is_correct", "error_type", "confidence", "skill", "explanation", "skipped_expected_steps",
                      "parse_error", "feedback_style", "feedback_text"}:
            raise ValueError("Invalid evaluation fields.")
        if not 0 <= e["confidence"] <= 1 or e["feedback_style"] not in FEEDBACK_STYLES:
            raise ValueError("Invalid evaluation.")
        if type(e["is_correct"]) is not bool or any(not isinstance(e[k], str) for k in
                ("student_step", "error_type", "skill", "explanation", "feedback_text")):
            raise ValueError("Invalid evaluation text or verdict.")
        if not isinstance(e["skipped_expected_steps"], list) or any(not isinstance(v, str) for v in e["skipped_expected_steps"]):
            raise ValueError("Invalid skipped steps.")
    rated = set()
    for r in payload["ratings"]:
        validate_rating(r)
        if r["student_step_index"] not in indices or r["student_step_index"] in rated:
            raise ValueError("Invalid rating step.")
        rated.add(r["student_step_index"])
    canonical(payload)


def validate_rating(rating):
    if set(rating) != {"feedback_event_id", "student_step_index", "context_key", "feedback_style", "reward", "created_at"}:
        raise ValueError("Invalid rating fields.")
    UUID(rating["feedback_event_id"])
    if type(rating["reward"]) is not int or rating["reward"] not in {-1, 1} or rating["feedback_style"] not in FEEDBACK_STYLES:
        raise ValueError("Invalid feedback rating.")
    if type(rating["student_step_index"]) is not int or rating["student_step_index"] < 1 or not isinstance(rating["context_key"], str):
        raise ValueError("Invalid rating step or context.")
    if datetime.fromisoformat(rating["created_at"]).tzinfo is None:
        raise ValueError("Rating timestamp needs a timezone.")


class ProgressStore(Protocol):
    owner_id: str
    def load_profile(self) -> dict: ...
    def save_profile(self, profile: dict) -> None: ...
    def save_attempts(self, attempts: list[dict]) -> None: ...
    def load_attempts(self) -> list[dict]: ...
    def load_history(self) -> pd.DataFrame: ...
    def load_feedback_events(self) -> list[dict]: ...
    def record_feedback(self, attempt_id: str, rating: dict) -> bool: ...


def history_frame(attempts):
    rows = []
    for attempt in attempts:
        for step in attempt["evaluations"]:
            rows.append({**{k: attempt[k] for k in ("attempt_id", "problem_id", "topic", "difficulty", "overall_score", "submitted_at")},
                         **{k: step[k] for k in ("student_step_index", "is_correct", "error_type", "confidence", "skill")}})
    return pd.DataFrame(rows, columns=["attempt_id", "problem_id", "topic", "difficulty", "overall_score", "submitted_at",
                                      "student_step_index", "is_correct", "error_type", "confidence", "skill"])


class GuestProgressStore:
    def __init__(self, memory):
        self.memory = memory
        memory.setdefault("owner_id", "guest_" + str(uuid4()))
        memory.setdefault("profile", default_profile(guest=True))
        memory.setdefault("attempts", {})
        memory.setdefault("ratings", {})
        self.owner_id = memory["owner_id"]

    def load_profile(self):
        return deepcopy(self.memory["profile"])

    def save_profile(self, profile):
        self.memory["profile"] = validate_profile(profile)

    def save_attempts(self, attempts):
        updated = deepcopy(self.memory["attempts"])
        for attempt in attempts:
            validate_payload(attempt)
            key = attempt["attempt_id"]
            if key in updated and canonical(updated[key]) != canonical(attempt):
                raise ValueError("An attempt with this ID has different content.")
            updated[key] = deepcopy(attempt)
        # Commit only after every supplied item passes validation.
        self.memory["attempts"] = updated

    def load_attempts(self):
        attempts = deepcopy(list(self.memory["attempts"].values()))
        for attempt in attempts:
            extra = [r for (aid, _), r in self.memory["ratings"].items() if aid == attempt["attempt_id"]]
            attempt["ratings"].extend(deepcopy(extra))
        return sorted(attempts, key=lambda a: (a["submitted_at"], a["attempt_id"]))

    def load_history(self):
        return history_frame(self.load_attempts())

    def load_feedback_events(self):
        return [{**r, "attempt_id": a["attempt_id"]} for a in self.load_attempts() for r in a["ratings"]]

    def record_feedback(self, attempt_id, rating):
        validate_rating(rating)
        attempt = self.memory["attempts"].get(attempt_id)
        if not attempt or rating["student_step_index"] not in {e["student_step_index"] for e in attempt["evaluations"]}:
            raise ValueError("This evaluated step is unavailable.")
        key = (attempt_id, rating["student_step_index"])
        if key in self.memory["ratings"] or any(r["student_step_index"] == key[1] for r in attempt["ratings"]):
            return False
        self.memory["ratings"][key] = deepcopy(rating)
        return True


def rebuild_bandit(store):
    bandit = FeedbackBandit()
    for event in store.load_feedback_events():
        bandit.update(event["context_key"], event["feedback_style"], event["reward"])
    return bandit


def analyze(store, problem_id, steps, bandit):
    attempt_id, submitted_at = str(uuid4()), now()
    profile = student_profile(store.owner_id, store.load_profile())
    report = run_mentor_attempt(profile, problem_id, steps, save=False, history=store.load_history(), bandit=bandit)
    snapshot = deepcopy(report["problem"])
    feedback = {f["step"]: f for f in report["feedback"]}
    payload = dict(attempt_id=attempt_id, submitted_at=submitted_at, problem_snapshot=snapshot,
                   problem_version=hashlib.sha256(canonical(snapshot).encode()).hexdigest(), scoring_version="v1",
                   **{k: snapshot[k] for k in ("problem_id", "topic", "concept", "difficulty")},
                   **report["scores"], evaluations=[{**e, "feedback_style": feedback[e["student_step_index"]]["style"],
                   "feedback_text": feedback[e["student_step_index"]]["feedback"]} for e in report["evaluations"]], ratings=[])
    validate_payload(payload)
    report["attempt_id"] = payload["attempt_id"]
    return deepcopy(payload), report


def report_for_attempt(store, attempt):
    # Saved verdicts, snapshot and generated feedback are used verbatim; no regrading.
    history = store.load_history()
    profile = student_profile(store.owner_id, store.load_profile())
    recommendation, ranking = recommend_next_problem(profile, history=history, attempted_problem_ids=history["problem_id"].unique().tolist())
    return dict(attempt_id=attempt["attempt_id"], submitted_at=attempt["submitted_at"], profile=asdict(profile),
                problem=deepcopy(attempt["problem_snapshot"]), scores={k: attempt[k] for k in ("step_accuracy", "coverage", "overall_score")},
                evaluations=[{k: v for k, v in e.items() if k not in {"feedback_style", "feedback_text"}} for e in attempt["evaluations"]],
                feedback=[dict(step=e["student_step_index"], style=e["feedback_style"], feedback=e["feedback_text"]) for e in attempt["evaluations"]],
                weakness_summary=weakness_summary(history=history).to_dict("records"), recommended_problem=asdict(recommendation),
                recommendation_ranking=ranking.to_dict("records"))


def new_rating(step, style, reward):
    return dict(feedback_event_id=str(uuid4()), student_step_index=step["student_step_index"],
                context_key=step["error_type"], feedback_style=style, reward=reward, created_at=now())
