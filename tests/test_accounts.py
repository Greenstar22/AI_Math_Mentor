"""Offline contracts and state-machine tests. These do NOT verify hosted RLS."""
from copy import deepcopy
from types import SimpleNamespace as NS
from uuid import uuid4
import time

import pytest

import account_ui as ui
import auth_service as auth
import math_mentor as engine
from progress_store import (GuestProgressStore, analyze, rebuild_bandit, new_rating,
                            default_profile, canonical, report_for_attempt)
from supabase_store import SupabaseProgressStore


@pytest.fixture
def guest():
    return GuestProgressStore({})


@pytest.fixture
def payload(guest):
    return analyze(guest, "ALG1-LIN-001", ["2*x+3=11", "2*x=10"], rebuild_bandit(guest))[0]


def test_guest_isolation_rename_and_copies(guest, payload):
    other = GuestProgressStore({})
    assert guest.owner_id != other.owner_id
    assert guest.owner_id.startswith("guest_")
    for store in (guest, other):
        profile = store.load_profile()
        profile["display_name"] = "Same name"
        store.save_profile(profile)
    guest.save_attempts([payload])
    profile["display_name"] = "Renamed"
    guest.save_profile(profile)
    assert len(guest.load_history()) == 2
    assert other.load_history().empty
    copy = guest.load_attempts()
    copy[0]["evaluations"].clear()
    assert len(guest.load_attempts()[0]["evaluations"]) == 2
    assert GuestProgressStore(guest.memory).owner_id == guest.owner_id


def test_guest_batch_atomicity_and_idempotency(guest, payload):
    bad = deepcopy(payload)
    bad["attempt_id"] = str(uuid4())
    bad["coverage"] = 2
    with pytest.raises(ValueError):
        guest.save_attempts([payload, bad])
    assert not guest.load_attempts()
    guest.save_attempts([payload, payload])
    assert len(guest.load_attempts()) == 1
    conflict = deepcopy(payload)
    conflict["overall_score"] = 50
    with pytest.raises(ValueError, match="different content"):
        guest.save_attempts([conflict])
    assert guest.load_attempts()[0] == payload


def test_feedback_first_saved_wins_and_bandit_rebuild(guest, payload):
    guest.save_attempts([payload])
    step = payload["evaluations"][1]
    rating = new_rating(step, step["feedback_style"], 1)
    assert guest.record_feedback(payload["attempt_id"], rating)
    opposite = {**rating, "feedback_event_id": str(uuid4()), "reward": -1}
    assert not guest.record_feedback(payload["attempt_id"], opposite)
    assert len(guest.load_feedback_events()) == 1
    key = (rating["context_key"], rating["feedback_style"])
    assert rebuild_bandit(guest).counts[key] == 1
    assert rebuild_bandit(guest).values[key] == 1
    assert not rebuild_bandit(GuestProgressStore({})).counts


@pytest.mark.parametrize("field,value", [("display_name", "x"*81), ("school_class", "x"*121),
    ("accessibility_notes", "x"*1001), ("theme", "Other"), ("preferred_feedback", "other"),
    ("current_levels", {"Made up": "advanced"})])
def test_profile_validation(guest, field, value):
    profile = guest.load_profile()
    profile[field] = value
    with pytest.raises(ValueError):
        guest.save_profile(profile)


def test_runtime_never_uses_sqlite(monkeypatch, guest, payload):
    def forbidden(*args, **kwargs):
        pytest.fail("Runtime attempted legacy SQLite access")
    for name in ("get_connection", "initialize_database", "load_student_history", "record_attempt"):
        monkeypatch.setattr(engine, name, forbidden)
    guest.save_attempts([payload])
    _, report = analyze(guest, "ALG1-LIN-001", ["x = 4"], rebuild_bandit(guest))
    assert report["recommended_problem"]
    report_for_attempt(guest, payload)
    engine.weakness_summary(history=guest.load_history())


