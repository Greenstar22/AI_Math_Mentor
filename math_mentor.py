from __future__ import annotations

import json
import random
import re
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import sympy as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

AUTHOR = "Anchit Nayak"
ADVISOR = "Dr. Qingyang Xiao"
PROJECT_TITLE = "AI Math Mentor App"
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

WORK_DIR = Path.cwd()
DB_PATH = WORK_DIR / "ai_math_mentor.db"
EXPORT_DIR = WORK_DIR / "ai_math_mentor_exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StudentProfile:
    student_id: str
    display_name: str
    grade_band: str
    current_levels: Dict[str, str]
    preferred_feedback: str = "socratic"
    accessibility_notes: str = ""


@dataclass
class ExpectedStep:
    math: str
    skill: str
    explanation: str


@dataclass
class MathProblem:
    problem_id: str
    topic: str
    concept: str
    grade_band: str
    difficulty: int
    prompt: str
    expected_steps: List[ExpectedStep]
    final_answer: str
    hints: List[str]

    @property
    def skills(self) -> List[str]:
        return list(dict.fromkeys(step.skill for step in self.expected_steps))


PROBLEM_BANK: List[MathProblem] = [
    MathProblem(
        problem_id="ALG1-FRAC-001",
        topic="Algebra 1",
        concept="Fractions",
        grade_band="Grades 5-7",
        difficulty=1,
        prompt="Compute 3/4 + 2/3. Show a common-denominator step and represent your answer as a mixed fraction.",
        expected_steps=[
            ExpectedStep("3/4 + 2/3", "equation_setup", "Identify the two fractions to add."),
            ExpectedStep("9/12 + 8/12", "least_common_denominator", "Rewrite both fractions with denominator 12."),
            ExpectedStep("17/12", "simplification", "Add the numerators while keeping the denominator."),
            ExpectedStep("1 + 5/12", "mixed_number", "Convert the improper fraction to a mixed number."),
        ],
        final_answer="1 + 5/12",
        hints=["The least common denominator of 4 and 3 is 12.", "Multiply 3/4 by 3/3 and 2/3 by 4/4."],
    ),
    MathProblem(
        problem_id="ALG1-EXP-001",
        topic="Algebra 1",
        concept="Exponents",
        grade_band="Grades 7-9",
        difficulty=2,
        prompt="Solve for x: ((9/16)^2)/((3/4)^3)",
        expected_steps=[
            ExpectedStep("((9/16)^2)/((3/4)^3)", "equation_setup", "Identify the structure of the expression."),
            ExpectedStep("(((3/4)^2)^2)/((3/4)^3)", "same_base", "Rewrite both fractions with the same base."),
            ExpectedStep("((3/4)^4)/((3/4)^3)", "simplification", "Multiply the exponents of the numerator."),
            ExpectedStep("3/4", "exponent_division", "Divide the numerator by the denominator as per the exponent division rule."),
        ],
        final_answer="3/4",
        hints=["Convert both exponentials to the same base.", "Use the exponent division rule to simplify."],
    ),
    MathProblem(
        problem_id="ALG1-LIN-001",
        topic="Algebra 1",
        concept="Linear equations",
        grade_band="Grades 7-10",
        difficulty=1,
        prompt="Solve 2x + 3 = 11. Show each algebraic transformation.",
        expected_steps=[
            ExpectedStep("2*x + 3 = 11", "equation_setup", "Restate the equation."),
            ExpectedStep("2*x = 8", "balanced_subtraction", "Subtract 3 from both sides."),
            ExpectedStep("x = 4", "balanced_division", "Divide both sides by 2."),
        ],
        final_answer="x = 4",
        hints=["Undo the +3 first.", "Apply the same operation to both sides."],
    ),
    MathProblem(
        problem_id="ALG1-LIN-002",
        topic="Algebra 1",
        concept="Linear equations",
        grade_band="Grades 7-10",
        difficulty=1,
        prompt="Find the slope of the line: 16y + 98x = 39.",
        expected_steps=[
            ExpectedStep("16*y + 98*x = 39", "equation_setup", "Restate the equation."),
            ExpectedStep("16*y = -98*x + 39", "balanced_subtraction", "Subtract 98*x from both sides."),
            ExpectedStep("y = (-98/16)*x + 39/16", "balanced_division", "Divide both sides by 16."),
            ExpectedStep("-98/16", "slope_identification", "Identify the slope from the coefficient of x."),
        ],
        final_answer="-98/16",
        hints=["Convert the equation to slope-intercept form.", "The slope of a line is the coefficient of x of the equation in slope-intercept form."],
    ),
    MathProblem(
        problem_id="ALG1-QUAD-001",
        topic="Algebra 1",
        concept="Quadratic equations",
        grade_band="Grades 9-12",
        difficulty=2,
        prompt="Solve x^2 - 5x + 6 = 0 by factoring.",
        expected_steps=[
            ExpectedStep("x**2 - 5*x + 6 = 0", "equation_setup", "Restate the quadratic equation."),
            ExpectedStep("(x - 2)*(x - 3) = 0", "factoring", "Factor the quadratic."),
            ExpectedStep("x = 2", "zero_product_property", "Set the first factor equal to zero."),
            ExpectedStep("x = 3", "zero_product_property", "Set the second factor equal to zero."),
        ],
        final_answer="x = 2 or x = 3",
        hints=["Find two numbers whose product is 6 and sum is -5.", "Use the zero-product property after factoring."],
    ),
    MathProblem(
        problem_id="ALG1-QUAD-002",
        topic="Algebra 1",
        concept="Quadratic equations",
        grade_band="Grades 9-12",
        difficulty=2,
        prompt="Find the y-coordinate of the vertex of the parabola y = x^2 - 5x + 6.",
        expected_steps=[
            ExpectedStep("y = x**2 - 5*x + 6", "equation_setup", "Restate the quadratic equation."),
            ExpectedStep("x = -b/(2*a)", "vertex_formula", "Apply the vertex formula."),
            ExpectedStep("x = --5/(2*1)", "substitution", "Substitute a = 1 and b = -5."),
            ExpectedStep("x = 5/2", "simplification", "Simplify the expression."),
            ExpectedStep("y = (5/2)**2 - 5*(5/2) + 6", "substitution", "Substitute x = 5/2 into the equation."),
            ExpectedStep("y = -1/4", "simplification", "Simplify the expression."),
        ],
        final_answer="y = -1/4.",
        hints=["Use the formula for the x-coordinate of the vertex for a parabola in standard form.", "Substitute the x-coordinate into the equation of the parabola to find the y-coordinate."],
        ),
    MathProblem(
        problem_id="ALG1-PROB-001",
        topic="Algebra 1",
        concept="Probability",
        grade_band="Grades 9-12",
        difficulty=2,
        prompt="Two fair coins are tossed. Find the probability of at least one head using the complement rule.",
        expected_steps=[
            ExpectedStep("P_none = (1/2)**2", "independence_property", "Compute the probability of no heads."),
            ExpectedStep("P_at_least_one = 1 - P_none", "complement_rule", "Use the complement rule."),
            ExpectedStep("P_at_least_one = 1 - (1/2)**2", "substitution", "Substitute the value of P_none."),
            ExpectedStep("P_at_least_one = 3/4", "simplification", "Simplify the probability."),
        ],
        final_answer="3/4",
        hints=["The complement of at least one head is zero heads.", "P(TT) = 1/2 times 1/2."],
        ),
    
    MathProblem(
        problem_id="GEO-TRIG-001",
        topic="Geometry",
        concept="Trigonometry",
        grade_band="Grades 6-8",
        difficulty=1,
        prompt="The two legs of a right triangle are 10 units and 24 units. Find the length of the hypotenuse using the Pythagorean theorem.",
        expected_steps=[
            ExpectedStep("a^2 + b^2 = c^2", "pythagorean_theorem", "Apply the Pythagorean theorem."),
            ExpectedStep("10^2 + 24^2 = c^2", "substitution", "Substitute the known values."),
            ExpectedStep("100 + 576 = c^2", "simplification", "Calculate the squares."),
            ExpectedStep("676 = c^2", "simplification", "Add the results."),
            ExpectedStep("c = 26", "square_root", "Take the square root of both sides."),
        ],
        final_answer="26",
        hints=["The pythagorean theorem states that a^2 + b^2 = c^2.", "a and b are the legs of the right triangle, while c is the length of the hypotenuse."],
        ),
    MathProblem(
        problem_id="ALG2-CONIC-001",
        topic="Algebra 2",
        concept="Conic sections",
        grade_band="Grades 9-12",
        difficulty=3,
        prompt="Find the sum of the x-coordinate and y-coordinate of the vertex of the conic section: x^2 + 8x + y^2 + 6y = 0.",
        expected_steps=[
            ExpectedStep("x^2 + 8x + y^2 + 6y = 0", "equation_setup", "Identify the conic section equationo."),
            ExpectedStep("x^2 + 8x + 16 + y^2 + 6y + 9 = 16 + 9", "completing_the_square", "Add 16 and 9 to both sides to complete the square."),
            ExpectedStep("(x + 4)^2 + (y + 3)^2 = 25", "factoring", "Factor the completed squares into squared factors."),
            ExpectedStep("(x - h)^2 + (y - k)^2 = r^2", "equation_setup", "Identify the standard form of a circle."),
            ExpectedStep("h = -4", "vertex_analysis", "Identify the x-coordinate of the vertex."),
            ExpectedStep("k = -3", "vertex_analysis", "Identify the y-coordinate of the vertex."),
            ExpectedStep("-4 + (-3)", "equation_setup", "Model the sum of the coordinates."),
            ExpectedStep("-7", "simplification", "Calculate the answer")
        ],
        final_answer="-7",
        hints=["Complete the square for both the x terms and the y terms individually", "To complete the square, add numbers to both sides to be able to factor the x and y terms into two squared factors", "Add (b/2)^2 to both sides twice, once where b is the coefficient of the first degree x term and once for y term", "Compare the resulting equation with the equation for a circle to determine the coordinates of the vertex"],
            ),
    MathProblem(
        problem_id="PRECALC-COMPLEX-001",
        topic="Precalculus",
        concept="Complex numbers",
        grade_band="Grades 9-12",
        difficulty=1,
        prompt="Find the sum of the coefficients of the real and imaginary terms of the complex number (3 + 4i) + (2 - 5i).",
        expected_steps=[
            ExpectedStep("(3 + 4i) + (2 - 5i)", "equation_setup", "Identify the equation."),
            ExpectedStep("5 - i", "simplification", "Combine like terms."),
            ExpectedStep("5 + (-1)", "equation_setup", "Model the sum of the coefficients of the real and imaginary terms."),
            ExpectedStep("4", "simplification", "Calculate the answer."),
        ],
        final_answer="4",
        hints=["To add complex numbers, add the real parts and the imaginary parts separately.", "The real part of (3 + 4i) is 3, and the real part of (2 - 5i) is 2.", "The imaginary part of (3 + 4i) is 4i, and the imaginary part of (2 - 5i) is -5i."],
    ),
    MathProblem(
        problem_id="CALC-POLYDERIV-001",
        topic="Calculus",
        concept="Polynomial derivatives",
        grade_band="College / AP",
        difficulty=2,
        prompt="Differentiate f(x) = x^3 - 4x + 7 with respect to x.",
        expected_steps=[
            ExpectedStep("Derivative(x**3 - 4*x + 7, x)", "derivative_setup", "Write the derivative operator."),
            ExpectedStep("3*x**2 - 4 + 0", "power_rule", "Apply the power rule and constant rule term by term."),
            ExpectedStep("3*x**2 - 4", "simplification", "Simplify the derivative."),
        ],
        final_answer="3*x**2 - 4",
        hints=["d/dx(x^n) = n*x^(n-1).", "The derivative of a constant is zero."],
    ),
    MathProblem(
        problem_id="CALC-DE-001",
        topic="Calculus",
        concept="Differential equations",
        grade_band="College",
        difficulty=3,
        prompt="Solve dy/dt = 3y with y(0) = 2. Show separation, integration, and the initial-condition step.",
        expected_steps=[
            ExpectedStep("1/y", "separation", "Separate variables conceptually: dy/y = 3 dt."),
            ExpectedStep("log(y) = 3*t + C", "integration", "Integrate both sides."),
            ExpectedStep("y = C*exp(3*t)", "exponentiation", "Exponentiate and absorb constants."),
            ExpectedStep("y = 2*exp(3*t)", "initial_condition", "Use y(0) = 2."),
        ],
        final_answer="y = 2*exp(3*t)",
        hints=["Move y to the left before integrating.", "After exponentiating, use the initial condition to find C."],
    )
]

