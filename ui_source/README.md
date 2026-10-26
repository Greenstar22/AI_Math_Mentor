# MathMentor AI React design demo

**Author:** Anchit Nayak  
**Advisor:** Dr. Qingyang Xiao

This directory retains the React/TypeScript design reference for the Streamlit
migration. It is independently runnable demonstration code, not the deployed
Streamlit frontend and not a second implementation of Supabase accounts.

The current app is https://math-mentorai.streamlit.app/ and its maintained entry
point is root-level `app.py`. See [the main README](../README.md) and
[ARCHITECTURE.md](../docs/ARCHITECTURE.md) for current behavior.

## What this demo actually does

- Five design pages: Home, Analyze, Mastery, About and Settings; the Streamlit
  app also has Account.
- A separate demonstration problem bank and string-comparison heuristics.
- Mock logistic/DNN functions based on string length, with fixed confidence
  and estimated-error values. No trained models, SymPy or Python API calls.
- In-memory mastery examples that can reset when the page reloads; these are
  not cloud learning records or the current app's mastery formula.
- A browser-localStorage Dark/Light appearance preference, not persisted login.
- Placeholder account/password controls with no authentication or save service.
- A simulated contact submission that sends no message.

Its labels, bank, diagnostic constants and proposed features are not the current
backend contract. `roadmap.md` preserves earlier design planning, including old
Linux-backend proposals, rather than promising the current deployment plan.

## Run the demo locally

From `ui_source/`, with Node.js and npm available:

```bash
npm install
npm run dev
```

`vite.config.ts` requests port 8080 (Vite may choose another if occupied).
`npm run build` compiles the reference; `npm run lint` checks its TypeScript/React
source. Node/npm are not required to run the Streamlit app. Dependencies include
Vite, React, Tailwind, shadcn/ui, Framer Motion, React Router and Recharts.
The package is private and does not identify a different current repository.