def sdk_client(owner=None):
    owner = owner or str(uuid4())
    user = NS(id=owner, email="test@example.invalid", email_confirmed_at=None)
    session = NS(access_token="access", refresh_token="refresh", expires_at=time.time()+3600)
    client = NS()
    client.last_credentials = None
    client.validations = []
    client.signouts = []
    def login(credentials):
        client.last_credentials = credentials
        return NS(session=session, user=user)
    def get_user(token):
        client.validations.append(token)
        return NS(user=user)
    def refresh(token):
        client.rotated = token
        return NS(session=NS(access_token="rotated", refresh_token="rotated-refresh", expires_at=time.time()+3600))
    client.auth = NS(sign_in_with_password=login, sign_up=login, get_user=get_user,
                     refresh_session=refresh,
                     admin=NS(sign_out=lambda token, scope: client.signouts.append({"scope": scope})))
    client.postgrest = NS(auth=lambda token: setattr(client, "db_token", token))
    return client, user, session


def signed_session(client):
    return auth.authenticate(auth.AuthConfig("https://example.invalid", "public"), "  test@example.invalid  ", " Password kept  ", factory=lambda c: client)


def test_signup_requires_session_and_server_user():
    client, user, _ = sdk_client()
    config = auth.AuthConfig("url", "public")
    session = auth.authenticate(config, " x@a.invalid ", " a password  ", signup=True, factory=lambda c: client)
    assert session.user_id == user.id
    assert client.last_credentials == {"email": "x@a.invalid", "password": " a password  "}
    assert client.validations
    client.auth.sign_up = lambda c: NS(session=None, user=user)
    with pytest.raises(auth.AccountError, match="Confirm email"):
        auth.authenticate(config, "x@a.invalid", "long password", signup=True, factory=lambda c: client)
    client.auth.sign_up = lambda c: NS(session=NS(access_token="x", refresh_token="r", expires_at=9999999999))
    client.auth.get_user = lambda token: NS(user=None)
    with pytest.raises(auth.AccountError):
        auth.authenticate(config, "x@a.invalid", "long password", signup=True, factory=lambda c: client)


def test_login_errors_are_generic_and_secret_free():
    client, _, _ = sdk_client()
    def fail(c):
        raise RuntimeError("sensitive provider details")
    client.auth.sign_in_with_password = fail
    with pytest.raises(auth.AccountError) as err:
        signed_session(client)
    assert "sensitive" not in str(err.value)
    assert "Unable to sign in" in str(err.value)


def test_refresh_retains_rotated_tokens_and_validates():
    client, _, _ = sdk_client()
    session = signed_session(client)
    session.expires_at = time.time()+30
    session.validate()
    assert client.rotated == "refresh"
    assert session.refresh_token == "rotated-refresh"
    assert client.validations[-1] == client.db_token == "rotated"
    session.validate()
    assert client.rotated == "refresh"  # No second refresh of the old token.


def test_network_blocks_private_operations_and_identity_change_rejected():
    client, user, _ = sdk_client()
    session = signed_session(client)
    client.auth.get_user = lambda token: (_ for _ in ()).throw(TimeoutError())
    with pytest.raises(auth.ConnectionUnavailable):
        session.protected(lambda c: pytest.fail("operation must not run"))
    assert session.user_id == user.id
    client.auth.get_user = lambda token: NS(user=NS(id=str(uuid4())))
    with pytest.raises(auth.InvalidSession):
        session.validate()


def test_logout_clears_all_private_state_even_on_remote_failure():
    client, _, _ = sdk_client()
    session = signed_session(client)
    client.auth.admin.sign_out = lambda *args: (_ for _ in ()).throw(TimeoutError())
    state = {"auth_session": session, "last_report": {"private": True}, "pending_attempts": [1],
             "guest_import": [2], "delete_password": "password", "solution_steps_x": "private", "bandit": object()}
    assert not ui.sign_out(state)
    assert "auth_session" not in state and "last_report" not in state and "pending_attempts" not in state
    assert "delete_password" not in state and "guest_import" not in state
    assert state["guest_memory"]["owner_id"].startswith("guest_")
    assert not session.access_token and not session.refresh_token