PROBLEMS_BY_ID = {p.problem_id: p for p in PROBLEM_BANK}
LEVEL_TO_DIFFICULTY = {"entry": 1, "beginner": 1, "intermediate": 2, "advanced": 3}


def normalize_level(level: str) -> str:
    level = (level or "entry").strip().lower()
    for known in LEVEL_TO_DIFFICULTY:
        if known in level:
            return known
    return "entry"


def assign_initial_problems(profile: StudentProfile, limit: int = 5) -> List[MathProblem]:
    scored: List[Tuple[float, MathProblem]] = []
    for problem in PROBLEM_BANK:
        stated = profile.current_levels.get(problem.topic, "entry")
        target_difficulty = LEVEL_TO_DIFFICULTY[normalize_level(stated)]
        score = 3.0 - abs(problem.difficulty - target_difficulty)
        if profile.grade_band.lower() in problem.grade_band.lower():
            score += 0.5
        scored.append((score, problem))
    scored.sort(key=lambda item: (-item[0], item[1].difficulty, item[1].problem_id))
    return [p for _, p in scored[:limit]]


TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)
LOCAL_DICT = {
    "x": sp.Symbol("x"),
    "y": sp.Symbol("y", positive=True),
    "t": sp.Symbol("t"),
    "C": sp.Symbol("C"),
    "P_none": sp.Symbol("P_none"),
    "P_at_least_one": sp.Symbol("P_at_least_one"),
    "Derivative": sp.Derivative,
    "diff": sp.diff,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.log,
    "sqrt": sp.sqrt,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
}


