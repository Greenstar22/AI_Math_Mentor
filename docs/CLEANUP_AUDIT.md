# Cleanup audit and project map

This audit compares the working tree with Git HEAD before the cleanup. It is an explanation, not an additional application change. No commit or push has been made.

## 1. What the evidence establishes

`app.py` and `math_mentor.py` have no changes relative to HEAD. Before cleanup, `app.py` already imported `math_mentor.py`. Neither file imported the deleted engine, loader, translation, or styling modules.

The repository had three implementations/reference layers:

1. **Active Streamlit app:** `app.py` -> `math_mentor.py` -> SymPy/scikit-learn/SQLite.
2. **Older regional implementation:** `ai_engine.py`, `problem_bank.py`, regional JSON, translations, styling, and a small companion notebook. The old engine tests and that companion notebook used these modules.
3. **React UI reference:** `ui_source/`, with its own demonstration problem bank, mock classifier functions, and in-memory mastery model. It is not wired to Python.

The cleanup removed layer 2. It did not implement layer 1 anew, or connect layer 3 to Python. Saying only that “country stuff was removed” understated the scope: real generic math functions, English text, and 22 problems were also deleted from the older implementation.

The active app still works in the tested workflows. That does not mean every removed function has an identical replacement or that the entire notebook has complete feature parity with the app.

## 2. Every file changed during cleanup

| File | Action | What changed and consequence |
|---|---|---|
| `ai_engine.py` | Deleted, 430 lines | Removed the older parser, equivalence checker, error models, evaluator, scoring, feedback bandit, recommender, and tabular results. These were real functions, but the active app did not call them. The active backend already has separate implementations. Old imports of this module will now fail. |
| `problem_bank.py` | Deleted, 37 lines | Removed `DATA_PATH`, `load_problem_bank()`, `stage_key()`, and `filter_problems()`. The old JSON loading and school/lyceum/university plus grade-range filtering API is gone. The active backend uses its own in-code bank and level/weakness scoring instead. |
| `data/problem_bank.json` | Deleted, 626 lines | Removed 22 multilingual problems, including their English titles/prompts/hints, solutions, difficulty, stages, and grade ranges. They were not added to the retained bank. The running app already used a separate six-problem bank, so its available set did not change. |
| `data/error_examples.csv` | Deleted, 7 lines | Removed a header and six English diagnostic examples. No Python source loaded this CSV; the old engine had inline training rows and the active engine builds its own synthetic dataset. It was useful reference data but not a runtime dependency. |
| `localization.py` | Deleted, 184 lines | Removed `LANGUAGES`, `TEXT`, `REGIONS`, `STAGES`, `LEVELS`, and `tr()`: three-language text lookup, 14 regional entries, education-stage labels, and level labels. English entries were removed along with the other translations. Active English copy and levels already live in the app/backend. |
| `ui_copy.py` | Deleted, 412 lines | Removed `COPY` and `ui()`, including all three languages, profile labels, branding, and notices. Active page text is already embedded in `app.py`. |
| `ui_theme.py` | Deleted, 563 lines | Removed `inject_ui_css()`, `page_header()`, `section_heading()`, and `render_footer()`. This included generic CSS as well as regional branding. `app.py` already owns its own CSS, headers, and footer. |
| `notebooks/AI_Math_Mentor_Uzbekistan_Colab.ipynb` | Deleted, 96 serialized lines | Removed a six-cell companion that installed dependencies, imported the old engine and loader, and demonstrated one regional problem. This was not the large uploaded backend notebook. |
| `README.md` | Updated | Added English-only/profile scope and teacher-support purpose; identified the active six-problem backend and the separate React demo; corrected the claim that React source was completely unmodified. |
| `UI_MIGRATION.md` | Updated | Corrected “exact original” to acknowledge pre-existing project-credit and README changes in the React reference. Those React edits were not made during this cleanup. |
| `docs/ARCHITECTURE.md` | Rewritten | Removed the obsolete regional dependency diagram, country controls, inaccurate session-only storage description, and old extension-point list. Described the actual backend, SQLite, feedback state, and prototype limits. |
| `docs/UI_INTEGRATION.md` | Rewritten | Removed regional adaptation instructions and references to deleted theme/copy modules. Described the active Streamlit design adaptation and the separate React reference. |
| `tests/test_engine.py` | Updated | Replaced imports/tests of the old engine and the regional-ID/grade-filter assertions with tests of the active engine: equivalence, all six reference solutions, an incorrect step, profile fields, database records, learner separation, mastery, and recommendation ranking. |
| `tests/test_app_smoke.py` | Updated | Preserved existing page tests. Added a test checking profile labels, analyzing a linear equation through the UI, checking the resulting score/recommendation/profile, and opening Mastery. |

