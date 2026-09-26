# Architecture

`app.py` provides the Home, Analyze, Mastery, About, and Settings views in
Streamlit. It contains the visual styling and English interface copy and calls
`math_mentor.py` for all mathematical analysis and learning records.

## Learning workflow

1. A learner sets a display name, grade band, topic levels, feedback preference,
   and optional learning notes.
2. The learner selects one of the six starter problems migrated from the Colab
   prototype and submits one mathematical step per line.
3. SymPy compares each step against the expected solution trajectory.
4. Rules, logistic regression, and a compact neural network assist error diagnosis.
5. The app records the attempt and step evaluations in SQLite, estimates concept
   mastery, and recommends practice using topic levels and observed weaknesses.
6. A contextual bandit selects feedback styles; learners can rate the feedback
   and download reports and history.

The interface, problem bank, and generated feedback are English-only. Profiles
contain learning needs and no geographic or locale settings.

## State and storage

Streamlit session state holds navigation, appearance, current learner settings,
and the displayed report. `ai_math_mentor.db` stores student records, attempts,
step evaluations, and feedback events. Feedback-bandit estimates are held in
memory. Server restarts on Streamlit Community Cloud can erase local storage.

The learner identifier is derived from the display name; this prototype has no
authenticated accounts. Mastery is a heuristic, and the small problem bank and
synthetic diagnostic training data retain the original prototype's limitations.

## Source references

The root Colab notebook preserves the uploaded backend's code cells.
`math_mentor.py` adapts that workflow for the app. `ui_source/` preserves the
uploaded React design with project-credit and README edits. Its demonstration
analysis and mastery data are not the running app's backend or learning records.