def clean_math_text(text: str) -> str:
    text = str(text).strip()
    text = re.sub(r"^step\s*\d+\s*[:.)-]?\s*", "", text, flags=re.I)
    replacements = {"−": "-", "–": "-", "×": "*", "÷": "/", "π": "pi", "√": "sqrt", "^": "**"}
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.replace("d/dx", "Derivative")
    return text.strip()


def parse_statement(text: str) -> sp.Basic:
    cleaned = clean_math_text(text)
    if not cleaned:
        raise ValueError("Empty step")
    if cleaned.count("=") == 1:
        lhs_text, rhs_text = [part.strip() for part in cleaned.split("=", 1)]
        lhs = parse_expr(lhs_text, local_dict=LOCAL_DICT, transformations=TRANSFORMATIONS, evaluate=True)
        rhs = parse_expr(rhs_text, local_dict=LOCAL_DICT, transformations=TRANSFORMATIONS, evaluate=True)
        return sp.Eq(lhs, rhs, evaluate=False)
    return parse_expr(cleaned, local_dict=LOCAL_DICT, transformations=TRANSFORMATIONS, evaluate=True)


def equation_residual(statement: sp.Basic) -> sp.Basic:
    if isinstance(statement, sp.Equality):
        return sp.expand(statement.lhs - statement.rhs)
    return sp.expand(statement)


def _safe_solution_set(statement: sp.Basic, variable: sp.Symbol) -> Optional[sp.Set]:
    try:
        residual = equation_residual(statement)
        return sp.solveset(residual, variable, domain=sp.S.Complexes)
    except Exception:
        return None


def symbolic_equivalent(a: sp.Basic, b: sp.Basic) -> bool:
    if isinstance(a, sp.Equality) and isinstance(b, sp.Equality):
        symbols = sorted(a.free_symbols | b.free_symbols, key=lambda s: s.name)
        if len(symbols) == 1:
            set_a = _safe_solution_set(a, symbols[0])
            set_b = _safe_solution_set(b, symbols[0])
            if set_a is not None and set_b is not None and set_a == set_b:
                return True
        ra = sp.factor(equation_residual(a))
        rb = sp.factor(equation_residual(b))
        try:
            if sp.simplify(ra - rb) == 0 or sp.simplify(ra + rb) == 0:
                return True
            if rb != 0:
                ratio = sp.simplify(ra / rb)
                if not ratio.free_symbols and ratio != 0:
                    return True
        except Exception:
            pass
        return False
    if isinstance(a, sp.Equality) != isinstance(b, sp.Equality):
        return False
    try:
        return bool(sp.simplify(a - b) == 0)
    except Exception:
        return False


