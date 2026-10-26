"""Session-local Supabase Auth. All outward errors deliberately omit provider details."""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
import time
from uuid import UUID


class AccountError(Exception):
    pass


class InvalidSession(AccountError):
    pass


class ConnectionUnavailable(AccountError):
    pass


@dataclass(repr=False)
class AuthConfig:
    url: str = ""
    publishable_key: str = ""

    @property
    def available(self):
        return bool(self.url and self.publishable_key)

    @classmethod
    def from_secrets(cls, secrets):
        try:
            section = secrets.get("supabase", {})
            return cls(str(section.get("url", "")), str(section.get("publishable_key", "")))
        except Exception:
            return cls()


def ordinary_client(config):
    if not config.available:
        raise AccountError("Account configuration is unavailable. Guest mode remains available.")
    from supabase import create_client, ClientOptions
    return create_client(config.url, config.publishable_key, options=ClientOptions(
        auto_refresh_token=False, persist_session=True, postgrest_client_timeout=15,
    ))


def translate_error(exc):
    status = str(getattr(exc, "status", getattr(exc, "status_code", "")))
    code = str(getattr(exc, "code", ""))
    if status in {"400", "401", "403", "404", "422"} or code in {
        "bad_jwt", "session_not_found", "refresh_token_not_found", "refresh_token_already_used",
        "user_not_found", "PGRST301", "PGRST302", "PGRST303",
    }:
        return InvalidSession("Your session is no longer valid. Sign in again.")
    return ConnectionUnavailable("Account service is unavailable. Retry when connectivity returns.")


@dataclass(repr=False)
class AuthSession:
    client: object
    user_id: str
    email: str
    access_token: str
    refresh_token: str
    expires_at: float
    lock: object = field(default_factory=RLock)

    def _retain(self, session):
        if not session or not session.access_token or not session.refresh_token:
            raise InvalidSession("No authenticated session was returned. Sign in again.")
        self.access_token = session.access_token
        self.refresh_token = session.refresh_token
        self.expires_at = session.expires_at or 0

    def validate(self):
        # A single lock covers refresh rotation, validation and each protected operation.
        with self.lock:
            try:
                if self.expires_at <= time.time() + 60:
                    self._retain(self.client.auth.refresh_session(self.refresh_token).session)
                user = self.client.auth.get_user(self.access_token).user
                if not user or str(UUID(str(user.id))) != self.user_id:
                    raise InvalidSession("Account identity changed. Sign in again.")
                self.email = user.email or ""
                self.client.postgrest.auth(self.access_token)
                return user
            except AccountError:
                raise
            except Exception as exc:
                raise translate_error(exc) from None

    def protected(self, operation):
        with self.lock:
            self.validate()
            try:
                return operation(self.client)
            except AccountError:
                raise
            except Exception as exc:
                error = translate_error(exc)
                if isinstance(error, InvalidSession):
                    raise error from None
                raise AccountError("The progress operation failed. Your pending work is retained; retry saving.") from None


def authenticate(config, email, password, *, signup=False, factory=ordinary_client):
    if signup and len(password) < 12:
        raise AccountError("Use a password of at least 12 characters.")
    try:
        client = factory(config)
        credentials = {"email": email.strip(), "password": password}
        response = client.auth.sign_up(credentials) if signup else client.auth.sign_in_with_password(credentials)
        session = response.session
        if not session or not getattr(session, "access_token", None) or not getattr(session, "refresh_token", None):
            if signup:
                raise AccountError("Signup did not establish a session. Check that Confirm email is OFF in Supabase.")
            raise AccountError("Unable to sign in. Check your credentials and try again.")
        user = client.auth.get_user(session.access_token).user
        if not user:
            raise InvalidSession("Unable to validate the authenticated session.")
        owner = str(UUID(str(user.id)))
        result = AuthSession(client, owner, user.email or "", session.access_token,
                             session.refresh_token, session.expires_at or 0)
        result.validate()
        return result
    except AccountError:
        raise
    except Exception:
        raise AccountError("Unable to sign up. Check your details and try again." if signup else
                           "Unable to sign in. Check your credentials and try again.") from None


def logout(session):
    try:
        with session.lock:
            # The SDK's high-level sign_out suppresses AuthApiError. Its public
            # revocation API calls the same endpoint without hiding failures.
            # This uses the ordinary user's token, never an administrator key.
            session.client.auth.admin.sign_out(session.access_token, "local")
        return True
    except Exception:
        return False
    finally:
        session.access_token = session.refresh_token = ""
        session.client = None


def delete_account(session, config, password, secrets, *, factory=ordinary_client, admin_factory=None):
    """The only path that reads or uses the administrator secret. No target from a form."""
    session.validate()
    verified = authenticate(config, session.email, password, factory=factory)
    if verified.user_id != session.user_id:
        logout(verified)
        raise AccountError("Reauthentication did not match the current account.")
    try:
        section = secrets.get("supabase", {})
        secret = section.get("secret_key", "")
        if not secret:
            raise AccountError("Account deletion is unavailable: administrator configuration is incomplete.")
        if admin_factory is None:
            from supabase import create_client, ClientOptions
            admin = create_client(config.url, secret, options=ClientOptions(
                auto_refresh_token=False, persist_session=False,
            ))
        else:
            admin = admin_factory(config.url, secret)
        # Never attach an ordinary access token to this isolated client.
        admin.auth.admin.delete_user(session.user_id, should_soft_delete=False)
    except AccountError:
        raise
    except Exception:
        raise AccountError("Account deletion failed. Your account has not been reported as deleted; retry.") from None
    finally:
        logout(verified)