def test_local_scope_signout():
    client, _, _ = sdk_client()
    assert auth.logout(signed_session(client))
    assert client.signouts == [{"scope": "local"}]


class CloudFake:
    """Offline transport fake, not a substitute for database policy tests."""
    def __init__(self, owner, attempts=None):
        self.owner_id = owner
        self.guest = GuestProgressStore({"owner_id": owner, "profile": default_profile()})
        self.calls = []
        self.fail = False
        if attempts:
            self.guest.save_attempts(attempts)
    def __getattr__(self, name):
        return getattr(self.guest, name)
    def save_attempts(self, attempts):
        self.calls.append(deepcopy(attempts))
        if self.fail:
            raise auth.AccountError("offline")
        self.guest.save_attempts(attempts)


def test_save_retry_does_not_evaluate_twice_and_excludes_pending(monkeypatch):
    state = {}
    ui.initialize_accounts(state)
    cloud = CloudFake(str(uuid4()))
    monkeypatch.setattr(ui, "selected_store", lambda state: cloud)
    cloud.fail = True
    with pytest.raises(auth.AccountError):
        ui.submit_analysis(state, "ALG1-LIN-001", ["2*x = 8"], )
    pending = deepcopy(state["pending_attempts"][0])
    assert cloud.load_history().empty
    monkeypatch.setattr(ui, "analyze", lambda *args: pytest.fail("Retry re-evaluated work"))
    cloud.fail = False
    ui.retry_attempt(state, pending["payload"]["attempt_id"])
    assert cloud.calls[0] == cloud.calls[1] == [pending["payload"]]
    assert len(cloud.load_attempts()) == 1 and not state["pending_attempts"]


def test_pending_cannot_save_under_other_identity(monkeypatch, payload):
    state = {"pending_attempts": [{"owner_id": str(uuid4()), "payload": payload}]}
    cloud = CloudFake(str(uuid4()))
    monkeypatch.setattr(ui, "selected_store", lambda state: cloud)
    with pytest.raises(auth.AccountError, match="different session"):
        ui.retry_attempt(state, payload["attempt_id"])
    assert not cloud.calls


def test_guest_import_retries_preserve_ids_ratings_and_account_settings(monkeypatch, guest, payload):
    guest.save_attempts([payload])
    step = payload["evaluations"][1]
    guest.record_feedback(payload["attempt_id"], new_rating(step, step["feedback_style"], 1))
    client, _, _ = sdk_client()
    session = signed_session(client)
    cloud = CloudFake(session.user_id)
    monkeypatch.setattr(ui, "SupabaseProgressStore", lambda session: cloud)
    state = {"guest_memory": guest.memory, "private_widget": 1}
    ui.establish_account(state, session)
    assert state["display_name"] == "Student"
    assert "private_widget" not in state and "guest_memory" not in state
    cloud.fail = True
    with pytest.raises(auth.AccountError):
        ui.import_guest_progress(state)
    assert state["guest_import"]["attempts"][0]["attempt_id"] == payload["attempt_id"]
    with pytest.raises(auth.AccountError, match="before analyzing"):
        ui.submit_analysis(state, "ALG1-LIN-001", ["x=4"])
    cloud.fail = False
    ui.import_guest_progress(state)
    assert cloud.calls[0] == cloud.calls[1]
    assert not state.get("guest_import")
    assert len(cloud.load_feedback_events()) == 1
    assert len(cloud.load_history()) == 2


def test_history_reopens_saved_verdicts_without_regrading(monkeypatch, guest, payload):
    guest.save_attempts([payload])
    monkeypatch.setattr(engine, "evaluate_solution_steps", lambda *a: pytest.fail("regraded history"))
    report = report_for_attempt(guest, payload)
    assert report["evaluations"][1]["is_correct"] == payload["evaluations"][1]["is_correct"]
    assert report["feedback"][1]["feedback"] == payload["evaluations"][1]["feedback_text"]