ERROR_LABELS = [
    "correct", "calculation_error", "sign_error", "algebra_transformation_error",
    "skill_gap", "incomplete_step", "format_or_parse_error",
]


def build_synthetic_error_dataset(seed: int = SEED) -> pd.DataFrame:
    rng = random.Random(seed)
    templates = {
        "correct": [
            "student step {step}; expected {expected}; equivalent symbolic result; correct operation",
            "valid transformation from {previous} to {step}; equation remains balanced",
            "correct use of {skill}; result {step}",
        ],
        "calculation_error": [
            "student computed {step} but expected {expected}; arithmetic value is wrong",
            "incorrect addition multiplication or fraction simplification in {step}",
            "number calculation mismatch between {step} and {expected}",
        ],
        "sign_error": [
            "student used the wrong sign in {step}; expected {expected}",
            "negative sign was lost or reversed after {previous}",
            "plus minus error in {step}",
        ],
        "algebra_transformation_error": [
            "operation was not applied to both sides in {step}; expected {expected}",
            "invalid distribution factoring cancellation or variable isolation in {step}",
            "equation balance changed from {previous} to {step}",
        ],
        "skill_gap": [
            "student selected the wrong rule for {skill}; step {step}",
            "missing understanding of {skill}; expected approach {expected}",
            "used an unrelated formula in {step}",
        ],
        "incomplete_step": [
            "step {step} is unfinished and does not reach {expected}",
            "student skipped necessary reasoning after {previous}",
            "partial expression without a complete transformation: {step}",
        ],
        "format_or_parse_error": [
            "cannot parse student notation {step}; use explicit equals signs and operators",
            "ambiguous or malformed math input in {step}",
            "unrecognized notation prevents symbolic evaluation: {step}",
        ],
    }
    skills = ["fraction addition", "inverse operations", "factoring", "power rule", "complement rule", "separation of variables", "initial condition"]
    steps = ["2*x=8", "x=4", "9/12+8/12", "17/12", "3*x**2-4", "P=3/4", "y=2*exp(3*t)", "(x-2)*(x-3)=0"]
    wrong_steps = ["2*x=14", "x=-4", "9/12+8/12=17/24", "3*x**2+4", "P=1/4", "y=2+exp(3*t)", "x**2-6=0", "2*x+3=8"]
    rows = []
    for label, label_templates in templates.items():
        for i in range(36):
            correct_step = rng.choice(steps)
            step = correct_step if label == "correct" else rng.choice(wrong_steps)
            expected = rng.choice(steps)
            previous = rng.choice(steps)
            skill = rng.choice(skills)
            text = rng.choice(label_templates).format(step=step, expected=expected, previous=previous, skill=skill)
            if i % 3 == 0:
                text += f"; topic {rng.choice(['algebra', 'calculus', 'probability', 'fractions', 'differential equations'])}"
            rows.append({"text": text, "label": label})
    rng.shuffle(rows)
    return pd.DataFrame(rows)


error_dataset = build_synthetic_error_dataset()
X_train, X_test, y_train, y_test = train_test_split(
    error_dataset["text"], error_dataset["label"], test_size=0.25, random_state=SEED, stratify=error_dataset["label"]
)
ERROR_CLASSIFIER = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), analyzer="word", min_df=1, max_features=2000)),
    ("model", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=SEED)),
])
ERROR_CLASSIFIER.fit(X_train, y_train)
DNN_VECTORIZER = TfidfVectorizer(ngram_range=(1, 2), max_features=500, sublinear_tf=True)
X_train_dnn = DNN_VECTORIZER.fit_transform(X_train).toarray()
DNN_LABEL_ENCODER = LabelEncoder()
y_train_dnn = DNN_LABEL_ENCODER.fit_transform(y_train)
DNN_CLASSIFIER = MLPClassifier(
    hidden_layer_sizes=(64, 32), activation="relu", solver="adam", alpha=1e-4,
    batch_size=32, learning_rate_init=1e-3, max_iter=350, early_stopping=True,
    validation_fraction=0.15, n_iter_no_change=20, random_state=SEED,
)
DNN_CLASSIFIER.fit(X_train_dnn, y_train_dnn)


@dataclass
class StepEvaluation:
    student_step_index: int
    student_step: str
    matched_expected_index: Optional[int]
    expected_step: Optional[str]
    is_correct: bool
    error_type: str
    confidence: float
    skill: str
    explanation: str
    skipped_expected_steps: List[str] = field(default_factory=list)
    parse_error: Optional[str] = None


def extract_numbers(text: str) -> List[float]:
    values = []
    for token in re.findall(r"[-+]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?", text):
        try:
            if "/" in token:
                num, den = token.split("/", 1)
                values.append(float(num) / float(den))
            else:
                values.append(float(token))
        except Exception:
            pass
    return values


