# MathMentor AI

**Author:** Anchit Nayak  
**Advisor:** Dr. Qingyang Xiao

MathMentor AI is a Streamlit Community Cloud-ready educational prototype that reviews a learner's mathematical solution one step at a time. It validates mathematical transformations, diagnoses likely error types, explains how to repair the first miss, tracks mastery, and recommends targeted next practice.

- **GitHub:** https://github.com/qxiao2ub/AI_Math_Mentor
- **Live app:** https://math-ai-mentor.streamlit.app/

## UI migration

The attached React, TypeScript, Tailwind CSS, shadcn/ui, and Framer Motion design was migrated into a native Streamlit experience. The exact front-end source is preserved under `ui_source/`; the deployable Streamlit implementation is `app.py`.

The migrated interface includes:

- Home, Analyze, Mastery, About, and Settings views
- Dark-first black and cobalt visual system with an optional light mode
- Editorial hero typography and responsive card layouts
- Step-level feedback cards with error labels, confidence, expected steps, concepts, and mentor guidance
- Mastery bars, weakness analytics, attempt history, and topic-level settings
- Complete product workflow, technology stack, prototype boundaries, and project credits

## Core AI and mathematical workflow

1. Capture a learner profile and current topic levels.
2. Select a problem from the calibrated starter bank.
3. Parse each submitted step with SymPy.
4. Compare steps symbolically with the expected solution trajectory.
5. Diagnose likely errors using transparent rules, logistic regression, and a compact neural-network classifier.
6. Save attempts and step evaluations in SQLite.
7. Estimate weaknesses and concept mastery.
8. Select a feedback style through an epsilon-greedy contextual bandit.
9. Generate downloadable Markdown and JSON reports.
10. Recommend the next targeted problem.

## Repository structure

```text
.
|-- app.py
|-- math_mentor.py
|-- requirements.txt
|-- runtime.txt
|-- .streamlit/config.toml
|-- Anchit_Nayak_AI_Math_Mentor_App_Colab_Prototype.ipynb
|-- assets/
|-- tests/
|-- ui_source/
|-- UI_MIGRATION.md
|-- DEPLOYMENT.md
|-- LICENSE
`-- README.md
```

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

Upload the contents of this repository to GitHub, choose the repository in Streamlit Community Cloud, and set the main file path to `app.py`. No API key is required for the math tutoring functions. Persistent cumulative visit counting requires one private GitHub token and a separate GitHub branch; see `VISITOR_COUNTER_SETUP.md`.

## Prototype notes

- The starter problem bank is intentionally small and self-contained.
- The symbolic checker is the primary mathematical validator.
- ML and DNN components support error diagnosis and personalization; they do not independently establish mathematical truth.
- SQLite persistence on Streamlit Community Cloud is ephemeral and can reset during restarts or redeployments.
- A production version should add authentication, a managed database, a curated or licensed problem corpus, accessibility testing, privacy controls, child-safety review, educator oversight, and broader validation.

## Credits

- **Author:** Anchit Nayak
- **Advisor:** Dr. Qingyang Xiao

## Persistent cumulative app-visit counter (new)

**Visible on every view (Home, Analyze, Mastery, About, Settings)** at the top
and in the footer. It increments by one for each *new Streamlit session*, not
each navigation click or UI rerun. The integer is preserved in a **GitHub JSON
file on a separate `visitor-stats` branch**, so it survives normal Streamlit
Community Cloud restarts and redeployments without using a counter database.
No personal visitor information is collected for this counter.

### Important: one-time secret and branch are required

A live, never-reset-on-redeploy total **cannot be guaranteed** with Streamlit's
local ephemeral files alone. To activate persistent counts, follow the exact
instructions in **[VISITOR_COUNTER_SETUP.md](VISITOR_COUNTER_SETUP.md)**:

1. Upload the repo to `main` at https://github.com/qxiao2ub/AI_Math_Mentor.
2. Create a new GitHub branch named `visitor-stats` from `main` **once**.
3. Create a fine-grained GitHub token scoped to this one repository with
   Contents **read/write** access.
4. Add the token and the branch in Streamlit Community Cloud's **App settings
   → Secrets** using `.streamlit/secrets.example.toml` as the template.

**Never push a real token to GitHub.** Without the token, the app still runs,
but the badge will show **— / SETUP REQUIRED**, not a false permanent count.
An initial zero in the JSON is only a seed; a successful first session changes
it to 1, and the UI never shows zero as an active visit total. Do not delete or
recreate the `visitor-stats` branch after launching, as it holds the history.

The file-commit implementation retries GitHub SHA conflicts and is appropriate
for a small educational prototype. It may not capture every visit during
GitHub outages/rate limits, and it does not distinguish unique humans from
multiple browser sessions.