class PagedClient:
    def __init__(self, rows):
        self.rows = rows
        self.filters = []
    def table(self, name):
        return self
    def select(self, columns):
        return self
    def eq(self, column, value):
        self.filters.append((column, value))
        return self
    def order(self, column):
        return self
    def range(self, start, end):
        self.start = start
        self.end = end
        return self
    def execute(self):
        return NS(data=self.rows[self.start:min(self.end+1, self.start+2)])  # Server cap below client page size.


def test_complete_pagination_and_owner_filter(payload):
    owner = str(uuid4())
    client = PagedClient([dict(user_id=owner, payload=payload) for _ in range(7)])
    store = SupabaseProgressStore(NS(user_id=owner, protected=lambda op: op(client)), page_size=5)
    assert len(store.load_attempts()) == 7
    assert all(f == ("user_id", owner) for f in client.filters)
    client.rows[3]["user_id"] = str(uuid4())
    with pytest.raises(auth.AccountError, match="ownership"):
        store.load_attempts()


@pytest.mark.parametrize("forged", ["user_id", "saved_at"])
def test_forged_payload_rejected_before_cloud_call(payload, forged):
    session = NS(user_id=str(uuid4()), protected=lambda op: pytest.fail("forged request was sent"))
    payload[forged] = str(uuid4())
    with pytest.raises(ValueError):
        SupabaseProgressStore(session).save_attempts([payload])


def test_deletion_wrong_password_and_identity_never_create_admin():
    client, _, _ = sdk_client()
    session = signed_session(client)
    config = auth.AuthConfig("url", "public")
    other, _, _ = sdk_client()
    def forbidden(*args):
        pytest.fail("Administrator client created without matching identity")
    with pytest.raises(auth.AccountError, match="match"):
        auth.delete_account(session, config, "wrong account", {}, factory=lambda c: other, admin_factory=forbidden)
    def wrong_password(c):
        raise RuntimeError("invalid login")
    client.auth.sign_in_with_password = wrong_password
    with pytest.raises(auth.AccountError):
        auth.delete_account(session, config, "wrong password", {}, factory=lambda c: client, admin_factory=forbidden)


def test_deletion_missing_secret_and_exact_verified_target():
    client, user, _ = sdk_client()
    session = signed_session(client)
    reauth, _, _ = sdk_client(user.id)
    with pytest.raises(auth.AccountError, match="administrator configuration"):
        auth.delete_account(session, auth.AuthConfig("url", "public"), "pw", {}, factory=lambda c: reauth)
    reauth, _, _ = sdk_client(user.id)
    calls = []
    admin = NS(auth=NS(admin=NS(delete_user=lambda target, **kw: calls.append((target, kw)))))
    auth.delete_account(session, auth.AuthConfig("url", "public"), "pw", {"supabase": {"secret_key": "test-only"}},
                        factory=lambda c: reauth, admin_factory=lambda url, key: admin)
    assert calls == [(session.user_id, {"should_soft_delete": False})]


def test_official_sdk_configuration_and_session_api_offline():
    import httpx
    from supabase import create_client, ClientOptions
    requests = []
    owner = str(uuid4())
    def transport(request):
        requests.append(request)
        return httpx.Response(200, json={"id": owner, "aud": "authenticated", "role": "authenticated",
            "email": "test@example.invalid", "app_metadata": {}, "user_metadata": {}, "created_at": "2026-01-01T00:00:00Z"})
    client = create_client("https://test.invalid", "publishable-placeholder", options=ClientOptions(
        auto_refresh_token=False, persist_session=True, httpx_client=httpx.Client(transport=httpx.MockTransport(transport))))
    assert client.auth.get_user("ordinary-token").user.id == owner
    assert requests[0].headers["authorization"] == "Bearer ordinary-token"
    assert client.options.auto_refresh_token is False
    assert client.options.persist_session is True