def has_sign_pattern_difference(student: str, expected: str) -> bool:
    s = parse_statement(clean_math_text(student).replace(" ", ""))
    e = parse_statement(clean_math_text(expected).replace(" ", ""))
    if isinstance(s, sp.Equality) and isinstance(e, sp.Equality):
        return (sp.simplify(s.lhs + e.lhs) == 0 and s.rhs == e.rhs) or (sp.simplify(s.rhs + e.rhs) == 0 and s.lhs == e.lhs)
    elif not isinstance(s, sp.Equality) and not isinstance(e, sp.Equality):
        return sp.simplify(s + e) == 0
    else:
        return False


def build_classifier_text(student_step: str, expected_step: str, previous_step: str, skill: str, diagnostic: str) -> str:
    return f"student step {student_step}; expected {expected_step}; previous {previous_step}; skill {skill}; diagnostic {diagnostic}"


def ml_error_prediction(text: str) -> Tuple[str, float]:
    probabilities = ERROR_CLASSIFIER.predict_proba([text])[0]
    labels = ERROR_CLASSIFIER.classes_
    idx = int(np.argmax(probabilities))
    return str(labels[idx]), float(probabilities[idx])


def dnn_error_prediction(text: str) -> Tuple[str, float]:
    vector = DNN_VECTORIZER.transform([text]).toarray()
    probabilities = DNN_CLASSIFIER.predict_proba(vector)[0]
    idx = int(np.argmax(probabilities))
    label = DNN_LABEL_ENCODER.inverse_transform([idx])[0]
    return str(label), float(probabilities[idx])


def classify_incorrect_step(student_step: str, expected_step: str, previous_step: str, skill: str, parse_exception: Optional[Exception] = None, matching_expected_path: bool = True) -> Tuple[str, float, str]:
    if parse_exception is not None:
        return "format_or_parse_error", 0.99, "The notation could not be parsed. Use one mathematical statement per line and explicit operators when needed."
    stripped = clean_math_text(student_step)
    if len(stripped) <= 2 or stripped.endswith(("=", "+", "-", "*", "/")):
        return "incomplete_step", 0.95, "The line appears incomplete. Finish the mathematical statement before moving to the next step."
    if has_sign_pattern_difference(student_step, expected_step):
        return "sign_error", 0.88, "A plus or minus sign differs from the expected transformation. Recheck signs before simplifying."
    student_numbers = extract_numbers(student_step)
    expected_numbers = extract_numbers(expected_step)
    if student_numbers and expected_numbers and set(student_numbers) != set(expected_numbers):
        student_letters = re.sub(r"[-+]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?", "N", clean_math_text(student_step))
        expected_letters = re.sub(r"[-+]?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?", "N", clean_math_text(expected_step))
        if student_letters.replace(" ", "") == expected_letters.replace(" ", ""):
            return "calculation_error", 0.90, "The operation pattern is plausible, but one or more numerical calculations do not match."
    diagnostic_text = build_classifier_text(student_step, expected_step, previous_step, skill, "symbolically not equivalent")
    ml_label, ml_conf = ml_error_prediction(diagnostic_text)
    dnn_label, dnn_conf = dnn_error_prediction(diagnostic_text)
    if ml_label == dnn_label:
        if ml_label == "correct":
            return "unclassified", min(0.95, 0.55 + 0.45 * max(ml_conf, dnn_conf)), f"Both learned classifiers identified this as {ml_label.replace('_', ' ')}. Your error was not able to be classified."
        return ml_label, min(0.95, 0.55 + 0.45 * max(ml_conf, dnn_conf)), f"Both learned classifiers identified this as {ml_label.replace('_', ' ')}. Review the expected skill and compare each transformation."
    if skill in {"power_rule", "complement_rule", "separation", "integration", "initial_condition", "factoring"}:
        return "skill_gap", 0.62, f"The step does not match the expected use of {skill.replace('_', ' ')}. Review that skill before retrying."
    return "algebra_transformation_error", 0.60, "The transformation is not symbolically equivalent to the expected step. Check whether the same legal operation was applied throughout."