Original cleanup total: 14 tracked files changed, 118 lines added, 2,497 removed. This audit document is an additional documentation file created in response to the request for a full explanation.

## 3. Removed names and surviving functionality

These are functional counterparts that already existed, not renames or guarantees of identical behavior.

| Deleted name(s) | Where the corresponding responsibility remains |
|---|---|
| `StepResult`, `StepResult.as_dict()` | `StepEvaluation` plus dataclass serialization in `math_mentor.py` |
| `_normalize()`, `_local_dict()`, `parse_math()` | `clean_math_text()`, `LOCAL_DICT`, `parse_statement()` |
| `_is_zero()`, `mathematically_equivalent()` | `symbolic_equivalent()`, `equation_residual()`, `_safe_solution_set()` |
| `TRAINING_ROWS`, `train_error_models()` | `build_synthetic_error_dataset()`, `ERROR_CLASSIFIER`, `DNN_VECTORIZER`, `DNN_CLASSIFIER` |
| `_numeric_only()`, `_rule_diagnosis()`, `classify_error()` | `extract_numbers()`, `has_sign_pattern_difference()`, `classify_incorrect_step()`, `ml_error_prediction()`, `dnn_error_prediction()`; heuristics differ |
| `_styled_feedback()`, `FEEDBACK`, `STYLE_PREFIX`, `LABEL_TEXT` | `create_feedback()` and English display formatting |
| `evaluate_steps()` | `evaluate_solution_steps()` |
| `score_results()` | `solution_score()` |
| `choose_feedback_style()`, `update_feedback_bandit()` | `FeedbackBandit.choose()`, `FeedbackBandit.update()`, `record_feedback_reward()` |
| `recommend_problem()` | `recommend_next_problem()` |
| `results_dataframe()` | `evaluations_to_frame()` and app review rendering |
| `load_problem_bank()`, `DATA_PATH` | In-code `PROBLEM_BANK` and `PROBLEMS_BY_ID`; there is no retained JSON-loader API |
| `stage_key()`, `filter_problems()` | No identical stage/grade filter remains. `assign_initial_problems()` and `recommend_next_problem()` score the active bank by learning needs. |
| `tr()`, `ui()` and translation dictionaries | English strings directly in `app.py` and `math_mentor.py`; no translation lookup remains |
| `inject_ui_css()`, `page_header()`, `section_heading()`, old `render_footer()` | `app.py` has `inject_css()`, `render_page_header()`, inline section markup, and its own `render_footer()` |

Examples of behavior differences between the two pre-existing engines:

- Old scoring weighted correctness 80% and submitted-length completeness 20%. Active scoring weights correctness 65% and distinct expected-step coverage 35%.
- The old result type explicitly distinguished repeated steps and skipped-step status strings. The active result type records skipped expected steps and classifies unmatched steps; it does not expose the same status API.
- The old equivalence checker could match an equation such as `x=5` against the expression `5`. The active checker rejects equation/expression mismatches.
- Old feedback styles were `socratic`, `concise`, and `worked`. Active styles are `socratic`, `concise_hint`, and `worked_example`.
- Old recommendations used a different same-topic/nearby-difficulty rule. Active recommendations use topic levels, stored weaknesses, concept errors, and an unattempted-problem bonus.