def test_engine_import_has_no_database_initialization():
    import ast
    from pathlib import Path
    tree = ast.parse(Path(engine.__file__).read_text(encoding="utf-8"))
    assert not any(isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and
                   getattr(n.value.func, "id", "") == "initialize_database" for n in tree.body)


@pytest.mark.parametrize("status", [204, 500])
def test_real_sdk_logout_reports_failure_and_clears_local_client(status):
    import httpx
    from supabase import create_client, ClientOptions
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(status, json={"message": "temporary failure"} if status == 500 else None)
    client = create_client("https://test.invalid", "public-placeholder", options=ClientOptions(
        auto_refresh_token=False, persist_session=True, httpx_client=httpx.Client(transport=httpx.MockTransport(respond))))
    session = auth.AuthSession(client, str(uuid4()), "test@example.invalid", "access", "refresh", time.time()+3600)
    assert auth.logout(session) == (status == 204)
    assert requests[0].url.params["scope"] == "local"
    assert requests[0].headers["authorization"] == "Bearer access"
    assert not session.access_token and not session.refresh_token and session.client is None


def test_pinned_sdk_login_and_refresh_with_mock_http():
    import httpx
    import json
    from supabase import create_client, ClientOptions
    owner = str(uuid4())
    user = {"id": owner, "aud": "authenticated", "role": "authenticated", "email": "test@example.invalid",
            "app_metadata": {}, "user_metadata": {}, "created_at": "2026-01-01T00:00:00Z"}
    requests = []
    def respond(request):
        requests.append(request)
        if request.url.path.endswith("/user"):
            return httpx.Response(200, json=user)
        rotated = request.url.params.get("grant_type") == "refresh_token"
        return httpx.Response(200, json={"user": user, "access_token": "rotated" if rotated else "original",
            "refresh_token": "rotated-refresh" if rotated else "original-refresh", "token_type": "bearer",
            "expires_in": 3600, "expires_at": int(time.time())+3600})
    client = create_client("https://test.invalid", "public-placeholder", options=ClientOptions(
        auto_refresh_token=False, persist_session=True, httpx_client=httpx.Client(transport=httpx.MockTransport(respond))))
    session = auth.authenticate(auth.AuthConfig("url", "public"), " test@example.invalid ", " Keep Spaces  ", factory=lambda c: client)
    assert session.user_id == owner
    assert json.loads(requests[0].content)["password"] == " Keep Spaces  "
    session.expires_at = time.time()+1
    session.validate()
    assert session.access_token == "rotated" and session.refresh_token == "rotated-refresh"
    assert client.auth.get_session().refresh_token == "rotated-refresh"


def test_migration_sql_and_plpgsql_parse_offline():
    from pathlib import Path
    from pglast import parse_sql, parse_plpgsql
    migration = Path(__file__).resolve().parents[1] / "supabase/migrations/202610260001_accounts.sql"
    text = migration.read_text(encoding="utf-8-sig")
    assert parse_sql(text)
    assert parse_plpgsql(text)


def test_streamlit_account_configuration_guest_reset_and_no_recovery():
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    owner = app.session_state["guest_memory"]["owner_id"]
    app.radio(key="top_nav").set_value("Account").run()
    assert not app.exception
    assert any(ui.RECOVERY_MESSAGE in c.value for c in app.caption)
    assert next(b for b in app.button if b.label == "Sign in").disabled
    next(b for b in app.button if b.label == "Start a new guest session").click().run()
    assert app.session_state["guest_memory"]["owner_id"] != owner
    app.radio(key="top_nav").set_value("Analyze").run()
    next(b for b in app.button if b.label == "Analyze my solution ->").click().run()
    app.radio(key="top_nav").set_value("Account").run()
    assert next(b for b in app.button if b.label == "Start a new guest session").disabled


