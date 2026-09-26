# UI Integration Notes

The supplied Vite/React UI uses TypeScript, Tailwind CSS, shadcn/ui, Framer Motion,
React Router, Archivo Black, and Inter. Its five main views are Home, Analyze,
Mastery, About, and Settings.

The current app implements those views in Streamlit in `app.py`, retaining the
black-and-cobalt palette, dark/light appearance, large headings, bordered cards,
step feedback panels, and mastery displays. Native Streamlit controls mean this
is a design adaptation rather than a pixel-identical React rendering.

All interface copy is English. Learner settings focus on grade band, topic
levels, feedback preference, and learning notes. `math_mentor.py` supplies the
Colab-derived problem bank, step analysis, persistence, and recommendations.

`ui_source/` remains a design reference. Compared with the supplied ZIP, its
substantive edits are project attribution in About and Footer and its README.
Running that React reference separately does not connect it to the Python
backend. Making it the active frontend would require an API integration and a
corresponding deployment change.

See `UI_MIGRATION.md` for the retained design features and `ARCHITECTURE.md` for
the running app's learning workflow and storage.
