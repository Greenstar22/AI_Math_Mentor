from math_mentor import PROBLEM_BANK, StudentProfile, run_mentor_attempt


def main() -> None:
    profile = StudentProfile(
        student_id="smoke_test_student",
        display_name="Smoke Test",
        grade_band="Grades 9-12",
        current_levels={
            "Geometry": "beginner",
            "Algebra 1": "intermediate",
            "Calculus": "beginner",
            "Algebra 2": "intermediate",
            "Precalculus": "beginner",
        },
        preferred_feedback="socratic",
    )
    problem = next(item for item in PROBLEM_BANK if item.problem_id == "ALG1-LIN-001")
    steps = ["2*x + 3 = 11", "2*x = 8", "x = 4"]
    report = run_mentor_attempt(profile, problem.problem_id, steps, save=False)
    assert report["scores"]["overall_score"] >= 90
    assert len(report["evaluations"]) == 3
    assert report["recommended_problem"]["problem_id"]
    print("Smoke test passed")


if __name__ == "__main__":
    main()
