/**
 * MathMentor AI — Solution analysis (STUB)
 *
 * This separate design stub is not the current Python engine or its API contract:
 *   1. Compare each submitted step against the problem bank's ground truth.
 *   2. Rule-based pass first: format/parse, incomplete, and sign-error labels.
 *   3. If unclear, "predict" with a mock logistic-regression model AND a mock
 *      DNN; report a demo confidence constant from a mock with fixed estimated error.
 *   4. On model disagreement, fall back to concept_gap or
 *      algebra_transformation_error.
 *   5. Pick 1 of 3 prebuilt explanation messages for the chosen label.
 *
 * TODO(real version): replace compareStep with a SymPy-based symbolic check,
 * replace mockLogisticRegression / mockDNN with calls to the hosted models,
 * and validate the integration and confidence method before claiming model accuracy.
 */

import type { Problem } from "@/data/problemBank";

export type ErrorLabel =
  | "correct"
  | "sign_error"
  | "calculation_error"
  | "algebra_transformation_error"
  | "concept_gap"
  | "incomplete_step"
  | "format_or_parse_error";

export const ERROR_LABELS: ErrorLabel[] = [
  "correct",
  "sign_error",
  "calculation_error",
  "algebra_transformation_error",
  "concept_gap",
  "incomplete_step",
  "format_or_parse_error",
];

export interface StepFeedback {
  stepId: number;
  submittedStep: string;
  correct: boolean;
  errorLabel: ErrorLabel;
  /** 0-1 demonstration constant/rule value, not a calibrated probability */
  confidence: number;
  concept: string;
  expectedStep: string;
  explanation: string;
}

/** Three prebuilt explanations per error label (prototype wording). */
export const EXPLANATIONS: Record<ErrorLabel, string[]> = {
  correct: [
    "This step is mathematically valid and follows from the previous one.",
    "Correct — your reasoning matches the expected solution here.",
    "Well done. This step is sound; keep going.",
  ],
  sign_error: [
    "A sign was flipped. When moving a term across the equals sign, its sign changes — double-check the positive and negative terms.",
    "Watch the negative sign: it looks like a term lost or gained a minus somewhere in this step.",
    "Sign error detected. Re-expand or re-subtract carefully, tracking each negative term.",
  ],
  calculation_error: [
    "The arithmetic here doesn't check out. Redo the numeric calculation in this step slowly.",
    "A small calculation slipped — recompute the numbers and compare against your previous line.",
    "Your method is fine, but the arithmetic result is wrong. Recalculate this step.",
  ],
  algebra_transformation_error: [
    "The algebraic rewrite isn't equivalent to the previous step. Check your factoring/distribution.",
    "This transformation changed the equation's meaning. Verify each term after expanding or factoring.",
    "An invalid algebraic move — remember you must apply the same operation to every term.",
  ],
  concept_gap: [
    "This step suggests a gap in the underlying concept. Review the core idea behind this problem type, then retry.",
    "The approach here doesn't match what this problem needs. Revisit the concept and how it's applied.",
    "It looks like the key concept isn't connecting yet — try a simpler example of the same idea first.",
  ],
  incomplete_step: [
    "This step is on the right track but unfinished — carry it through to a full result.",
    "Partial work detected. Complete the step before moving on.",
    "You started correctly but stopped short; finish the simplification here.",
  ],
  format_or_parse_error: [
    "This step couldn't be read as math. Check for typos, unmatched brackets, or unsupported symbols.",
    "Formatting issue — write the step as a clear equation or expression.",
    "Unparseable input. Use standard notation like 2x + 3 = 7.",
  ],
};

/* ---------- helpers ---------- */

/** Loose string normalization. TODO: replace with SymPy symbolic equality. */
function normalize(s: string): string {
  return s.replace(/\s+/g, "").toLowerCase();
}

/** Rule-based comparison against the ground-truth step. */
function compareStep(submitted: string, expected: string): ErrorLabel | null {
  const sub = normalize(submitted);
  const exp = normalize(expected);

  if (!sub) return "incomplete_step";
  // crude parse check: unbalanced brackets or stray characters
  const opens = (sub.match(/[([{]/g) || []).length;
  const closes = (sub.match(/[)\]}]/g) || []).length;
  if (opens !== closes || /[^0-9a-z=+\-*/^().,[\]{}]/.test(sub)) {
    return "format_or_parse_error";
  }
  if (sub === exp) return "correct";
  // sign heuristic: same digits but a flipped sign
  const stripSigns = (s: string) => s.replace(/[+-]/g, "");
  if (stripSigns(sub) === stripSigns(exp)) return "sign_error";
  // same length and mostly overlapping → likely just arithmetic
  const digits = (s: string) => (s.match(/\d+/g) || []).sort().join(",");
  if (digits(sub) !== digits(exp) && stripSigns(sub).replace(/\d+/g, "n") === stripSigns(exp).replace(/\d+/g, "n")) {
    return "calculation_error";
  }
  return null; // unclear → hand off to the "models"
}

/** Mock logistic regression prediction. TODO: real model call. */
function mockLogisticRegression(step: string): { label: ErrorLabel; confidence: number; estError: number } {
  const label: ErrorLabel = step.length % 2 === 0 ? "algebra_transformation_error" : "concept_gap";
  return { label, confidence: 0.62, estError: 0.28 };
}

/** Mock DNN prediction. TODO: real model call. */
function mockDNN(step: string): { label: ErrorLabel; confidence: number; estError: number } {
  const label: ErrorLabel = step.length % 3 === 0 ? "concept_gap" : "algebra_transformation_error";
  return { label, confidence: 0.71, estError: 0.22 };
}

function pick<T>(arr: T[], seed: number): T {
  return arr[seed % arr.length];
}

/** Analyze the student's steps against the problem's ground truth. */
export function analyzeSolution(problem: Problem, studentSteps: string[]): StepFeedback[] {
  return studentSteps.map((submitted, i) => {
    const expected = problem.groundTruthSteps[i] ?? problem.groundTruthSteps[problem.groundTruthSteps.length - 1] ?? "";

    let label: ErrorLabel | null = compareStep(submitted, expected);
    let confidence = 1;

    if (label === null) {
      const lr = mockLogisticRegression(submitted);
      const dnn = mockDNN(submitted);
      if (lr.label === dnn.label) {
        // agree → report confidence from the model with the lower estimated error
        const winner = lr.estError <= dnn.estError ? lr : dnn;
        label = winner.label;
        confidence = winner.confidence;
      } else {
        // disagree → fallback
        label = i % 2 === 0 ? "concept_gap" : "algebra_transformation_error";
        confidence = Math.min(lr.confidence, dnn.confidence) * 0.8;
      }
    } else if (label === "correct") {
      confidence = 1;
    } else {
      confidence = 0.9;
    }

    const correct = label === "correct";
    return {
      stepId: i + 1,
      submittedStep: submitted,
      correct,
      errorLabel: label,
      confidence: Math.round(confidence * 100) / 100,
      concept: problem.concept,
      expectedStep: expected,
      explanation: pick(EXPLANATIONS[label], submitted.length + i),
    };
  });
}
