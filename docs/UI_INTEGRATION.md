# UI integration notes

The retained `ui_source/` Vite/React demo uses TypeScript, Tailwind, shadcn/ui,
Framer Motion, React Router, Archivo Black and Inter. It has five design views:
Home, Analyze, Mastery, About and Settings. It is an independent reference,
not the frontend serving the current Streamlit app.

The current `app.py` adapts that design into native Streamlit controls and CSS,
and now has a sixth **Account** view. `account_ui.py` provides the account forms
and session transitions; `auth_service.py`, `progress_store.py` and
`supabase_store.py` implement validated Supabase identity, account storage and
session-only guest storage. `math_mentor.py` provides the reviewed 50-problem
bank, reference/transition checks, diagnostic models and calculation formulas.
It is not the active persistence boundary.

The migration retains the black/cobalt palette, dark/light controls, headings,
bordered cards, review panels and skill estimates. Native controls make this
a design adaptation, not a pixel-identical React rendering. Interface copy is
English, and learner settings contain no dedicated geographic or locale fields.

The React source has its own demonstration bank, mocked logistic/DNN functions,
in-memory mastery, browser-local appearance preferences, placeholder account
controls and simulated contact form. It does not call the Python checker,
Supabase Auth, or the cloud learning store. React confidence and estimated-error
constants are demonstration values, not measured classifier performance.

Running `npm run dev` from `ui_source/` opens only that demo. Making it the active
frontend would need an API integration and deployment decision; this audit does
not implement one. The root Colab notebook and old cleanup report are historical
references, not the current accounts or problem-bank implementation.

See [UI_MIGRATION.md](../UI_MIGRATION.md), [ARCHITECTURE.md](ARCHITECTURE.md),
and [ACCOUNTS_SETUP.md](ACCOUNTS_SETUP.md) for maintained behavior and setup.
