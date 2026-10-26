# Consistency audit - October 26, 2026

## Scope and evidence

Audited the actual workspace `C:\Users\anchi\OneDrive\Documents\GitHub\AI_Math_Mentor`,
including current Python entry points, auth/storage modules, SQL migration,
offline/live test source, dependency files, runtime/Streamlit configuration,
GitHub workflow, maintained documentation, root notebook and React reference.
Applicable AGENTS.md files were not found. Existing unstaged ownership fixes
were preserved. No substitute checkout was used.

Only the tracked placeholder secrets template and configuration-reading code
were inspected. Real `secrets.toml`, untracked secrets copies, learner databases,
exports, credentials and hosted settings were not read. Generated environments,
caches and scratch test artifacts were excluded from source-content searches.

| Confirmed discrepancy | Correction |
|---|---|
| Old public app address in code, product links and deployment/counter guides | Current references use https://math-mentorai.streamlit.app/; the public URL template agrees. The current fork remains Greenstar22/AI_Math_Mentor. |
| SQLite/name-based identity/no-account descriptions | README, architecture, integration and setup guides describe authenticated UUIDs, Supabase PostgreSQL accounts, session-only guests and explicit legacy SQLite helpers. |
| Six/fifty-problem and five/six-page claims mixed together | Current source is documented as 50 problems, five topics, 25 concepts, 212 reference lines and 70 skill labels, with six pages including Account. Historical six-problem/five-page material is labeled historical. |
| Proof-checking/calibrated-bank/confidence claims exceeded implementation evidence | Current copy distinguishes reference matching from preceding-line equivalence, author-rated difficulty from empirical calibration, and heuristic confidence/mastery from validated assessment. |
| Documentation treated a synthetic demonstration MLP as unspecified general AI | Architecture documents the actual corpus, splits, configured feature caps, `(64,32)` hidden layers and locally measured dimensions/parameter count, without classroom-accuracy or performance claims. |
| Internal spacing affected reference credit | With owner authorization, token-based matching now ignores formatting whitespace, retains token boundaries and written operations, and does not use symbolic equivalence to align reference steps. |
| Python 3.11 runtime file conflicted with 3.12 CI | With owner authorization, `runtime.txt` now says `python-3.12`; maintained setup/deployment docs target Python 3.12. No dependency upgrades. |
| Contact demo reported a sent message, or implied a working contact service | React contact copy says no message was sent. Streamlit copy describes validation in the current app session, with no contact message stored in learning history. |
| React placeholders and earlier Linux-backend plans could be mistaken for current accounts | README, metadata, navigation and affected demo pages identify the separate design demo; its archived roadmap is labeled historical. No React backend integration was added. |
| Account guide ambiguities about credentials, save certainty and live testing | Clarified no dedicated learning-table credential columns, possible personal data in free text, uncertain commit acknowledgments, and the separately gated administrator-key deletion test. |
| Offline test secrets replacement did not cover visitor-counter environment fallback | Tests now also remove the three visitor-counter environment overrides during each offline test, avoiding accidental external counter use. |

## Owner decisions and deliberately unchanged behavior

All clarification questions raised during this audit were answered:

1. **Restricted parsing is deferred.** `parse_statement` still calls SymPy
   `parse_expr`; normalization is not a sandbox. No adversarial execution
   payload was run. [SymPy's documentation](https://docs.sympy.org/latest/modules/parsing.html)
   describes the unsanitized-input risk. The owner wants restricted parsing
   later, but explicitly requested leaving it unchanged for this audit.
2. **Only formatting-insensitive reference matching changes.** Different
   algebraic stages remain distinct. Existing additional-step/carried-error
   credit, cursor advancement, grading labels, formulas, mastery and ranking
   behavior remain. No symbolic-equivalence matching of references was added.
3. **Counter reset behavior is retained.** Account establishment, logout,
   deletion and new-guest resets can clear the counter flag and cause another
   attempted increment in one browser session. Current descriptions now state
   this instead of promising strict browser-session uniqueness.
4. **Python 3.12 is authoritative for supported/tested source.** CI already
   used it, and runtime.txt was aligned without changing its syntax.

The bank, stable problem/skill IDs, Auth UUID identity rules, storage contracts,
RLS/RPC schema, data compatibility, dependency constraints, credits, license,
upstream provenance and Git remotes were not redesigned. Historical notebook
code cells, saved outputs and metadata are unchanged; only a historical-scope
notice was added to its first Markdown cell.

## Verification performed

- Python **3.12.14**: `python -m pytest tests -q -m "not live"` passed
  **164 tests**, with **5 live tests deselected**. Real credentials were not used.
- The focused engine/Streamlit run passed **121 tests**, including formatting
  variants for all 50 references. Tests distinguish equivalent equation stages,
  verify token boundaries, and reject using `symbolic_equivalent` for reference
  matching. Existing i/I and Integral/Limit tests pass.
- Offline migration SQL/PL/pgSQL parsing passed as part of the suite. This is
  syntax checking, not database execution or RLS/transaction/cascade verification.
- Maintained relative Markdown file links, React local imports and entry paths
  were checked. The bank, parser behavior outside matching, score/mastery/ranking
  functions, account/storage modules, migration, dependencies and license were
  compared with the unchanged source baseline where applicable.
- Targeted searches covered old app URLs, owner references, storage/identity
  assumptions, counts, confidence/model claims, Python versions and placeholder
  features. Remaining SQLite/name-hash/six-problem descriptions belong to
  explicitly labeled historical material or legacy APIs. The only remaining
  original-owner project link is intentional fork provenance in CREDITS.md.
- Read-only public HEAD checks returned **200** for the fork and upstream
  repository URLs. The corrected Streamlit URL responded with **303**; the
  final page/deployed behavior was not exercised. No app browser/WebSocket
  session was opened to generate a visit or run learning operations.

## Manual follow-up and limits

- Check the hosted app's actual Python interpreter. Community Cloud chooses it
  in deployment **Advanced settings**; `runtime.txt` alone does not establish
  the running version. See the [official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy).
  No hosted version change or deployment was performed.
- Privately verify the app's repository/branch/entry point, public URL metadata
  and `[app].public_url`. The latter is descriptive and currently unused by
  runtime link generation; `LIVE_APP_URL` in app.py supplies the visible link.
- Verify Supabase migration status, Confirm email OFF, password minimum 12 and
  the required private configuration using ACCOUNTS_SETUP.md. Hosted RLS,
  transactional retries, trigger/backfill behavior and deletion cascades remain
  live checks, not conclusions from mocks or SQL parsing.
- Verify `VISIT_COUNTER_REPO`, `VISIT_COUNTER_BRANCH` and token scope on the fork.
  Existing secret/environment overrides can supersede the source defaults.
  Preserve existing counter history; no external counter was modified.
- The parser remains a deferred security issue for untrusted public input.
  Known grading/domain/branch/alternative-method limitations are documented;
  passing reference tests does not demonstrate comprehensive mathematical
  accuracy. No learner-outcome, performance, fairness or environmental-impact
  study was performed.
- The React reference has no installed node_modules in this workspace. Local
  imports and text changes were inspected; no npm install, build, lint or
  browser UI test was run. The historical Colab notebook was not executed.

This is a source consistency audit within these limits, not a claim that every
inconsistency or security issue has been found. Nothing was staged, committed,
pushed, branched or deployed; no hosted settings, migrations, learner records,
external counter resources or remotes were modified.