These differences were already present before cleanup. They would matter if someone tried to use the removed engine directly or expected drop-in compatibility.

## 4. Profiles were retained

`StudentProfile` remains at `math_mentor.py:43`, with:

- `student_id`
- `display_name`
- `grade_band`
- `current_levels`
- `preferred_feedback`
- `accessibility_notes`

`app.py:85` constructs it in `current_profile()`. `render_settings()` presents the learner settings. `upsert_student()` saves profile data when an attempt is recorded. `record_attempt()` saves the attempt and its steps. `load_student_history()` and `weakness_summary()` drive progress displays.

The removed localization files contained profile *labels*, country/region lists, and education-stage labels. They did not contain the active `StudentProfile` class.

Existing limitation: “School / class” is a session-state field in the UI but is not included in `StudentProfile` or its database columns. Display names determine learner IDs; there is no account authentication. These behaviors were not introduced by cleanup.

## 5. The three problem banks

| Bank | Before | After |
|---|---|---|
| `math_mentor.py::PROBLEM_BANK` | Active Python app, six problems | Unchanged |
| `data/problem_bank.json` | Separate regional bank, 22 problems | Deleted, including its English content |
| `ui_source/src/data/problemBank.ts` | React demonstration bank | Unchanged; separate from Python |

Retained Python problem IDs: `ARITH-001`, `ALG-LIN-001`, `ALG-QUAD-001`, `CALC-DERIV-001`, `PROB-001`, `DE-EXP-001`. They cover fractions, linear equations, quadratic equations, differentiation, probability, and differential equations.

The deleted 22-problem bank also had geometry, trigonometry, sequences, combinatorics, linear algebra, statistics, and other topics. Deleting its country fields alone would have allowed much of that content to be retained after conversion. I chose removal because it belonged to the separate implementation and the requested reference backend used six problems; it was not technically necessary to delete every English problem to make the app English-only. The old bank is recoverable from Git HEAD. It has not been restored or merged as part of this audit.

## 6. Current runtime structure

```text
Browser -> app.py (Streamlit)
             |
             +-> learner settings -> StudentProfile
             +-> choose problem -> PROBLEM_BANK / PROBLEMS_BY_ID
             +-> submit steps -> run_mentor_attempt()
                                    |
                                    +-> parse and compare steps
                                    +-> diagnose errors
                                    +-> score and generate feedback
                                    +-> record profile/attempt/steps in SQLite
                                    +-> summarize weaknesses and recommend practice
             +-> review / Mastery / report and history downloads

Separate reference: ui_source/index.html -> src/main.tsx -> src/App.tsx
                      -> React pages -> browser-side demo math/mastery modules
                      (no Python API connection)
```

`math_mentor.py` trains its small diagnostic models and initializes its SQLite database when imported. Its database and export directory are relative to the working directory. That explains why tests can create local runtime files without changing tracked application source.

## 7. Verification and limits

The latest rerun passed all 13 automated tests in 15.26 seconds. It covers six expected solution paths, equation/fraction equivalence, an incorrect step, persistence, another learner having no history, mastery data, recommendation ranking, all five Streamlit pages, and a submit-to-Mastery UI workflow.

This establishes that the active app does not need the deleted modules for those paths. It is not comprehensive mathematical validation, a React build test, a deployed-server test, or proof of identical behavior to the deleted engine. Feedback reward clicks and every report-download payload were not individually tested by this suite.

The root Colab notebook code cells were previously compared with the uploaded reference and matched. The active Python module is an adaptation; this audit does not claim every notebook-only feature has been migrated. The React reference has mock logistic/DNN functions, an in-memory placeholder mastery catalogue, a simulated contact submission, and account placeholders. Those limitations predate cleanup.

## 8. Complete first-party file inventory

Every remaining tracked first-party file is listed below. Deleted paths are covered in section 2. Generated dependencies and caches are described separately rather than listing thousands of third-party files.

