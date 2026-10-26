# Streamlit Community Cloud Deployment

1. Open the GitHub repository: https://github.com/Greenstar22/AI_Math_Mentor
2. Use the reviewed files from this workspace on your deployment branch
   (`main` in this checkout), at the repository root. `app.py`,
   `math_mentor.py`, and `requirements.txt` belong
   at root, not inside a wrapper folder.
3. In Streamlit Community Cloud verify that the app is connected to
   `Greenstar22/AI_Math_Mentor` and the intended deployment branch (`main`
   in this checkout).
   Set the main file path to `app.py`, then deploy or reboot the existing app.
4. **Activate the cumulative visitor counter:** follow
   [VISITOR_COUNTER_SETUP.md](VISITOR_COUNTER_SETUP.md) to verify the separate
   `visitor-stats` storage branch exists in your fork (create it only if
   absent, and preserve any existing counter history) and set a **private**
   fine-grained GitHub
   token in Streamlit app secrets. The math functionality does not need a
   token; **persistent visit counting does**. This GitHub token is unrelated to
   Supabase account keys.
5. Check https://math-mentorai.streamlit.app/ — the visit badge should show
   an increasing positive number if the secret and storage branch are set.

**Important:** Do not commit credentials or delete the `visitor-stats` branch.
Store visits on the visitor branch to avoid redeployment on every visit.

## Fork-specific hosting checks

The correct public URL is https://math-mentorai.streamlit.app/. Update old
bookmarks and any hosting metadata that still advertises another address. The app's source-code link points
to the fork in code. If Streamlit's built-in **View source** still opens the
original repository, review the hosted app's repository/branch/main-file
configuration; this audit does not modify hosting settings.

In local or hosted Streamlit secrets, and any environment-variable overrides,
set `VISIT_COUNTER_REPO` to `Greenstar22/AI_Math_Mentor`. Verify that
`VISIT_COUNTER_BRANCH` names a branch in that fork containing
`data/visit_counter.json`; do not assume the fork copied an upstream storage
branch or its count. `VISIT_COUNTER_GITHUB_TOKEN` must have Contents read/write
access to the fork, with the appropriate resource owner and selected repository.
Do not paste credentials into documentation. See [VISITOR_COUNTER_SETUP.md](VISITOR_COUNTER_SETUP.md).

## Account setup is separate from deployment

Before enabling saved accounts, manually review/apply
[supabase/migrations/202610260001_accounts.sql](supabase/migrations/202610260001_accounts.sql)
and configure `[supabase].url` and `[supabase].publishable_key` in private
Streamlit secrets. `[supabase].secret_key` is needed only for guarded account
deletion. Follow [ACCOUNTS_SETUP.md](docs/ACCOUNTS_SETUP.md): Confirm email OFF,
minimum password length 12, no recovery emails and no Remember me. Guests can
use the app without Supabase configuration, with session-only progress.

`[app].public_url` should document https://math-mentorai.streamlit.app/, but is
not currently read to generate links or authentication redirects. The source
link comes from `GITHUB_URL`, and the public-app link from `LIVE_APP_URL`, in
`app.py`. No hosted settings were inspected as part of the local audit.

Run from the repository root with `python -m streamlit run app.py`. The supported and tested target is **Python 3.12**; `runtime.txt`
and CI specify it. Streamlit Community Cloud selects the actual Python version
in deployment **Advanced settings**. `runtime.txt` alone is not evidence of the
live version. Check the existing hosted app's actual Python version manually;
this audit does not change deployment settings or redeploy it.

See [Streamlit's deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) for the Python-version selector. Checking or changing a hosted interpreter is a separate owner action; this audit does neither.
