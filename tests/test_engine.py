from dataclasses import asdict
from collections import defaultdict

import pytest
import sympy as sp

from math_mentor import (
    PROBLEM_BANK, PROBLEMS_BY_ID, StudentProfile, evaluate_solution_steps,
    initialize_database, load_student_history, parse_statement, record_attempt,
    recommend_next_problem, solution_score, symbolic_equivalent, weakness_summary,
)


def test_problem_bank_structure():
    assert len(PROBLEM_BANK) == len(PROBLEMS_BY_ID) == 50
    topics = defaultdict(lambda: defaultdict(list))
    for problem in PROBLEM_BANK:
        topics[problem.topic][problem.concept].append(problem)
    assert len(topics) == 5
    for concepts in topics.values():
        assert len(concepts) == 5
        for pair in concepts.values():
            assert len(pair) == 2
            assert {p.problem_id.rsplit("-", 1)[1] for p in pair} == {"001", "002"}
            assert len({p.difficulty for p in pair}) == 2


@pytest.mark.parametrize("unit", ["i", "I"])
def test_imaginary_unit_arithmetic(unit):
    assert parse_statement(f"{unit}**2") == -1
    assert sp.simplify(parse_statement(f"(3 + 2*{unit})/(1 - {unit})") - (sp.Rational(1, 2) + sp.Rational(5, 2)*sp.I)) == 0
    assert parse_statement(f"(3 + 4{unit}) + (2 - 5{unit})") == 5 - sp.I


@pytest.mark.parametrize("problem_id", ["PRECALC-COMPLEX-001", "PRECALC-COMPLEX-002"])
@pytest.mark.parametrize("unit", ["i", "I"])
def test_imaginary_unit_reference_credit(problem_id, unit):
    problem = PROBLEMS_BY_ID[problem_id]
    results = evaluate_solution_steps(problem, [step.math.replace("i", unit) for step in problem.expected_steps])
    assert [r.matched_expected_index for r in results] == list(range(len(problem.expected_steps)))
    assert all(r.is_correct and r.parse_error is None for r in results)
    assert solution_score(results, problem)["overall_score"] == 100.0


def test_imaginary_normalization_preserves_sympy_names():
    from math_mentor import clean_math_text

    for text, kind in [("Integral(x, x)", sp.Integral), ("Limit(x, x, 0)", sp.Limit)]:
        assert clean_math_text(text) == text
        assert isinstance(parse_statement(text), kind)


def test_equivalent_equations():
    assert symbolic_equivalent(parse_statement("3*x+5=20"), parse_statement("3*x=15"))
    assert symbolic_equivalent(parse_statement("x=5"), parse_statement("3*x=15"))


def test_fraction_equivalence():
    assert symbolic_equivalent(parse_statement("3/4+1/8"), parse_statement("7/8"))


@pytest.mark.parametrize("problem", PROBLEM_BANK, ids=lambda p: p.problem_id)
def test_reference_solutions_score_full_marks(problem):
    assert all(isinstance(parse_statement(step.math), sp.Basic) for step in problem.expected_steps)
    results = evaluate_solution_steps(problem, [step.math for step in problem.expected_steps])
    assert all(result.is_correct for result in results)
    assert solution_score(results, problem)["overall_score"] == 100.0


def test_incorrect_step_is_caught():
    problem = PROBLEMS_BY_ID["ALG1-LIN-001"]
    results = evaluate_solution_steps(problem, ["2*x + 3 = 11", "2*x = 10"])
    assert results[0].is_correct
    assert not results[1].is_correct


def test_profile_progress_and_recommendation(tmp_path):
    profile = StudentProfile("learner", "Learner", "Grades 9-12", {"Algebra 1": "intermediate"})
    assert set(asdict(profile)) == {
        "student_id", "display_name", "grade_band", "current_levels",
        "preferred_feedback", "accessibility_notes",
    }
    db_path = tmp_path / "progress.db"
    initialize_database(db_path)
    problem = PROBLEMS_BY_ID["ALG1-LIN-001"]
    results = evaluate_solution_steps(problem, ["2*x + 3 = 11", "2*x = 10"])
    attempt_id = record_attempt(profile, problem, results, db_path)
    history = load_student_history(profile.student_id, db_path)
    assert len(history) == 2
    assert set(history["attempt_id"]) == {attempt_id}
    assert load_student_history("another_learner", db_path).empty
    assert not weakness_summary(profile.student_id, db_path).empty
    recommendation, ranking = recommend_next_problem(profile, db_path=db_path)
    assert recommendation.problem_id in PROBLEMS_BY_ID
    assert len(ranking) == len(PROBLEM_BANK)


def test_legacy_skill_migration_preserves_history_and_can_repeat(tmp_path):
    import sqlite3

    db_path = tmp_path / "legacy.db"
    initialize_database(db_path)
    profile = StudentProfile("legacy", "Legacy learner", "Grades 9-12", {})
    problem = PROBLEMS_BY_ID["ALG1-LIN-001"]
    evaluations = evaluate_solution_steps(problem, [step.math for step in problem.expected_steps])
    record_attempt(profile, problem, evaluations, db_path)
    original = load_student_history(profile.student_id, db_path)

    # Reproduce the schema used before step concepts were renamed to skills.
    with sqlite3.connect(db_path) as conn:
        conn.execute("ALTER TABLE step_evaluations RENAME COLUMN skill TO concept")

    initialize_database(db_path)
    initialize_database(db_path)
    restored = load_student_history(profile.student_id, db_path)
    assert restored.equals(original)
    assert not weakness_summary(profile.student_id, db_path).empty
