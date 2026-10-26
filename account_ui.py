"""Account forms and owner-bound Streamlit state transitions."""
from copy import deepcopy

import streamlit as st

from auth_service import AuthConfig, AccountError, InvalidSession, authenticate, logout, delete_account
from progress_store import (GuestProgressStore, TOPICS, default_profile, student_profile,
                            rebuild_bandit, analyze, report_for_attempt)
from supabase_store import SupabaseProgressStore

GUEST_MESSAGE = "Guest mode — progress lasts only for this session. Sign in to save it."
RECOVERY_MESSAGE = "Password recovery is not available in this prototype."


def apply_profile(state, profile):
    for key, value in profile.items():
        if key == "current_levels":
            for topic, level in value.items():
                state[f"level_{topic}"] = level
        else:
            state[key] = value


def reset_local(state):
    # No private widgets, reports, tokens, mutable clients, pending writes or bandits survive.
    session = state.get("auth_session")
    if session:
        session.access_token = session.refresh_token = ""
        session.client = None
    state.clear()
    state["guest_memory"] = {}
    store = GuestProgressStore(state["guest_memory"])
    apply_profile(state, store.load_profile())
    state["bandit"] = rebuild_bandit(store)
    state["top_nav"] = "Account"


def initialize_accounts(state):
    for key in state.pop("_clear_credentials", []):
        state.pop(key, None)
    if "guest_memory" not in state and "auth_session" not in state:
        state["guest_memory"] = {}
        store = GuestProgressStore(state["guest_memory"])
        apply_profile(state, store.load_profile())
        state["bandit"] = rebuild_bandit(store)
    state.setdefault("pending_attempts", [])


def selected_store(state):
    session = state.get("auth_session")
    if session:
        session.validate()
        return SupabaseProgressStore(session)
    return GuestProgressStore(state["guest_memory"])


def establish_account(state, session):
    store = SupabaseProgressStore(session)
    profile = store.load_profile()
    store.load_attempts()
    bandit = rebuild_bandit(store)
    guest_attempts = GuestProgressStore(state["guest_memory"]).load_attempts()
    state.clear()
    state["auth_session"] = session
    state["bandit"] = bandit
    state["pending_attempts"] = []
    if guest_attempts:
        state["guest_import"] = dict(owner_id=session.user_id, attempts=guest_attempts)
    apply_profile(state, profile)
    state["top_nav"] = "Account"


def save_preferences(state, changes):
    store = selected_store(state)
    profile = store.load_profile()
    profile.update(changes)
    store.save_profile(profile)
    apply_profile(state, profile)


def submit_analysis(state, problem_id, steps):
    if state.get("guest_import"):
        raise AccountError("Choose whether to save or discard guest progress before analyzing again.")
    store = selected_store(state)
    payload, report = analyze(store, problem_id, steps, state["bandit"])
    # Queue the exact immutable JSON-compatible content before the first network write.
    pending = dict(owner_id=store.owner_id, payload=deepcopy(payload), report=deepcopy(report))
    state.setdefault("pending_attempts", []).append(pending)
    state["last_report"] = report
    state["feedback_recorded"] = False
    return retry_attempt(state, payload["attempt_id"])


def retry_attempt(state, attempt_id):
    store = selected_store(state)
    item = next(p for p in state["pending_attempts"] if p["payload"]["attempt_id"] == attempt_id)
    if item["owner_id"] != store.owner_id:
        raise AccountError("Pending work belongs to a different session. It cannot be saved here.")
    store.save_attempts([deepcopy(item["payload"])])
    # Confirm reads before removing the pending payload. Retrying is idempotent if reads failed.
    refreshed = report_for_attempt(store, item["payload"])
    state["bandit"] = rebuild_bandit(store)
    state["last_report"] = refreshed
    state["pending_attempts"] = [p for p in state["pending_attempts"] if p is not item]
    problem_id = item["payload"]["problem_id"]
    draft = state.get("solution_drafts", {}).get(problem_id)
    if draft is not None and [line.strip() for line in draft.splitlines() if line.strip()] == [e["student_step"] for e in item["payload"]["evaluations"]]:
        state["solution_drafts"].pop(problem_id)
    return refreshed


def import_guest_progress(state):
    store = selected_store(state)
    pending = state["guest_import"]
    if pending["owner_id"] != store.owner_id:
        raise AccountError("Guest import belongs to another account.")
    store.save_attempts(deepcopy(pending["attempts"]))
    store.load_history()
    state["bandit"] = rebuild_bandit(store)
    del state["guest_import"]


def sign_out(state):
    session = state.get("auth_session")
    success = logout(session) if session else True
    reset_local(state)
    return success