| File | Purpose |
|---|---|
| `.github/workflows/tests.yml` | GitHub Actions: install development requirements and run pytest on pushes/PRs with Python 3.12. |
| `.gitignore` | Keeps environments, caches, SQLite files, secrets, exports, and frontend build output out of Git. |
| `.streamlit/config.toml` | Streamlit dark palette, headless server, and disabled usage-stat collection. |
| `Anchit_Nayak_AI_Math_Mentor_App_Colab_Prototype.ipynb` | Full original backend notebook: data models, six problems, checking, models, storage, mastery, recommendations, feedback, exports, and optional Gradio demo. Preserved. |
| `CREDITS.md` | Author/advisor attribution and project links. |
| `DEPLOYMENT.md` | Instructions for deploying app.py on Streamlit Community Cloud. |
| `LICENSE` | MIT license text. |
| `README.md` | Project overview, setup, active workflow, source references, and limitations. |
| `UI_MIGRATION.md` | Summary of how the React design was adapted into Streamlit. |
| `app.py` | Active UI entry point: five pages, CSS, session state, profile controls, backend calls, feedback ratings, and downloads. |
| `assets/favicon.ico` | Retained root icon asset; no direct reference found in app.py. |
| `assets/placeholder.svg` | Retained root placeholder graphic; no direct reference found in app.py. |
| `docs/ARCHITECTURE.md` | Documentation of the active backend, workflow, storage, and limitations. |
| `docs/UI_INTEGRATION.md` | Explains Streamlit adaptation and the separate React reference. |
| `math_mentor.py` | Active backend: profile/problem models, bank, symbolic checker, diagnostic models, SQLite, feedback, mastery, recommendations, and report formatting. |
| `requirements-dev.txt` | Runtime dependencies plus pytest. |
| `requirements.txt` | Runtime Python dependencies: Streamlit, NumPy, pandas, SymPy, scikit-learn. |
| `runtime.txt` | Declares python-3.11; CI currently uses Python 3.12. |
| `tests/smoke_test.py` | Standalone main() smoke script for a successful linear-equation attempt and recommendation. Its main() is not run just by pytest collection. |
| `tests/test_app_smoke.py` | Streamlit AppTest coverage of pages, settings, and the submission-to-Mastery workflow. |
| `tests/test_engine.py` | Automated tests of the active backend, profiles, all six solutions, persistence, mastery, and recommendation ranking. |
| `ui_source/.gitignore` | Ignore rules for the React reference. |
| `ui_source/README.md` | React reference purpose, technology, and run instructions. |
| `ui_source/components.json` | shadcn/ui generator configuration and path aliases. |
| `ui_source/eslint.config.js` | JavaScript/TypeScript lint configuration. |
| `ui_source/index.html` | HTML document into which React mounts. |
| `ui_source/package.json` | Frontend scripts and runtime/build dependency declarations. |
| `ui_source/postcss.config.js` | CSS processing setup for Tailwind and Autoprefixer. |
| `ui_source/public/favicon.ico` | React site icon. |
| `ui_source/public/placeholder.svg` | React placeholder graphic. |
| `ui_source/public/robots.txt` | Crawler instructions for the React site. |
| `ui_source/roadmap.md` | Historical frontend checklist, including explicit notes that the backend integration is unfinished. |
| `ui_source/src/App.css` | Additional React app styles. |
| `ui_source/src/App.tsx` | Route table and shared providers/navigation/footer for the React app. |
| `ui_source/src/components/ContactForm.tsx` | Frontend contact form; simulates submission, with no real message delivery. |
| `ui_source/src/components/Footer.tsx` | Shared React footer and project information. |
| `ui_source/src/components/NavLink.tsx` | Navigation-link wrapper for active/pending route styling. |
| `ui_source/src/components/Navigation.tsx` | React site navigation. |
| `ui_source/src/components/ScrollToTop.tsx` | Resets browser scroll when the route changes. |
| `ui_source/src/components/ui/accordion.tsx` | Expandable stacked sections. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/alert-dialog.tsx` | Confirmation dialog. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/alert.tsx` | Inline status or warning panel. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/aspect-ratio.tsx` | Maintains content proportions. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/avatar.tsx` | User image/fallback. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/badge.tsx` | Small status label. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/breadcrumb.tsx` | Breadcrumb navigation. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/button.tsx` | Styled buttons. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/calendar.tsx` | Date-selection calendar. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/card.tsx` | Card layout sections. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/carousel.tsx` | Sliding content controls. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/chart.tsx` | Chart wrappers and theme helpers. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/checkbox.tsx` | Checkbox control. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/collapsible.tsx` | Show/hide content. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/command.tsx` | Searchable command menu. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/context-menu.tsx` | Right-click menu. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/dialog.tsx` | Modal window. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/drawer.tsx` | Drawer overlay. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/dropdown-menu.tsx` | Dropdown menu. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/form.tsx` | Form state/validation bindings. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/hover-card.tsx` | Hover-triggered information. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/input-otp.tsx` | Segmented code input. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/input.tsx` | Text input. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/label.tsx` | Form label. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/menubar.tsx` | Menu bar. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/navigation-menu.tsx` | Navigation menu. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/pagination.tsx` | Page navigation controls. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/popover.tsx` | Anchored floating panel. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/progress.tsx` | Progress indicator. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/radio-group.tsx` | Single-choice controls. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/resizable.tsx` | Resizable panels. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/scroll-area.tsx` | Styled scrolling container. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/select.tsx` | Selection dropdown. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/separator.tsx` | Visual divider. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/sheet.tsx` | Side-panel dialog. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/sidebar.tsx` | Sidebar layout/navigation controls. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/skeleton.tsx` | Loading placeholder. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/slider.tsx` | Numeric range control. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/sonner.tsx` | Sonner toast integration. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/switch.tsx` | On/off toggle. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/table.tsx` | Styled table elements. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/tabs.tsx` | Tabbed panels. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/textarea.tsx` | Multiline text input. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/toast.tsx` | Toast primitives. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/toaster.tsx` | Toast rendering host. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/toggle-group.tsx` | Grouped toggle controls. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/toggle.tsx` | Toggle button. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/tooltip.tsx` | Hover/focus help. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/components/ui/use-toast.ts` | Re-export of the shared toast hook. Reusable React UI component/helper; not Python backend logic. |
| `ui_source/src/contexts/AppearanceContext.tsx` | Dark/light theme state persisted to browser localStorage. |
| `ui_source/src/data/mastery.ts` | Placeholder topic/concept catalogue and in-memory mastery updates; no SQLite/API connection. |
| `ui_source/src/data/problemBank.ts` | Independent demonstration problem definitions and selection helpers. |
| `ui_source/src/hooks/use-mobile.tsx` | Responsive mobile-width detection hook. |
| `ui_source/src/hooks/use-toast.ts` | Toast notification state and helper hook. |
| `ui_source/src/hooks/useScrollToTop.tsx` | Hook form of route-change scroll reset. |
| `ui_source/src/index.css` | Global CSS, typography, design tokens, and Tailwind layers. |
| `ui_source/src/lib/analyzeSolution.ts` | Browser-side string comparison heuristics and mock classifier responses; not the Python symbolic engine. |
| `ui_source/src/lib/utils.ts` | cn() helper for combining class names and resolving Tailwind conflicts. |
| `ui_source/src/main.tsx` | Mounts React and loads global styles. |
| `ui_source/src/pages/About.tsx` | Project background and contact page. |
| `ui_source/src/pages/Analyze.tsx` | React solution-entry and demonstration feedback workspace. |
| `ui_source/src/pages/Index.tsx` | Landing page. |
| `ui_source/src/pages/Mastery.tsx` | Displays placeholder mastery topics/concepts and level selectors. |
| `ui_source/src/pages/NotFound.tsx` | Fallback route for unknown URLs. |
| `ui_source/src/pages/Settings.tsx` | Theme controls and placeholder account fields; not a working account system. |
| `ui_source/src/tailwind.config.lov.json` | Design-tool theme configuration snapshot. |
| `ui_source/src/vite-env.d.ts` | Vite TypeScript environment declarations. |
| `ui_source/tailwind.config.ts` | Tailwind colors, typography, theme extensions, and plugins. |
| `ui_source/tsconfig.app.json` | TypeScript compiler settings for browser application code. |
| `ui_source/tsconfig.json` | Top-level TypeScript project references and path aliases. |
| `ui_source/tsconfig.node.json` | TypeScript compiler settings for build-tool configuration. |
| `ui_source/vite.config.ts` | Vite React/SWC build and development-server configuration, @ alias, and development tagging plugin. |

