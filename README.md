# MathMentor AI

**Author:** Anchit Nayak  
**Advisor:** Dr. Qingyang Xiao

MathMentor AI is a Streamlit Community Cloud-ready educational prototype that reviews a learner's mathematical solution one step at a time. It validates mathematical transformations, diagnoses likely error types, explains how to repair the first miss, tracks mastery, and recommends targeted next practice.

- **GitHub:** https://github.com/qxiao2ub/AI_Math_Mentor
- **Live app:** https://math-ai-mentor.streamlit.app/

The app supports teachers through step-level feedback, progress tracking, and targeted practice suggestions. The interface, feedback, and problems are English-only. Profiles contain no country, region, or language settings.

## UI migration

The attached React, TypeScript, Tailwind CSS, shadcn/ui, and Framer Motion design was migrated into a native Streamlit experience. The front-end source is preserved under `ui_source/` with project-credit and README edits; the deployable Streamlit implementation is `app.py`.

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

Upload the contents of this repository to GitHub, choose the repository in Streamlit Community Cloud, and set the main file path to `app.py`. No API key is required.

## Prototype notes

- `math_mentor.py` is the single app backend and owns the six-problem starter bank from the uploaded Colab prototype. The root notebook code cells match that reference.
- `ui_source/` is a standalone design reference with demo analysis and mastery data; it is not connected to the Python backend.

- The starter problem bank is intentionally small and self-contained.
- The symbolic checker is the primary mathematical validator.
- ML and DNN components support error diagnosis and personalization; they do not independently establish mathematical truth.
- SQLite persistence on Streamlit Community Cloud is ephemeral and can reset during restarts or redeployments.
- A production version should add authentication, a managed database, a curated or licensed problem corpus, accessibility testing, privacy controls, child-safety review, educator oversight, and broader validation.

## Credits

- **Author:** Anchit Nayak
- **Advisor:** Dr. Qingyang Xiao