def render_pending():
    state = st.session_state
    if state.get("guest_import"):
        st.warning("Choose what to do with this guest session before new learning submissions.")
        if st.button("Save this session to my account"):
            try:
                import_guest_progress(state)
                st.success("Session progress saved to your account.")
            except InvalidSession:
                raise
            except (AccountError, ValueError) as exc:
                st.error(str(exc))
        if state.get("guest_import") and st.button("Discard guest progress"):
            del state["guest_import"]
            st.rerun()
    for pending in list(state.get("pending_attempts", [])):
        st.warning("Analysis complete — not saved. Retry saving.")
        aid = pending["payload"]["attempt_id"]
        if st.button("Retry saving", key=f"retry_{aid}"):
            try:
                retry_attempt(state, aid)
                st.success("Saved to your account" if state.get("auth_session") else "Saved for this guest session.")
            except InvalidSession:
                raise
            except (AccountError, ValueError) as exc:
                st.error(str(exc))


def render_account():
    state = st.session_state
    st.title("Account")
    st.info("Email ownership is not verified in this prototype.")
    st.caption(RECOVERY_MESSAGE)
    notice = state.pop("account_notice", None)
    if notice:
        st.info(notice)
    config = AuthConfig.from_secrets(st.secrets)
    session = state.get("auth_session")
    if not session:
        st.info(GUEST_MESSAGE)
        if not config.available:
            st.info("Account configuration is unavailable. Guest mode remains available.")
        for signup, label in [(False, "Sign in"), (True, "Create account")]:
            prefix = "signup" if signup else "login"
            keys = [f"{prefix}_email", f"{prefix}_password"] + ([f"{prefix}_confirm"] if signup else [])
            with st.form(prefix):
                email = st.text_input("Email", key=keys[0], disabled=not config.available)
                password = st.text_input("Password (at least 12 characters)" if signup else "Password", type="password", key=keys[1], disabled=not config.available)
                confirmation = st.text_input("Confirm password", type="password", key=keys[2], disabled=not config.available) if signup else None
                submitted = st.form_submit_button(label, disabled=not config.available)
            if submitted:
                try:
                    if signup and password != confirmation:
                        raise AccountError("Passwords must match.")
                    authenticated = authenticate(config, email, password, signup=signup)
                    establish_account(state, authenticated)
                    state["account_notice"] = "Signed in. Account preferences have been loaded."
                except (AccountError, ValueError) as exc:
                    state["account_notice"] = str(exc)
                finally:
                    state["_clear_credentials"] = keys
                st.rerun()
        guest_has_work = (bool(selected_store(state).load_attempts()) or bool(state.get("pending_attempts"))
                          or selected_store(state).load_profile() != default_profile(guest=True)
                          or bool(state.get("solution_drafts")))
        confirmed = st.checkbox("Discard this guest session and its work") if guest_has_work else True
        if st.button("Start a new guest session", disabled=not confirmed):
            reset_local(state)
            st.rerun()
        return

    st.text_input("Signed-in email", value=session.email, disabled=True)
    st.caption("Login state lasts only for this Streamlit session. Saved cloud progress survives signing in again.")
    if st.button("Refresh saved progress"):
        try:
            store = selected_store(state)
            profile = store.load_profile()
            store.load_history()
            state["bandit"] = rebuild_bandit(store)
            apply_profile(state, profile)
            state.pop("last_report", None)
            for key in list(state):
                if key.endswith("_input"):
                    del state[key]
            st.success("Saved progress refreshed.")
        except InvalidSession:
            raise
        except AccountError as exc:
            st.error(str(exc))
    has_unsaved = bool(state.get("pending_attempts") or state.get("guest_import")
                       or state.get("solution_drafts"))
    if has_unsaved:
        st.warning("Signing out will discard unsaved analyses and temporary guest-import work.")
    confirmed = st.checkbox("Discard unsaved work and sign out") if has_unsaved else True
    if st.button("Sign out", disabled=not confirmed):
        success = sign_out(state)
        state["account_notice"] = "Signed out locally." if success else "Local access cleared. Remote sign-out failed; the provider session may remain valid until expiry."
        st.rerun()
    with st.expander("Delete my account"):
        st.warning("This permanently deletes your account and its learning records. Provider backups and already issued tokens may outlive deletion.")
        with st.form("delete_account"):
            phrase = st.text_input("Type DELETE", key="delete_phrase")
            password = st.text_input("Current password", type="password", key="delete_password")
            submitted = st.form_submit_button("Delete my account")
        if submitted:
            try:
                if phrase != "DELETE":
                    raise AccountError("Type DELETE to confirm account deletion.")
                delete_account(session, config, password, st.secrets)
                reset_local(state)
                state["account_notice"] = "Account deleted. A new guest session has started."
            except InvalidSession:
                raise
            except AccountError as exc:
                state["account_notice"] = str(exc)
            finally:
                state["_clear_credentials"] = ["delete_password", "delete_phrase"]
            st.rerun()
