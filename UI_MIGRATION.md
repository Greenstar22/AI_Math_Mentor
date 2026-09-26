# UI Migration Notes

The attached React/Tailwind prototype was migrated into a native Streamlit interface so the complete product can run on Streamlit Community Cloud from one Python entry point.

## Migrated design language

- Dark-first black and cobalt visual system
- Archivo Black-inspired display typography and Inter body typography
- Large editorial hero headings
- Square bordered cards, cobalt accents, progress bars, and step-review panels
- Five views: Home, Analyze, Mastery, About, and Settings
- Dark/light appearance control
- Responsive layouts for desktop, tablet, and mobile

## Migrated product behavior

- Problem selection and calibrated starter bank
- One-step-per-line solution workspace
- Step-level correctness and error-category feedback
- Confidence, expected step, concept, and mentor response panels
- Attempt history and mastery analytics
- Topic-level learner settings
- Full workflow and technology overview
- Author and advisor attribution throughout the app

## Architecture decision

Streamlit Community Cloud serves Python applications and does not directly run a Vite development server as the primary app process. The UI was therefore ported to native Streamlit plus custom CSS, while the supplied React/Tailwind source, with project-credit and README edits, is retained under `ui_source/` for design reference and future front-end work.

## Main entry point

`app.py`