def evaluate_solution_steps(problem: MathProblem, student_steps: Sequence[str]) -> List[StepEvaluation]:
    expected_parsed: List[Optional[sp.Basic]] = []
    expected_cleaned: List[Optional[str]] = []
    for expected in problem.expected_steps:
        try:
            expected_parsed.append(parse_statement(expected.math))
            expected_cleaned.append(clean_math_text(expected.math))
        except Exception:
            expected_parsed.append(None)
            expected_cleaned.append(None)
    results: List[StepEvaluation] = []
    next_expected_index = 0
    previous_student_step = None
    matching_expected_path = True
    for student_index, raw_step in enumerate(student_steps, start=1):
        raw_step = str(raw_step).strip()
        if not raw_step:
            continue
        try:
            parsed_student = parse_statement(raw_step)
            cleaned_student = clean_math_text(raw_step)
            parse_exception = None
        except Exception as exc:
            parsed_student = None
            cleaned_student = None
            parse_exception = exc
        try:
            parsed_previous = parse_statement(previous_student_step) if previous_student_step else None
        except Exception:
            parsed_previous = None
        matched_index = None
        if parsed_student is not None:
            for j in range(next_expected_index, len(problem.expected_steps)):
                expected_obj = expected_parsed[j]
                cleaned_expected = expected_cleaned[j]
                if cleaned_expected is not None and cleaned_student == cleaned_expected:  # symbolic_equivalent(parsed_student, expected_obj):
                    matched_index = j
                    break
        if matched_index is not None:
            skipped = [s.math for s in problem.expected_steps[next_expected_index:matched_index]]
            expected = problem.expected_steps[matched_index]
            explanation = "This step is mathematically equivalent to the expected step."
            if matched_index > next_expected_index:
                explanation += " It is correct, but some intermediary steps were skipped."
            result = StepEvaluation(
                student_step_index=student_index, student_step=raw_step, matched_expected_index=matched_index,
                expected_step=expected.math, is_correct=True, error_type="correct", confidence=0.99,
                skill=expected.skill, explanation=explanation, skipped_expected_steps=skipped,
            )
            next_expected_index = matched_index + 1
            matching_expected_path = True
        elif parsed_student is not None and parsed_previous is not None and symbolic_equivalent(parsed_student, parsed_previous):
            target_index = min(next_expected_index, len(problem.expected_steps) - 1)
            expected = problem.expected_steps[target_index]
            if matching_expected_path:
                label, confidence, explanation = "valid additional step", 0.99, "The transformation is mathematically valid, but does not match the expected solution path."
            else:
                label, confidence, explanation = "carry-on error", 0.99, "The transformation is mathematically valid, but does not match the expected solution path due to a previous deviation."
            result = StepEvaluation(
                student_step_index=student_index, student_step=raw_step, matched_expected_index=None,
                expected_step=expected.math, is_correct=True, error_type=label, confidence=confidence,
                skill=expected.skill, explanation=explanation,
            )
        else:
            target_index = min(next_expected_index, len(problem.expected_steps) - 1)
            expected = problem.expected_steps[target_index]
            label, confidence, explanation = classify_incorrect_step(
                student_step=raw_step, expected_step=expected.math, previous_step=previous_student_step,
                skill=expected.skill, parse_exception=parse_exception, matching_expected_path=matching_expected_path,
            )
            result = StepEvaluation(
                student_step_index=student_index, student_step=raw_step, matched_expected_index=None,
                expected_step=expected.math, is_correct=False, error_type=label, confidence=confidence,
                skill=expected.skill, explanation=explanation,
                parse_error=str(parse_exception) if parse_exception else None,
            )
            next_expected_index += 1
            matching_expected_path = False
        results.append(result)
        previous_student_step = raw_step
    return results


def solution_score(evaluations: Sequence[StepEvaluation], problem: MathProblem) -> Dict[str, float]:
    if not evaluations:
        return {"step_accuracy": 0.0, "coverage": 0.0, "overall_score": 0.0}
    correct_count = sum(item.is_correct for item in evaluations)
    unique_matches = len({item.matched_expected_index for item in evaluations if item.matched_expected_index is not None})
    step_accuracy = correct_count / len(evaluations)
    coverage = unique_matches / max(1, len(problem.expected_steps))
    overall = 100.0 * (0.65 * step_accuracy + 0.35 * coverage)
    return {"step_accuracy": round(step_accuracy, 3), "coverage": round(coverage, 3), "overall_score": round(overall, 1)}


