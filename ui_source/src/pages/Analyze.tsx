import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Link } from "react-router-dom";
import { ArrowRight, ArrowLeft, Check, X, RefreshCw } from "lucide-react";
import { pickRandomProblem, type Problem } from "@/data/problemBank";
import { analyzeSolution, type StepFeedback } from "@/lib/analyzeSolution";
import { recordAttempt, type MasteryDelta } from "@/data/mastery";

const LABEL_STYLES: Record<string, string> = {
  correct: "Correct",
  sign_error: "Sign error",
  calculation_error: "Calculation error",
  algebra_transformation_error: "Algebra transformation error",
  concept_gap: "Concept gap",
  incomplete_step: "Incomplete step",
  format_or_parse_error: "Format / parse error",
};

type Phase = "input" | "feedback";

const Analyze = () => {
  const [problem, setProblem] = useState<Problem>(() => pickRandomProblem());
  const [input, setInput] = useState("");
  const [feedback, setFeedback] = useState<StepFeedback[] | null>(null);
  const [deltas, setDeltas] = useState<MasteryDelta[] | null>(null);
  const [phase, setPhase] = useState<Phase>("input");
  const inputRef = useRef<HTMLDivElement>(null);
  const feedbackRef = useRef<HTMLElement>(null);

  // Keep the active panel in view when the phase swaps — the exit/enter
  // animation changes page height, so re-center on the incoming panel.
  useEffect(() => {
    // With mode="wait" the incoming panel mounts only after the outgoing one
    // finishes exiting (~0.55s), so scroll after the swap has completed.
    const timer = setTimeout(() => {
      const el = phase === "feedback" ? feedbackRef.current : inputRef.current;
      el?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 650);
    return () => clearTimeout(timer);
  }, [phase]);

  const newProblem = () => {
    setProblem(pickRandomProblem());
    setInput("");
    setFeedback(null);
    setDeltas(null);
    setPhase("input");
  };

  const runAnalysis = () => {
    const steps = input
      .split("\n")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    if (steps.length === 0) return;
    const result = analyzeSolution(problem, steps);
    setFeedback(result);
    // Prototype: log the attempt and surface the mastery movement it caused.
    setDeltas(
      recordAttempt({
        topicName: "",
        conceptName: problem.concept,
        difficulty: problem.difficulty,
        stepsAttempted: result.length,
        stepsCorrect: result.filter((s) => s.correct).length,
      })
    );
    setPhase("feedback");
  };

  const backToSolution = () => setPhase("input");

  return (
    <main className="min-h-screen bg-background pt-32 pb-20 px-4 md:px-6 overflow-x-hidden">
      <div className="container mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-16"
        >
          <h1 className="heading-display text-[clamp(3rem,10vw,10rem)] leading-[0.85] mb-8">
            Analyze
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl">
            This design demo compares strings and uses mock diagnostics. It does
            not run the Python checker or save progress to Supabase.
          </p>
        </motion.div>

        <AnimatePresence mode="wait" initial={false}>
          {phase === "input" ? (
            <motion.div
              key="input"
              ref={inputRef}
              className="scroll-mt-32"
              initial={{ x: "60%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "-110%", opacity: 0 }}
              transition={{
                duration: 0.55,
                ease: phase === "input" ? [0.22, 1, 0.36, 1] : [0.7, 0, 0.84, 0],
              }}
            >
              {/* Problem */}
              <div className="border border-border bg-secondary/50 p-8 mb-6">
                <div className="flex items-start justify-between gap-6 mb-4">
                  <span className="text-xs uppercase tracking-wider text-muted-foreground">
                    Your problem
                  </span>
                  <button
                    onClick={newProblem}
                    className="inline-flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground hover:text-primary transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    New problem
                  </button>
                </div>
                <p className="text-2xl md:text-3xl text-foreground">
                  {problem.problemText}
                </p>
                <p className="mt-4 text-sm text-muted-foreground">
                  Concept: {problem.concept}
                </p>
              </div>

              {/* Solution input */}
              <div className="border border-border bg-secondary/50 p-8 mb-16">
                <span className="text-xs uppercase tracking-wider text-muted-foreground block mb-4">
                  Your solution — one step per line
                </span>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  rows={6}
                  placeholder={
                    "3(x² − 4x + 3) = 0\n3(x − 1)(x − 3) = 0\nx = 1 or x = 3"
                  }
                  className="w-full bg-background border border-border p-4 text-lg text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:border-primary transition-colors resize-y"
                />
                <button
                  onClick={runAnalysis}
                  disabled={input.trim().length === 0}
                  className="mt-6 inline-flex items-center gap-4 text-lg font-semibold uppercase tracking-wider bg-primary text-primary-foreground px-8 py-4 hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:pointer-events-none group"
                >
                  Analyze my solution
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform" />
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.section
              key="feedback"
              ref={feedbackRef}
              initial={{ x: "60%", opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "-110%", opacity: 0 }}
              transition={{ duration: 0.55, ease: [0.22, 1, 0.36, 1] }}
              className="mb-20 scroll-mt-32"
            >
              <div className="mb-10">
                <div className="flex items-start justify-between gap-6 mb-4">
                  <span className="text-xs uppercase tracking-wider text-muted-foreground">
                    Feedback — {problem.problemText}
                  </span>
                  <div className="flex items-center gap-6 shrink-0">
                    <button
                      onClick={backToSolution}
                      className="inline-flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground hover:text-primary transition-colors"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      Edit solution
                    </button>
                    <button
                      onClick={newProblem}
                      className="inline-flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground hover:text-primary transition-colors"
                    >
                      <RefreshCw className="w-4 h-4" />
                      New problem
                    </button>
                  </div>
                </div>
                <h2 className="heading-display text-3xl md:text-5xl">
                  Step-by-step <span className="text-primary">review</span>
                </h2>
              </div>

              <div className="space-y-6">
                {feedback?.map((step, index) => (
                  <motion.div
                    key={step.stepId}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.3 + index * 0.08 }}
                    className={`border bg-secondary/50 p-6 md:p-8 border-l-4 ${
                      step.correct ? "border-l-primary" : "border-l-destructive"
                    } border-border`}
                  >
                    <div className="flex items-start gap-4 mb-6">
                      {step.correct ? (
                        <Check className="w-6 h-6 mt-1 text-primary shrink-0" />
                      ) : (
                        <X className="w-6 h-6 mt-1 text-destructive shrink-0" />
                      )}
                      <div className="flex-1">
                        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mb-2">
                          <span className="text-xs uppercase tracking-wider text-muted-foreground">
                            Step {step.stepId}
                          </span>
                          <span
                            className={`text-xs font-semibold uppercase tracking-wider ${
                              step.correct ? "text-primary" : "text-destructive"
                            }`}
                          >
                            {LABEL_STYLES[step.errorLabel]}
                          </span>
                          <span className="text-xs uppercase tracking-wider text-muted-foreground">
                            Confidence: {Math.round(step.confidence * 100)}%
                          </span>
                        </div>
                        <p className="text-xl text-foreground">
                          {step.submittedStep}
                        </p>
                      </div>
                    </div>

                    {!step.correct && (
                      <dl className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6 text-base">
                        <div className="border border-border bg-background p-4">
                          <dt className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                            Expected step
                          </dt>
                          <dd className="text-foreground">{step.expectedStep}</dd>
                        </div>
                        <div className="border border-border bg-background p-4">
                          <dt className="text-xs uppercase tracking-wider text-muted-foreground mb-1">
                            Concept
                          </dt>
                          <dd className="text-foreground">{step.concept}</dd>
                        </div>
                      </dl>
                    )}

                    <div className="border-l-2 border-primary pl-4">
                      <p className="text-base md:text-lg text-primary">
                        {step.explanation}
                      </p>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Mastery movement from this attempt */}
              {deltas && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    duration: 0.4,
                    delay: 0.3 + (feedback?.length ?? 0) * 0.08,
                  }}
                  className="mt-10 border border-border bg-secondary/50 p-6 md:p-8"
                >
                  <h3 className="heading-display text-2xl mb-6">
                    Mastery <span className="text-primary">update</span>
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {deltas.map((d) => (
                      <div
                        key={d.scope}
                        className="border border-border bg-background p-5"
                      >
                        <span className="text-xs uppercase tracking-wider text-muted-foreground block mb-1">
                          {d.scope}
                        </span>
                        <p className="text-lg text-foreground mb-4">{d.name}</p>
                        <div className="flex items-end gap-6">
                          <div>
                            <span className="text-xs uppercase tracking-wider text-muted-foreground block">
                              Old
                            </span>
                            <span className="text-xl text-muted-foreground">
                              {d.old.toFixed(2)}
                            </span>
                          </div>
                          <div>
                            <span className="text-xs uppercase tracking-wider text-muted-foreground block">
                              New
                            </span>
                            <span className="text-xl text-foreground">
                              {d.next.toFixed(2)}
                            </span>
                          </div>
                          <div>
                            <span className="text-xs uppercase tracking-wider text-muted-foreground block">
                              Change
                            </span>
                            <span
                              className={`text-xl font-semibold ${
                                d.delta >= 0 ? "text-primary" : "text-destructive"
                              }`}
                            >
                              {d.delta >= 0 ? "+" : ""}
                              {d.delta.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </motion.section>
          )}
        </AnimatePresence>

        {/* CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
        >
          <Link
            to="/"
            className="inline-flex items-center gap-4 text-lg font-semibold uppercase tracking-wider text-muted-foreground hover:text-primary transition-all group"
          >
            Back to home
            <ArrowRight className="w-5 h-5 group-hover:translate-x-2 transition-transform" />
          </Link>
        </motion.div>
      </div>
    </main>
  );
};

export default Analyze;
