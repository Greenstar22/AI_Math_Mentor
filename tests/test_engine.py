from dataclasses import asdict

import pytest

from math_mentor import (
    PROBLEM_BANK, PROBLEMS_BY_ID, StudentProfile, evaluate_solution_steps,
    initialize_database, load_student_history, parse_statement, record_attempt,
    recommend_next_problem, solution_score, symbolic_equivalent, weakness_summary,
)


def test_equivalent_equations():
    assert symbolic_equivalent(parse_statement("3*x+5=20"), parse_statement("3*x=15"))
    assert symbolic_equivalent(parse_statement("x=5"), parse_statement("3*x=15"))


def test_fraction_equivalence():
    assert symbolic_equivalent(parse_statement("3/4+1/8"), parse_statement("7/8"))


@pytest.mark.parametrize("problem", PROBLEM_BANK, ids=lambda p: p.problem_id)
def test_reference_solutions_score_full_marks(problem):
    results = evaluate_solution_steps(problem, [step.math for step in problem.expected_steps])
    assert all(result.is_correct for result in results)
    assert solution_score(results, problem)["overall_score"] == 100.0


def test_incorrect_step_is_caught():
    problem = PROBLEMS_BY_ID["ALG-LIN-001"]
    results = evaluate_solution_steps(problem, ["2*x + 3 = 11", "2*x = 10"])
    assert results[0].is_correct
    assert not results[1].is_correct


def test_profile_progress_and_recommendation(tmp_path):
    profile = StudentProfile("learner", "Learner", "Grades 9-12", {"Algebra": "intermediate"})
    assert set(asdict(profile)) == {
        "student_id", "display_name", "grade_band", "current_levels",
        "preferred_feedback", "accessibility_notes",
    }
    db_path = tmp_path / "progress.db"
    initialize_database(db_path)
    problem = PROBLEMS_BY_ID["ALG-LIN-001"]
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