## 9. Local/generated folders and files

| Path | Explanation |
|---|---|
| `.git/` | Existing Git history and index. Deleted source files remain recoverable from HEAD. No history was rewritten. |
| `.venv/` | Local Python environment created to run verification. Includes third-party packages installed from requirements-dev.txt; ignored by Git. |
| `__pycache__/`, `tests/__pycache__/` | Generated Python bytecode caches. Not source. |
| `.test_tmp/` | Temporary database directory from the latest test rerun. |
| `ai_math_mentor.db` | Local SQLite runtime database. The latest UI test can create a demo learner attempt. This is generated data, not a source change. |
| `ai_math_mentor_exports/` | Runtime export directory created by backend import; ignored by Git. |
| `data/` | Now empty after the older CSV and JSON were deleted. Active problems are in math_mentor.py. |
| `notebooks/` | Now empty after the short regional notebook was deleted. The original full notebook remains at the repository root. |

The first test run's disposable database and temporary directory were removed. The later verification rerun recreated runtime artifacts. The uploaded files in Downloads were only read and were never modified.

## 10. Active Python symbol inventory

For locating code, these are the actual top-level classes and functions that remain. This inventory is generated from Python syntax trees, not inferred from file names.

### app.py

| Symbol | Line |
|---|---|
| `initialize_state` | 49 |
| `safe_student_id` | 71 |
| `esc` | 76 |
| `go_to` | 80 |
| `current_profile` | 85 |
| `inject_css` | 96 |
| `render_navigation` | 280 |
| `render_page_header` | 302 |
| `render_profile_strip` | 318 |
| `render_home` | 335 |
| `render_review` | 420 |
| `render_analyze` | 524 |
| `weighted_topic_metrics` | 619 |
| `render_mastery` | 632 |
| `workflow_html` | 706 |
| `render_about` | 724 |
| `render_settings` | 797 |
| `render_footer` | 855 |

