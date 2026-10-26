# UI migration notes

The earlier React/Tailwind design was adapted to native Streamlit plus custom
CSS. The maintained entry point is `app.py`, launched from the repository root
with `python -m streamlit run app.py`.

## Retained design and current behavior

- Dark-first black/cobalt styling with an optional Light theme, Archivo Black
  and Inter typography, bordered cards, progress bars and step-review panels.
- Six current pages: Home, Analyze, Mastery, About, Settings and Account. The
  original React design had five pages and remains separate.
- Selection from 50 reviewed problems across five topics and 25 concepts;
  difficulty is author-assigned, not empirically calibrated.
- One mathematical expression/equation per line, reference matching and
  preceding-line symbolic checks, with known alternative-path limitations.
- Diagnostic rules and locally trained synthetic-data classifiers; displayed
  confidence and mastery are heuristic, not validated assessment probabilities.
- Guest preferences and progress in Streamlit session memory; authenticated
  account UUIDs, profiles and saved learning records in Supabase PostgreSQL.
- Saved history and reports, topic-level settings, guarded guest import/save
  retries, account logout and guarded deletion.
- Retained author/advisor attribution and upstream fork provenance.

## Reference boundary

`ui_source/` is the preserved React design/demo with its own problem bank,
mocked analysis, in-memory mastery, localStorage appearance preference, account
placeholders and simulated contact submission. It does not provide the current
Python or Supabase backend. The Colab notebook likewise preserves a historical
six-problem SQLite/optional-Gradio workflow. Neither is synchronized with the
current 50-problem bank or account implementation.

The Streamlit About-page contact form validates locally and sends nothing.
Feedback ratings on saved mathematical reviews are separate and use the selected
progress store. No general problem-entry API, proof verifier, SMTP service,
password recovery, email-change flow or Remember me has been implemented.

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for formulas and limitations,
[ACCOUNTS_SETUP.md](docs/ACCOUNTS_SETUP.md) for account setup, and
[CONSISTENCY_AUDIT.md](docs/CONSISTENCY_AUDIT.md) for open decisions.
