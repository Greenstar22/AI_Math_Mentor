# Streamlit Community Cloud Deployment

1. Open the GitHub repository: https://github.com/qxiao2ub/AI_Math_Mentor
2. Replace or upload the files from this ZIP to its **main** branch at the
   repository root. `app.py`, `math_mentor.py`, and `requirements.txt` belong
   at root, not inside a wrapper folder.
3. In Streamlit Community Cloud choose this repository and branch `main`.
   Set the main file path to `app.py`, then deploy or reboot the existing app.
4. **Activate the cumulative visitor counter:** follow
   [VISITOR_COUNTER_SETUP.md](VISITOR_COUNTER_SETUP.md) to create the separate
   `visitor-stats` storage branch and set a **private** fine-grained GitHub
   token in Streamlit app secrets. The math functionality does not need a
   token; **persistent visit counting does**.
5. Check https://math-ai-mentor.streamlit.app/ — the visit badge should show
   an increasing positive number if the secret and storage branch are set.

**Important:** Do not commit credentials or delete the `visitor-stats` branch.
Store visits on the visitor branch to avoid redeployment on every visit.