### math_mentor.py

| Symbol | Line |
|---|---|
| `StudentProfile` | 43 |
| `ExpectedStep` | 53 |
| `MathProblem` | 60 |
| `normalize_level` | 179 |
| `assign_initial_problems` | 187 |
| `clean_math_text` | 220 |
| `parse_statement` | 230 |
| `equation_residual` | 242 |
| `_safe_solution_set` | 248 |
| `symbolic_equivalent` | 256 |
| `build_synthetic_error_dataset` | 290 |
| `StepEvaluation` | 370 |
| `extract_numbers` | 384 |
| `has_sign_pattern_difference` | 398 |
| `build_classifier_text` | 406 |
| `ml_error_prediction` | 410 |
| `dnn_error_prediction` | 417 |
| `classify_incorrect_step` | 425 |
| `evaluate_solution_steps` | 450 |
| `solution_score` | 507 |
| `evaluations_to_frame` | 518 |
| `get_connection` | 534 |
| `initialize_database` | 540 |
| `upsert_student` | 569 |
| `record_attempt` | 582 |
| `load_student_history` | 602 |
| `weakness_summary` | 613 |
| `recommend_next_problem` | 626 |
| `FeedbackBandit` | 656 |
| `FeedbackBandit.__init__` | 657 |
| `FeedbackBandit.choose` | 662 |
| `FeedbackBandit.update` | 669 |
| `create_feedback` | 680 |
| `record_feedback_reward` | 716 |
| `run_mentor_attempt` | 725 |
| `report_to_markdown` | 754 |

