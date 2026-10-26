# Persistent visitor counter — setup guide

**This version uses no database for counting visitors.** It stores one integer
(`total_visits`) in a small JSON file committed to a dedicated GitHub branch.
Every **new Streamlit browser session** attempts to increment the total once.
Moving among Home, Analyze, Mastery, About, Settings, and Account does
**not** add extra visits. Opening a new tab, browser session or reloading may
create a new session; this counter measures **visits, not verified unique people**.

The persistent branch is essential: Streamlit Community Cloud's local disk is
not durable. Unlike a local file or session_state-only counter, committed
GitHub data survives app sleep, restarts, server replacement and deployments.

Account/guest resets currently clear the counter state too, so login,
logout, account deletion, or starting a new guest session can attempt another
increment within the same browser session. This is a known counting boundary,
not evidence of another unique visitor; the owner chose to retain this behavior for now.
The counter is separate from Supabase learner records.

## One-time GitHub configuration (required)

1. Use the current app files on the deployment branch (`main` in this checkout) of
   <https://github.com/Greenstar22/AI_Math_Mentor>. Keep `app.py` at root and
   `data/visit_counter.json` in the data folder.
2. Verify that **your fork** has a `visitor-stats` branch containing
   `data/visit_counter.json`. If it is absent, create that branch from your
   deployment branch once. Preserve an existing branch and its historical
   total; a fork does not establish that upstream storage branches or their
   totals are present. The program
   writes its totals to `visitor-stats`, **not** the deployment branch. This
   prevents a stream of visitor commits from redeploying your web app.
3. In GitHub, open **Settings > Developer settings > Personal access tokens >
   Fine-grained tokens** (or your account's token settings). Create a token
   with access **only to `Greenstar22/AI_Math_Mentor`** and **Repository contents:
   Read and write**. Keep the token private and set an expiration/rotation
   reminder as appropriate. The token must be allowed to update the
   `visitor-stats` branch; branch protections that block token writes need
   adjustment.
4. Open <https://share.streamlit.io/> (or Streamlit Community Cloud) and
   select the application serving `math-mentorai.streamlit.app`. Under **App settings > Secrets**
   configure the token and repository explicitly, and verify the storage branch:

   ```toml
   VISIT_COUNTER_GITHUB_TOKEN = "github_pat_YOUR_ACTUAL_TOKEN"
   VISIT_COUNTER_REPO = "Greenstar22/AI_Math_Mentor"
   VISIT_COUNTER_BRANCH = "visitor-stats"
   ```

   Existing `VISIT_COUNTER_REPO` secrets override the Python default; update
   that setting to the fork even if the app code is already corrected. The
   same setting names can also be supplied through environment variables,
   which must be checked separately. Review local and hosted configuration
   privately; never copy actual credential values into an audit or log.

5. Save the secrets and reboot/redeploy the app if requested. Test the app at
   <https://math-mentorai.streamlit.app/>. If the counter file is an unused zero seed, a successful first recorded visit
   changes it to 1; preserve any existing nonzero historical total instead. **0 is never presented as
   an active visitor total**. Every app page shows the cumulative visits badge.
6. Visit in a fresh browser session/private window to confirm the number
   increases. Navigate among pages in one session to confirm it does not
   increase again. Inspect `data/visit_counter.json` **on the `visitor-stats`
   branch** in GitHub to check the actual durable number.

## Why a GitHub branch instead of a local file?

- On Streamlit Cloud, local files, process globals and `st.session_state`
  can disappear on restart, redeployment or server replacement.
- A versioned JSON file stored on GitHub persists independently of app restarts unless you explicitly
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

**Counter data:** The application writes no personal identifiers, IP addresses,
browser fingerprints, or credentials into its aggregate JSON. This does not
make claims about GitHub or hosting-provider request logs. Never hardcode a PAT in Python,
README, `secrets.example.toml`, or any pushed repository file.
