# Persistent visitor counter — setup guide

**This version uses no database for counting visitors.** It stores one integer
(`total_visits`) in a small JSON file committed to a dedicated GitHub branch.
Every **new Streamlit browser session** attempts to increment the total once.
Moving among the app's Home, Analyze, Mastery, About, and Settings pages does
**not** add extra visits. Opening a new tab, browser session or reloading may
create a new session; this counter measures **visits, not verified unique people**.

The persistent branch is essential: Streamlit Community Cloud's local disk is
not durable. Unlike a local file or session_state-only counter, committed
GitHub data survives app sleep, restarts, server replacement and deployments.

## One-time GitHub configuration (required)

1. Upload the contents of the ZIP to the **main** branch of
   <https://github.com/qxiao2ub/AI_Math_Mentor>. Keep `app.py` at root and
   `data/visit_counter.json` in the data folder.
2. On GitHub, use the branch selector (usually "main"), create a **new branch
   named `visitor-stats` from `main`**, and leave it in the same repository.
   This copies the starting JSON file into the storage branch. The program
   writes its totals to `visitor-stats`, **not** the deployment branch. This
   prevents a stream of visitor commits from redeploying your web app.
3. In GitHub, open **Settings > Developer settings > Personal access tokens >
   Fine-grained tokens** (or your account's token settings). Create a token
   with access **only to `qxiao2ub/AI_Math_Mentor`** and **Repository contents:
   Read and write**. Keep the token private and set an expiration/rotation
   reminder as appropriate. The token must be allowed to update the
   `visitor-stats` branch; branch protections that block token writes need
   adjustment.
4. Open <https://share.streamlit.io/> (or Streamlit Community Cloud) and
   select the `math-ai-mentor` application. Under **App settings > Secrets**
   paste, replacing ONLY the private token:

   ```toml
   VISIT_COUNTER_GITHUB_TOKEN = "github_pat_YOUR_ACTUAL_TOKEN"
   VISIT_COUNTER_REPO = "qxiao2ub/AI_Math_Mentor"
   VISIT_COUNTER_BRANCH = "visitor-stats"
   ```

5. Save the secrets and reboot/redeploy the app if requested. Test the app at
   <https://math-ai-mentor.streamlit.app/>. The first recorded visit changes
   the counter from 0 (initial storage value) to 1; **0 is never presented as
   an active visitor total**. Every app page shows the cumulative visits badge.
6. Visit in a fresh browser session/private window to confirm the number
   increases. Navigate among pages in one session to confirm it does not
   increase again. Inspect `data/visit_counter.json` **on the `visitor-stats`
   branch** in GitHub to check the actual durable number.

## Why a GitHub branch instead of a local file?

- On Streamlit Cloud, local files, process globals and `st.session_state`
  can disappear on restart, redeployment or server replacement.
- A versioned JSON file stored on GitHub is permanent unless you explicitly
  delete/reset the branch, revoke all write access, or the service becomes
  unavailable. Do **not** re-create `visitor-stats` from main after launch:
  that would replace your running total with the initial file.
- The code uses GitHub's SHA conflict check and retries to reduce lost
  increments during overlapping visits. This is suitable for a prototype with
  modest traffic, not a high-traffic, mathematically perfect analytics service.
- Each new session records one GitHub commit in `visitor-stats`, which can
  consume API quotas and git history over time. High-traffic apps should use
  a dedicated atomic counter service instead.

## Reliability and troubleshooting

- **Counter shows “SETUP REQUIRED” / dash:** token missing or secrets not saved.
- **Counter shows “UNAVAILABLE” / dash:** GitHub unreachable, bad token, missing
  branch, permissions, rate limits or an invalid counter file. Unlike a fake
  local fallback, a missing total is never shown as 0.
- **Count visible but “LAST KNOWN”:** fresh reads failed; the app shows the
  previous value until storage is available. It doesn't roll back to zero.
- **Counter not increasing:** ensure storage branch is `visitor-stats`, token
  has Contents read/write and is configured in Streamlit, not on GitHub UI
  alone. Try a *new browser session*; page-navigation does not count again.
- **Deployment repeatedly restarts:** ensure Streamlit deploys `main`, not
  `visitor-stats`, and that CI workflows don't run on counter branch commits.
- **Token expired:** replace just the secret in Streamlit. Preserve the
  existing `visitor-stats` branch to keep the historical count.

**Security:** No personal identifiers, IP addresses, browser fingerprints, or
credentials are written into the counter JSON. Never hardcode a PAT in Python,
README, `secrets.example.toml`, or any pushed repository file.
