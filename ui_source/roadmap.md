# MathMentor AI — Front-End Draft Roadmap

> Archived React design roadmap, not the current Streamlit release plan. The Linux-backend/Colab proposals and old checklist states below are preserved as historical planning. Current Streamlit accounts use Supabase, and this React demo remains disconnected. See [the current architecture](../docs/ARCHITECTURE.md).

## Done
- [x] Rebrand from Liam Fletcher portfolio to MathMentor AI (nav, footer, page copy, index.html metadata)
- [x] Navigation restructured: Home, Analyze, Mastery, About, Settings — each tab its own page, no same-page anchors
- [x] New landing page: graphic how-it-works intro (3 steps with mock visuals) + get-started options on scroll
- [x] About page: merged About + Contact (contact form moved here) with placeholder content
- [x] Settings page created (rightmost tab) with placeholder sections
- [x] Analyze page created with workspace wireframe placeholder
- [x] Removed Work, Contact, Styleguide pages and unused portfolio components/assets

## Open
- [x] Analyze page built: random problem from bank, one-step-per-line input, card-per-step feedback with stub analyzer (7 labels, confidence, explanations) — swap stub for real SymPy/ML pipeline later
- [ ] About page content — waiting on user guidance
- [x] Mastery page: per-topic level selector and expandable concept scores; mastery update remains at the end of Analyze feedback. Topic/concept names are placeholders; real catalogue + recommender + secure attempt DB come with the Linux backend.
- [x] Mastery moved to its own navigation page; Settings includes a persistent Light/Dark display control, with Dark as the default.
- [ ] Backend skeleton — later, based on user's integration instructions (model trained on Google Colab, to be hosted on mentor's Linux system)