def test_streamlit_failed_login_clears_password_on_rerun(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    monkeypatch.setattr(ui.AuthConfig, "from_secrets", lambda secrets: auth.AuthConfig("url", "public"))
    def fail(*args, **kwargs):
        raise auth.AccountError("Unable to sign in. Check your credentials and try again.")
    monkeypatch.setattr(ui, "authenticate", fail)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    app.radio(key="top_nav").set_value("Account").run()
    app.text_input(key="login_email").set_value("test@example.invalid")
    app.text_input(key="login_password").set_value("test-only-password")
    next(b for b in app.button if b.label == "Sign in").click().run()
    assert not app.exception
    assert app.text_input(key="login_password").value == ""
    assert any("Unable to sign in" in i.value for i in app.info)


def test_streamlit_login_import_rename_and_logout(monkeypatch):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    client, _, _ = sdk_client()
    session = signed_session(client)
    cloud = CloudFake(session.user_id)
    monkeypatch.setattr(ui.AuthConfig, "from_secrets", lambda secrets: auth.AuthConfig("url", "public"))
    monkeypatch.setattr(ui, "authenticate", lambda *args, **kwargs: session)
    monkeypatch.setattr(ui, "SupabaseProgressStore", lambda session: cloud)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    app.radio(key="top_nav").set_value("Analyze").run()
    next(b for b in app.button if b.label == "Analyze my solution ->").click().run()
    original_id = app.session_state["last_report"]["attempt_id"]
    app.radio(key="top_nav").set_value("Account").run()
    app.text_input(key="login_email").set_value("test@example.invalid")
    app.text_input(key="login_password").set_value("test-password")
    next(b for b in app.button if b.label == "Sign in").click().run()
    assert not app.exception
    assert app.session_state["display_name"] == "Student"
    assert "login_password" not in app.session_state
    assert app.session_state["guest_import"]["owner_id"] == session.user_id
    app.radio(key="top_nav").set_value("Analyze").run()
    assert next(b for b in app.button if b.label == "Analyze my solution ->").disabled
    next(b for b in app.button if b.label == "Save this session to my account").click().run()
    assert not app.exception
    assert cloud.load_attempts()[0]["attempt_id"] == original_id
    app.text_area(key="solution_steps_ALG1-QUAD-001").set_value("x = 99").run()
    app.radio(key="top_nav").set_value("Settings").run()
    app.text_input(key="display_name_input").set_value("Renamed account")
    next(b for b in app.button if b.label == "Save learner settings").click().run()
    assert not app.exception
    assert cloud.load_profile()["display_name"] == "Renamed account"
    assert cloud.load_attempts()[0]["attempt_id"] == original_id
    app.radio(key="top_nav").set_value("Account").run()
    # A solution draft exists from visiting Analyze as the account.
    assert next(b for b in app.button if b.label == "Sign out").disabled
    app.checkbox[0].check().run()
    next(b for b in app.button if b.label == "Sign out").click().run()
    assert not app.exception
    assert "auth_session" not in app.session_state and "last_report" not in app.session_state
    assert not app.session_state["guest_memory"]["attempts"]


@pytest.mark.parametrize("invalid", [False, True])
def test_streamlit_connection_failure_blocks_private_rendering_and_invalid_session_clears(invalid):
    from pathlib import Path
    from streamlit.testing.v1 import AppTest
    client, _, _ = sdk_client()
    session = signed_session(client)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/"app.py"), default_timeout=60).run()
    app.session_state["auth_session"] = session
    app.session_state["last_report"] = {"private": "must never render"}
    failure = auth.InvalidSession("Expired") if invalid else TimeoutError()
    def fail(token):
        raise failure
    client.auth.get_user = fail
    app.run()
    assert not app.exception
    if invalid:
        assert "auth_session" not in app.session_state and "last_report" not in app.session_state
        assert session.client is None and not session.access_token
    else:
        assert app.session_state["auth_session"] is session
        assert any("Retry" in e.value for e in app.error)
        assert not any("Signed in as" in c.value for c in app.caption)