def evaluations_to_frame(evaluations: Sequence[StepEvaluation]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "student_step": e.student_step_index,
            "submitted": e.student_step,
            "correct": e.is_correct,
            "error_type": e.error_type,
            "confidence": round(e.confidence, 3),
            "skill": e.skill,
            "expected": e.expected_step,
            "explanation": e.explanation,
        }
        for e in evaluations
    ])


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path = DB_PATH) -> None:
    with get_connection(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, grade_band TEXT NOT NULL,
            current_levels_json TEXT NOT NULL, preferred_feedback TEXT NOT NULL,
            accessibility_notes TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL,
            problem_id TEXT NOT NULL, topic TEXT NOT NULL, difficulty INTEGER NOT NULL,
            overall_score REAL NOT NULL, submitted_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(student_id)
        );
        CREATE TABLE IF NOT EXISTS step_evaluations (
            step_evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT, attempt_id INTEGER NOT NULL,
            student_step_index INTEGER NOT NULL, submitted_step TEXT NOT NULL, expected_step TEXT,
            is_correct INTEGER NOT NULL, error_type TEXT NOT NULL, confidence REAL NOT NULL,
            skill TEXT NOT NULL, explanation TEXT NOT NULL,
            FOREIGN KEY(attempt_id) REFERENCES attempts(attempt_id)
        );
        CREATE TABLE IF NOT EXISTS feedback_events (
            feedback_event_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL,
            context_key TEXT NOT NULL, feedback_style TEXT NOT NULL, reward REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        # CREATE TABLE IF NOT EXISTS does not update databases from older versions.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(step_evaluations)")}
        if "concept" in columns and "skill" not in columns:
            conn.execute("ALTER TABLE step_evaluations RENAME COLUMN concept TO skill")



def upsert_student(profile: StudentProfile, db_path: Path = DB_PATH) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.execute("""
            INSERT INTO students (student_id, display_name, grade_band, current_levels_json, preferred_feedback, accessibility_notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                display_name=excluded.display_name, grade_band=excluded.grade_band,
                current_levels_json=excluded.current_levels_json, preferred_feedback=excluded.preferred_feedback,
                accessibility_notes=excluded.accessibility_notes
        """, (profile.student_id, profile.display_name, profile.grade_band, json.dumps(profile.current_levels), profile.preferred_feedback, profile.accessibility_notes, now))


def record_attempt(profile: StudentProfile, problem: MathProblem, evaluations: Sequence[StepEvaluation], db_path: Path = DB_PATH) -> int:
    upsert_student(profile, db_path)
    score = solution_score(evaluations, problem)["overall_score"]
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO attempts (student_id, problem_id, topic, difficulty, overall_score, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
            (profile.student_id, problem.problem_id, problem.topic, problem.difficulty, score, now),
        )
        attempt_id = int(cursor.lastrowid)
        conn.executemany("""
            INSERT INTO step_evaluations (attempt_id, student_step_index, submitted_step, expected_step, is_correct, error_type, confidence, skill, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (attempt_id, e.student_step_index, e.student_step, e.expected_step, int(e.is_correct), e.error_type, e.confidence, e.skill, e.explanation)
            for e in evaluations
        ])
    return attempt_id


def load_student_history(student_id: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    query = """
        SELECT a.attempt_id, a.problem_id, a.topic, a.difficulty, a.overall_score, a.submitted_at,
               s.student_step_index, s.is_correct, s.error_type, s.confidence, s.skill
        FROM attempts a JOIN step_evaluations s ON a.attempt_id = s.attempt_id
        WHERE a.student_id = ? ORDER BY a.submitted_at, s.student_step_index
    """
    with get_connection(db_path) as conn:
        return pd.read_sql_query(query, conn, params=(student_id,))


def weakness_summary(student_id: str, db_path: Path = DB_PATH) -> pd.DataFrame:
    history = load_student_history(student_id, db_path)
    if history.empty:
        return pd.DataFrame(columns=["topic", "skill", "attempted_steps", "correct_steps", "error_rate", "mastery"])
    grouped = history.groupby(["topic", "skill"], as_index=False).agg(
        attempted_steps=("is_correct", "size"), correct_steps=("is_correct", "sum"), avg_difficulty=("difficulty", "mean")
    )
    grouped["error_rate"] = 1.0 - grouped["correct_steps"] / grouped["attempted_steps"]
    grouped["mastery"] = ((grouped["correct_steps"] + 1.0) / (grouped["attempted_steps"] + 2.0)) * (1.0 + 0.05 * (grouped["avg_difficulty"] - 1.0))
    grouped["mastery"] = grouped["mastery"].clip(0.0, 1.0)
    return grouped.sort_values(["mastery", "attempted_steps"], ascending=[True, False]).reset_index(drop=True)


def recommend_next_problem(profile: StudentProfile, student_id: Optional[str] = None, attempted_problem_ids: Optional[Iterable[str]] = None, db_path: Path = DB_PATH) -> Tuple[MathProblem, pd.DataFrame]:
    student_id = student_id or profile.student_id
    attempted_problem_ids = set(attempted_problem_ids or [])
    weaknesses = weakness_summary(student_id, db_path)
    weak_topics = defaultdict(float)
    weak_concepts = defaultdict(float)
    for _, row in weaknesses.iterrows():
        weak_topics[row["topic"]] = max(weak_topics[row["topic"]], float(row["error_rate"]))
        weak_concepts[row["skill"]] = max(weak_concepts[row["skill"]], float(row["error_rate"]))
    scored = []
    for problem in PROBLEM_BANK:
        stated_level = normalize_level(profile.current_levels.get(problem.topic, "entry"))
        target = LEVEL_TO_DIFFICULTY[stated_level]
        score = 2.0 - abs(problem.difficulty - target)
        score += 2.5 * weak_topics.get(problem.topic, 0.0)
        score += sum(0.8 * weak_concepts.get(step.skill, 0.0) for step in problem.expected_steps)
        if problem.problem_id not in attempted_problem_ids:
            score += 0.4
        scored.append((score, problem))
    scored.sort(key=lambda item: (-item[0], item[1].difficulty, item[1].problem_id))
    recommendation_table = pd.DataFrame([
        {"rank": rank, "problem_id": problem.problem_id, "topic": problem.topic, "difficulty": problem.difficulty, "score": round(score, 3), "prompt": problem.prompt}
        for rank, (score, problem) in enumerate(scored, start=1)
    ])
    return scored[0][1], recommendation_table


FEEDBACK_STYLES = ["socratic", "concise_hint", "worked_example"]


class FeedbackBandit:
    def __init__(self, epsilon: float = 0.15):
        self.epsilon = epsilon
        self.counts: Dict[Tuple[str, str], int] = defaultdict(int)
        self.values: Dict[Tuple[str, str], float] = defaultdict(float)

    def choose(self, context_key: str, preferred_style: Optional[str] = None) -> str:
        if preferred_style in FEEDBACK_STYLES and sum(self.counts[(context_key, action)] for action in FEEDBACK_STYLES) == 0:
            return str(preferred_style)
        if random.random() < self.epsilon:
            return random.choice(FEEDBACK_STYLES)
        return max(FEEDBACK_STYLES, key=lambda action: (self.values[(context_key, action)], -FEEDBACK_STYLES.index(action)))

    def update(self, context_key: str, action: str, reward: float) -> None:
        key = (context_key, action)
        self.counts[key] += 1
        n = self.counts[key]
        old_value = self.values[key]
        self.values[key] = old_value + (reward - old_value) / n


FEEDBACK_BANDIT = FeedbackBandit(epsilon=0.15)


def create_feedback(evaluation: StepEvaluation, problem: MathProblem, style: str) -> str:
    skill_name = evaluation.skill.replace("_", " ")
    expected = evaluation.expected_step or "the next valid transformation"
    if evaluation.is_correct:
        if evaluation.error_type == "carry-on error":
            return f"Correct. Your step is mathematically valid, but it does not match the expected solution path due to a previous deviation. Review the earlier steps and try to align with the expected transformations."
        if evaluation.error_type == "valid additional step":
            return f"Correct. Your step preserves the mathematics and contributes towards demonstrating {skill_name}. However, this step is not completely necessary. Continue to the next transformation."
        return f"Correct. Your step preserves the mathematics and demonstrates {skill_name}. Continue to the next transformation."
    if style == "socratic":
        prompts = {
            "calculation_error": "Recalculate only the numerical part. Which arithmetic operation changed the value?",
            "sign_error": "What should happen to the sign when you move or simplify this term?",
            "algebra_transformation_error": "Did you apply the same legal operation to every required part of the expression or equation?",
            "skill_gap": f"Which rule governs {skill_name}, and what conditions must be true before using it?",
            "incomplete_step": "What mathematical statement would make this line complete?",
            "format_or_parse_error": "Can you rewrite this as one explicit expression or equation using an equals sign?",
        }
        return prompts.get(evaluation.error_type, "What is the next mathematically justified transformation?")
    if style == "worked_example":
        examples = {
            "calculation_error": "Parallel example: 2a + 3 = 11 becomes 2a = 8 after subtracting 3 from both sides.",
            "sign_error": "Parallel example: -(x - 2) expands to -x + 2, because the negative sign multiplies both terms.",
            "algebra_transformation_error": "Parallel example: from 3z = 12, divide both sides by 3 to obtain z = 4.",
            "skill_gap": f"Review a small example of {skill_name}, then apply the same rule to your current line.",
            "incomplete_step": "Parallel example: instead of writing '2x =', finish the statement as '2x = 8'.",
            "format_or_parse_error": "Use a format such as '2*x + 3 = 11' or '3*x**2 - 4'.",
        }
        return examples.get(evaluation.error_type, f"Compare your line with the expected structure: {expected}")
    hints = {
        "calculation_error": "Recheck the arithmetic before continuing.",
        "sign_error": "Audit every plus and minus sign.",
        "algebra_transformation_error": "Preserve equivalence by applying a valid operation consistently.",
        "skill_gap": f"Review the {skill_name} rule.",
        "incomplete_step": "Complete the expression or equation.",
        "format_or_parse_error": "Rewrite using explicit mathematical notation.",
    }
    return hints.get(evaluation.error_type, evaluation.explanation)


def record_feedback_reward(student_id: str, context_key: str, style: str, reward: float, db_path: Path = DB_PATH) -> None:
    FEEDBACK_BANDIT.update(context_key, style, reward)
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO feedback_events (student_id, context_key, feedback_style, reward, created_at) VALUES (?, ?, ?, ?, ?)",
            (student_id, context_key, style, float(reward), datetime.now(timezone.utc).isoformat()),
        )


def run_mentor_attempt(profile: StudentProfile, problem_id: str, student_steps: Sequence[str], save: bool = True) -> Dict[str, Any]:
    if problem_id not in PROBLEMS_BY_ID:
        raise KeyError(f"Unknown problem_id: {problem_id}")
    problem = PROBLEMS_BY_ID[problem_id]
    evaluations = evaluate_solution_steps(problem, student_steps)
    scores = solution_score(evaluations, problem)
    attempt_id = record_attempt(profile, problem, evaluations) if save else None
    feedback_rows = []
    for evaluation in evaluations:
        style = FEEDBACK_BANDIT.choose(evaluation.error_type, preferred_style=profile.preferred_feedback)
        feedback_rows.append({"step": evaluation.student_step_index, "style": style, "feedback": create_feedback(evaluation, problem, style)})
    attempted_ids = []
    history = load_student_history(profile.student_id)
    if not history.empty:
        attempted_ids = history["problem_id"].unique().tolist()
    recommendation, ranking = recommend_next_problem(profile, attempted_problem_ids=attempted_ids)
    return {
        "attempt_id": attempt_id,
        "profile": asdict(profile),
        "problem": asdict(problem),
        "scores": scores,
        "evaluations": [asdict(e) for e in evaluations],
        "feedback": feedback_rows,
        "weakness_summary": weakness_summary(profile.student_id).to_dict(orient="records"),
        "recommended_problem": asdict(recommendation),
        "recommendation_ranking": ranking.to_dict(orient="records"),
    }


def report_to_markdown(report: Dict[str, Any]) -> str:
    problem = report["problem"]
    scores = report["scores"]
    lines = [
        "# Math Mentor Report", "",
        f"**Author:** {AUTHOR}  ", f"**Advisor:** {ADVISOR}", "",
        f"**Problem:** {problem['problem_id']} - {problem['prompt']}", "",
        f"**Overall score:** {scores['overall_score']} / 100  ",
        f"**Submitted-step accuracy:** {100*scores['step_accuracy']:.1f}%  ",
        f"**Expected-path coverage:** {100*scores['coverage']:.1f}%", "", "## Step analysis",
    ]
    feedback_by_step = {item["step"]: item for item in report["feedback"]}
    for evaluation in report["evaluations"]:
        marker = "Correct" if evaluation["is_correct"] else "Needs revision"
        lines.extend([
            f"### Step {evaluation['student_step_index']}: {marker}",
            f"- Submitted: `{evaluation['student_step']}`",
            f"- Expected target: `{evaluation['expected_step']}`",
            f"- Category: `{evaluation['error_type']}`",
            f"- Skill: `{evaluation['skill']}`",
            f"- Diagnosis: {evaluation['explanation']}",
            f"- Mentor response ({feedback_by_step[evaluation['student_step_index']]['style']}): {feedback_by_step[evaluation['student_step_index']]['feedback']}", "",
        ])
    recommendation = report["recommended_problem"]
    lines.extend([
        "## Recommended next problem",
        f"**{recommendation['problem_id']}** ({recommendation['topic']}, difficulty {recommendation['difficulty']}): {recommendation['prompt']}",
    ])
    return "\n".join(lines)


initialize_database()
