# MathMentor accounts setup

This implementation is local source only. No hosted migration or deployment is performed by the tests or by importing the app. Ordinary data access uses the publishable key and a server-validated user's access token. SDK version: `supabase==2.33.0`.

## 1. Configure Supabase Auth

In the project's Auth settings, enable email/password sign-in, turn **Confirm email OFF**, and set the password minimum to **12 characters**. Do not configure SMTP, verification codes, recovery links, Resend, email templates, or redirects for this release. Signup must return an authenticated session, and the app validates it with `auth.get_user`; a user object alone is insufficient.

Email ownership is **not verified**. Password recovery is **unavailable**. Do not use this prototype for sensitive learning records or passwords you cannot afford to lose.

## 2. Apply the migration manually

In Supabase SQL Editor, using the database owner's SQL Editor context:

1. Review and run the **entire** file `supabase/migrations/202610260001_accounts.sql`, from `BEGIN` through `COMMIT`. It is the only migration, so there are no earlier files to apply.
2. Confirm all four tables exist with RLS enabled: `profiles`, `attempts`, `step_evaluations`, `feedback_events`.
3. Confirm `mathmentor_create_profile` is an INSERT trigger on `auth.users`. Its restricted SECURITY DEFINER function uses an empty search path and fixed defaults. The migration backfills missing profiles for existing Auth users without copying editable metadata.
4. Confirm `save_attempts(jsonb)` and `record_feedback(uuid,jsonb)` are SECURITY INVOKER and executable only by authenticated users. Verify profile ownership/creation-time columns and server timestamps are not granted for client updates.

Rerunning this migration preserves data. Existing tables with the same names but without this migration's schema marker are rejected as incompatible; review and reconcile them separately. Do not drop existing tables to bypass that error. No automatic import from local SQLite exists.

The immutable `attempts.payload` column stores the original request for strict retry comparison. It also preserves saved verdicts, feedback, and the selected problem snapshot for history reopening. Later ratings are loaded separately from `feedback_events`. Neither learning table contains an email or password. `problem_version` is SHA-256 of UTF-8 problem JSON with sorted keys, compact separators, unescaped Unicode, and no nonfinite numbers. `scoring_version` is `v1`.

The attempt RPC saves a whole batch and all steps/imported ratings atomically. It serializes competing attempt IDs, compares exact JSONB payloads for retries, and rejects conflicting content. The rating RPC keeps the first successful rating per evaluated step. These protections must be checked on the actual database; offline Python fakes do not establish RLS or transaction correctness.

## 3. Configure Streamlit secrets

Keep `.streamlit/secrets.toml` ignored and untracked. Preserve existing visitor-counter configuration if used. The example file contains placeholders only:

```toml
[supabase]
url = "https://YOUR_PROJECT.supabase.co"
publishable_key = "REPLACE_WITH_PUBLISHABLE_KEY"
secret_key = "REPLACE_WITH_SECRET_KEY"

[app]
public_url = "https://YOUR_APP.streamlit.app"
```

Set the actual values locally in the ignored file. For a deployment you perform later, enter the same sections in the hosting provider's private Streamlit Secrets settings; do not upload a real secrets file or put keys in a repository. `public_url` is reserved for deployment documentation; authentication does not use email redirects.

The URL and publishable key enable login and saved progress. Missing either leaves guest mode usable and account forms disabled. Missing only the secret key leaves normal accounts usable and disables deletion with an administrator-configuration message. The secret key is read exclusively inside the isolated deletion function, after current-session validation and matching password reauthentication. It is never used for ordinary table access.

Install dependencies with `python -m pip install -r requirements-dev.txt`, then start locally with `python -m streamlit run app.py`.

## 4. Manual two-browser/device checks

Use two dedicated accounts and separate browser sessions, plus a fresh guest window:

1. Verify guest mode opens immediately. Give two guests the same display name and analyze different problems. Confirm each history and export contains only its own session. Change preferences, start a new guest session, and verify confirmation is required before work is discarded.
2. Create a dedicated account. With confirmation OFF it should enter account mode immediately only after a validated session. Verify the profile trigger created `Student`, Dark, Grades 9-12, socratic feedback, empty class/notes and beginner levels for all five topics, regardless of user metadata. Temporarily test confirmation ON only in a disposable test project; signup without a session must not enter account mode. Restore OFF.
3. Enter incorrect login details and verify a generic error. After every signup/login/deletion submission, confirm password widgets clear on the following rerun. Account email is read-only; there is no email-change or password-recovery flow.
4. Analyze as a guest, rate feedback, then sign in. Account preferences should load first. New analysis is blocked until choosing **Save this session to my account** or **Discard guest progress**. Import preserves original attempt IDs, analysis times, steps and ratings.
5. Sign in to account A in two browsers. Save on one, choose **Refresh saved progress** on the other, and check history/mastery. Rename A and check history remains. Give B the same display name and confirm it cannot see A's history, reports, exports or feedback state.
6. Interrupt connectivity during saving. The report remains pending and is excluded from persisted mastery/recommendations. Restore connectivity and retry: the original ID/time/feedback is reused. Repeat after a timeout where the server may already have committed. Verify exactly one attempt and one rating per step. Try logout with pending work/imports and check its discard warning.
7. Reopen an older history item after editing a problem in a disposable checkout. Saved verdicts and feedback should remain unchanged; the current bank must not silently regrade it.
8. Test token expiry/rotation and temporary network outages. Invalid identity/session clears local private state and asks for login; temporary failures block private operations without replacing the account with a guest. Logout clears local access even if remote local-scope signout fails, with an honest status message.
9. Deletion is destructive: use only a separately designated disposable account. Wrong password, a reauthenticated UUID mismatch, or a missing administrator key must prevent deletion. Correct DELETE confirmation and password should hard-delete that UUID and cascade learning records. Manually recreate the same email afterward: its new UUID must have no former history. No immediate provider-backup purge or revocation of every issued access token is promised.

## 5. Tests and explicit live opt-in

Safe offline suite (real Streamlit secrets are replaced with empty configuration in tests):

```powershell
python -m pytest tests -q
```

Offline tests cover storage contracts, state transitions, SDK HTTP mocking, owner filtering, retries and grading regressions. They do **not** test hosted RLS, hosted triggers, actual transaction rollback, or actual deletion cascades. The development dependency `pglast==7.21` validates SQL/PL/pgSQL syntax offline; it does not execute the migration.

Live tests require a migrated **test** project and two **precreated dedicated** accounts. They use ordinary user tokens, never an admin key. Set the following variables privately in your shell (do not paste secrets into shared transcripts):

- `MATHMENTOR_LIVE=1`
- `MM_TEST_SUPABASE_URL`, `MM_TEST_PUBLISHABLE_KEY`
- `MM_TEST_EMAIL_A`, `MM_TEST_PASSWORD_A`
- `MM_TEST_EMAIL_B`, `MM_TEST_PASSWORD_B`

Then run:

```powershell
python -m pytest tests/live/test_supabase_accounts_live.py -q --tb=short
```

This appends immutable test attempts/ratings and temporarily edits/restores dedicated profile display names. It tests actual RPC rollback, conflicting and concurrent retries, ownership filters, cross-owner child records, unauthenticated denials, column grants, imports, rating idempotency, and pagination. It does not create accounts, send emails or apply migrations. Repeated runs intentionally leave history on the dedicated accounts. Do not point it at real learners' accounts.

The deletion test is skipped unless you additionally set `MATHMENTOR_DELETE_DISPOSABLE=1`, `MM_DISPOSABLE_EMAIL`, `MM_DISPOSABLE_PASSWORD`, `MM_DISPOSABLE_USER_ID`, and `MM_DISPOSABLE_SECRET_KEY`. This account must be separate from A and B. The UUID must match the validated disposable identity. Only the isolated deletion function receives that administrator secret. To run just this destructive check:

```powershell
python -m pytest tests/live/test_supabase_accounts_live.py -q --tb=short -k disposable
```

Clear these environment variables after testing. No hosted tests, including destruction, are part of ordinary automated development.

## Prototype limits

Guests retain preferences, attempts, ratings and mastery only within one Streamlit session. Refreshing or losing that session may discard them. Login tokens also remain only in session memory; there is no Remember me, cookie or disk token storage. Cloud history survives signing in again. There is no email ownership verification, password recovery, automatic SQLite migration, or email-address editing. Pending unsaved analyses and unimported guest work are temporary and can be discarded on logout/session loss.
