# MathMentor AI

**Author:** Anchit Nayak  
**Advisor:** Dr. Qingyang Xiao

MathMentor AI is an educational Streamlit prototype for reviewing a learner's written mathematical steps, suggesting likely error categories, recording practice, estimating skill mastery, and recommending another problem. Its checker has reference-path and symbolic-comparison limitations; it is not a proof verifier or a formal assessment system.

- **Current repository:** https://github.com/Greenstar22/AI_Math_Mentor
- **Public app:** https://math-mentorai.streamlit.app/
- **Fork provenance and retained credits:** [CREDITS.md](CREDITS.md#fork-provenance)

The current source provides six pages: Home, Analyze, Mastery, About, Settings, and Account. The interface, reference problems, and generated feedback are English-only. Profiles have no dedicated country, region, or language settings.

## Accounts, guests, and storage

The app starts in guest mode. A random `guest_` UUID identifies that Streamlit session; preferences, drafts, attempts, evaluations, and feedback ratings stay in session memory. Losing or resetting the session can discard this work. Guests do not need an API key, an anonymous Supabase account, or a local progress database.

Optional accounts use Supabase email/password authentication. Identity is the server-validated `auth.users.id` UUID, never a display name or email hash. Display names are editable and nonunique. With the migration and secrets configured, account profiles and saved learning records live in Supabase PostgreSQL. Mastery, recommendations, history, feedback selection, and exports use the selected owner's saved history. Legacy SQLite helpers remain for compatibility and tests, but normal guest/account flows do not use them or automatically migrate old records.

For this prototype, **Confirm email must be OFF**, **passwords must have at least 12 characters**, **password recovery is unavailable**, and **there is no Remember me**. Email ownership is not verified. Tokens and authenticated clients live only in Streamlit session memory; signing in again can recover saved cloud history, not discarded guest work or unsaved analyses. Missing Supabase configuration leaves guest mode usable.

After login, existing guest attempts require an explicit import-or-discard choice. New learning submissions are blocked until that choice is resolved. Failed account saves retain the original attempt payload for retry; the app does not intentionally add pending work to saved mastery. History reopens saved problem snapshots, verdicts, and feedback without regrading them. Account deletion requires DELETE confirmation and password reauthentication, and uses an isolated server-side administrator client. Hosted privacy, transaction, and cascade behavior require live verification; offline tests alone do not establish those guarantees.

See [ACCOUNTS_SETUP.md](docs/ACCOUNTS_SETUP.md) for the migration, configuration, session limits, and opt-in live tests.

## Problem bank and input

`math_mentor.py` contains **50 unique problems**: five topics, five concepts per topic, and two problems (`001` and `002`) per concept. Every pair has different difficulty ratings; `002` is not always harder. Difficulty 1/2/3 corresponds to beginner/intermediate/advanced selection targets and is an author-assigned rating, not a calibrated student-performance measure.

The topics are Algebra 1, Geometry, Algebra 2, Precalculus, and Calculus. Problems carry prompts, grade bands, expected steps, consolidated skill labels, explanations, hints, and final answers. There are 212 reference lines and 70 distinct skill labels. `DEFAULT_STEPS` in `app.py` derives the example input directly from those reference lines.

Enter one expression or equation per line, using explicit multiplication (`2*x`), powers (`x**2` or `x^2`), and radians for trigonometric functions. Functions include `sqrt`, `sin`, `cos`, `tan`, `log`, `exp`, `Derivative`, `Integral`, and `Limit`. Both `i` and `I` represent the imaginary unit; their reference matching is normalized without changing `Integral` or `Limit`.

Parsing support does not guarantee reference credit for every equivalent spelling. Reference matching now ignores whitespace between tokens while preserving the written operations and token boundaries; it does not simplify equivalent equations into the same stage. Keep original domain restrictions even after cancellation. Natural-language proofs, arbitrary problem entry, diagram interpretation, and general branch-aware proof checking are not implemented.

## Checking, scores, and diagnostic models

The evaluator first looks forward for a matching reference line. If no match is found, it can accept symbolic equivalence with the preceding submitted line as a `valid additional step` or a `carry-on error` after an earlier deviation. Both currently count as correct submitted steps, but neither adds reference coverage. This does not establish that a carried error solves the original problem or that an inferred skill was demonstrated.

The unchanged `v1` overall score is `100 * (0.65 * step_accuracy + 0.35 * coverage)`. Coverage counts distinct matched reference indices. Mastery is a heuristic grouped by topic and skill, not a validated proficiency measure; recommendations rank the bank using stated topic levels, observed errors, skill overlap, and a small bonus for unattempted problems.

Diagnostic rules are supplemented by TF-IDF plus logistic regression and a scikit-learn MLP with hidden layers `(64, 32)`. They train at module import on 252 synthetic template examples, split into 189 training and 63 held-out examples; the MLP also reserves part of its training split for early stopping. These are local demonstration classifiers, not an LLM or a model trained on real learner outcomes. Displayed confidence combines heuristic constants and model outputs and is not a calibrated probability of mathematical correctness. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for formulas, model dimensions, and limitations.

The current parser uses SymPy `parse_expr`; input normalization is not a security sandbox. [SymPy's parsing documentation](https://docs.sympy.org/latest/modules/parsing.html) warns about evaluating unsanitized input. Parser hardening is deferred at the owner's request; account RLS does not make the Python parser safe for untrusted public input.

## Run locally

Run from the repository root using **Python 3.12**, the supported and tested project target. `runtime.txt` and CI both specify 3.12. Streamlit Community Cloud selects its actual Python version through deployment **Advanced settings**; `runtime.txt` alone does not establish the hosted version. No dependency upgrade is part of this alignment.

```bash
python3.12 -m venv .venv
# Windows alternative: py -3.12 -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

For offline development checks:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q -m "not live"
```

Runtime dependencies are Streamlit, NumPy, pandas, SymPy, scikit-learn, and pinned `supabase==2.33.0`. Development requirements add pytest and `pglast==7.21` for SQL syntax checks. Hosted migrations, real account tests, authentication emails, and account deletion are not part of the offline command.

## Setup and deployment

The Streamlit entry point is `app.py` in this repository. [DEPLOYMENT.md](DEPLOYMENT.md) covers repository/branch selection and the public URL. Accounts require the manually applied SQL migration and `[supabase]` URL/publishable-key settings described in [ACCOUNTS_SETUP.md](docs/ACCOUNTS_SETUP.md). The administrator secret is used only for account deletion. Do not put real credentials in tracked files.

The placeholder template is [.streamlit/secrets.example.toml](.streamlit/secrets.example.toml); the real `.streamlit/secrets.toml` must remain ignored. `[app].public_url` is descriptive configuration only: the displayed app link currently comes from `LIVE_APP_URL` in `app.py`, and authentication uses no email redirects.

The optional visit counter is separate from learner progress. It stores an aggregate integer at `data/visit_counter.json` on the configured GitHub storage branch, defaulting to `visitor-stats` in `Greenstar22/AI_Math_Mentor`. `VISIT_COUNTER_GITHUB_TOKEN` needs Contents read/write access to the fork; `VISIT_COUNTER_REPO` and `VISIT_COUNTER_BRANCH` can override defaults through Streamlit secrets or environment variables. Verify that the branch and file exist in the fork; do not recreate an existing counter branch or reset its total. See [VISITOR_COUNTER_SETUP.md](VISITOR_COUNTER_SETUP.md).

No token means the counter is unavailable/setup-required, not a fabricated live zero. Network failures and ambiguous writes can miss increments, and this does not measure unique humans. Current account/guest state resets also clear the counter's attempted flag, so another increment can occur within one browser session; that counting behavior is intentionally retained for now.

## Maintained source and historical references

| Path | Role |
|---|---|
| `app.py`, `account_ui.py` | Current Streamlit pages, forms, and session transitions |
| `auth_service.py` | Validated authentication, refresh, local-scope logout, isolated deletion |
| `progress_store.py`, `supabase_store.py` | Guest memory, cloud storage, immutable attempt payloads, history adapters |
| `math_mentor.py` | Reviewed bank, parser/checker, synthetic diagnostic models, scoring, mastery, recommendations; explicit legacy SQLite helpers |
| `visit_counter.py` | Separate GitHub-backed aggregate counter |
| `supabase/migrations/202610260001_accounts.sql` | Learning schema, profile triggers, RLS, ownership constraints, transactional RPCs |
| `tests/` | Offline engine, store, authentication, counter, and Streamlit checks; opt-in `tests/live/` |
| `ui_source/` | Independent React design/demo, not the deployed frontend or account implementation |
| `Anchit_Nayak_AI_Math_Mentor_App_Colab_Prototype.ipynb` | Historical six-problem SQLite/optional-Gradio prototype; not synchronized with the current bank or accounts |
| `docs/CLEANUP_AUDIT.md` | Historical cleanup report, not a current architecture or test-results statement |

The React demo uses separate problems, mocked diagnostic models, an in-memory mastery catalogue, browser-local appearance preferences, and account placeholders. Its contact form simulates submission. The current Streamlit About contact form also only validates locally; it does not send a message. Neither is a working contact service.

Current limitations and deferred work are recorded in [CONSISTENCY_AUDIT.md](docs/CONSISTENCY_AUDIT.md). There is no claim of classroom-calibrated accuracy, comprehensive mathematical correctness, measured environmental benefit, production security, or completed hosted verification.
