"""Durable, database-free cumulative visit counter backed by a GitHub JSON file.

Each retained counter-state lifecycle records one *attempted* visit. Account
or guest resets clear that state and can count again within one browser session.
The aggregate counter is
stored in a separate GitHub branch so that normal counters do not redeploy the
app. A GitHub Contents API compare-and-swap (file SHA) protects most concurrent
updates and is retried on conflicts. No visitor identity is stored.

Required Streamlit secret: VISIT_COUNTER_GITHUB_TOKEN (Contents read/write).
Optional: VISIT_COUNTER_REPO and VISIT_COUNTER_BRANCH.
"""
from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import re
import time
from typing import Any, MutableMapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

COUNTER_FILE = "data/visit_counter.json"
DEFAULT_REPOSITORY = "Greenstar22/AI_Math_Mentor"
DEFAULT_BRANCH = "visitor-stats"
REFRESH_SECONDS = 30.0
MAX_UPDATE_ATTEMPTS = 6


class CounterError(Exception):
    """Public-facing counter failure, sanitized of credentials and request data."""


class CounterConflict(CounterError):
    """A simultaneous writer updated the GitHub file before this request."""


@dataclass(frozen=True)
class CounterConfig:
    token: str = ""
    repository: str = DEFAULT_REPOSITORY
    branch: str = DEFAULT_BRANCH

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise CounterError("Invalid visitor counter GitHub repository name.")
        if not self.branch or len(self.branch) > 200 or any(c.isspace() for c in self.branch):
            raise CounterError("Invalid visitor counter storage branch name.")

    @classmethod
    def from_secrets(cls, secrets: Any = None) -> "CounterConfig":
        """Use Streamlit secrets when available; fall back to environment vars.

        Don't read or log a token into UI-visible error messages.
        """
        def setting(key: str, default: str = "") -> str:
            value = None
            if secrets is not None:
                try:
                    value = secrets.get(key)
                except Exception:
                    # Streamlit raises its own exception if no secrets file exists.
                    pass
            if value is None or value == "":
                value = os.environ.get(key, default)
            return str(value).strip()

        return cls(
            token=setting("VISIT_COUNTER_GITHUB_TOKEN"),
            repository=setting("VISIT_COUNTER_REPO", DEFAULT_REPOSITORY),
            branch=setting("VISIT_COUNTER_BRANCH", DEFAULT_BRANCH),
        )


class GitHubVisitCounter:
    """Atomic-by-SHA GitHub Contents REST API visit-counter file."""

    def __init__(self, config: CounterConfig):
        self.config = config

    @property
    def url(self) -> str:
        return (
            f"https://api.github.com/repos/{self.config.repository}/contents/"
            f"{quote(COUNTER_FILE, safe='/')}"
        )

    def _request(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        url = self.url
        if method == "GET":
            url += f"?ref={quote(self.config.branch, safe='')}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MathMentorAI-visit-counter/1.0",
            "Authorization": f"Bearer {self.config.token}",
        }
        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, headers=headers, data=data, method=method)
        try:
            with urlopen(request, timeout=9) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as err:
            if err.code == 404 and method == "GET":
                return None  # New counter file, or absent branch (PUT will fail clearly).
            if err.code == 409 and method == "PUT":
                raise CounterConflict("Another visitor updated the counter.") from None
            if err.code in (401, 403):
                raise CounterError("Counter access denied: check GitHub token permissions and limits.") from None
            if err.code == 404:
                raise CounterError("Counter branch/repository not found. Create the visitor-stats branch first.") from None
            if err.code == 422:
                raise CounterError("GitHub rejected the counter update; check its storage branch and permissions.") from None
            raise CounterError(f"Counter storage returned HTTP {err.code}.") from None
        except (URLError, TimeoutError, OSError) as err:
            raise CounterError("Counter storage is temporarily unreachable.") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise CounterError("Counter storage returned an unreadable response.") from None

    def read_file(self) -> tuple[int, str | None]:
        """Return (persisted total, GitHub file SHA). Never silently discard corruption."""
        payload = self._request("GET")
        if payload is None:
            return (0, None)
        try:
            sha = payload["sha"]
            raw = base64.b64decode(payload["content"], validate=False)
            doc = json.loads(raw.decode("utf-8"))
            count = doc["total_visits"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("Invalid total_visits")
            if not isinstance(sha, str) or not sha:
                raise ValueError("Invalid GitHub file SHA")
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError):
            raise CounterError("The counter file is invalid. Restore a valid nonnegative total_visits integer.") from None
        return (count, sha)

    def increment(self) -> int:
        """Add one visit in the remote file; retry SHA conflicts, but not network timeouts.

        Retrying ambiguous timeouts is avoided because a commit may have landed
        even when the client never received its response.
        """
        for attempt in range(MAX_UPDATE_ATTEMPTS):
            current, sha = self.read_file()
            new_total = current + 1
            doc = {
                "schema_version": 1,
                "total_visits": new_total,
                "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "description": "Cumulative app visit sessions; no visitor personal data stored.",
            }
            request: dict[str, Any] = {
                "message": "chore(visitor-stats): add MathMentor AI app visit [skip ci]",
                "content": base64.b64encode(
                    (json.dumps(doc, indent=2) + "\n").encode("utf-8")
                ).decode("ascii"),
                "branch": self.config.branch,
            }
            if sha is not None:
                request["sha"] = sha
            try:
                self._request("PUT", request)
                return new_total
            except CounterConflict:
                if attempt == MAX_UPDATE_ATTEMPTS - 1:
                    raise CounterError("The counter is busy; please try a new session later.") from None
                time.sleep(0.08 * (attempt + 1))
        raise CounterError("The counter could not be updated.")

    def read_total(self) -> int:
        return self.read_file()[0]


@dataclass(frozen=True)
class CounterSnapshot:
    total: int | None
    status: str  # live | cached | setup | unavailable
    message: str


def snapshot_for_session(
    state: MutableMapping[str, Any],
    counter: GitHubVisitCounter | None,
    *,
    now: float | None = None,
) -> CounterSnapshot:
    """Increment once per retained counter state; refresh without another increment.

    The attempted flag is set before the network call so a rerun following a
    partially successful/ambiguous request won't blindly add a duplicate visit.
    """
    if counter is None:
        return CounterSnapshot(None, "setup", "One-time GitHub token setup required")

    clock = time.monotonic() if now is None else now
    key = "_mathmentor_visits_"
    if not state.get(key + "attempted", False):
        state[key + "attempted"] = True
        state[key + "last_fetch"] = clock
        try:
            total = counter.increment()
            state[key + "total"] = total
            state[key + "successful"] = True
            return CounterSnapshot(total, "live", "Cumulative app sessions · stored in GitHub")
        except CounterError as err:
            state[key + "successful"] = False
            return CounterSnapshot(None, "unavailable", str(err))

    old_total = state.get(key + "total")
    if old_total is not None and not isinstance(old_total, int):
        old_total = None
    if clock - state.get(key + "last_fetch", float("-inf")) >= REFRESH_SECONDS:
        state[key + "last_fetch"] = clock
        try:
            latest = counter.read_total()
            # Never regress within one browser session if someone changed the file.
            total = max(int(old_total or 0), latest)
            if total > 0:
                state[key + "total"] = total
                return CounterSnapshot(total, "live", "Cumulative app sessions · stored in GitHub")
        except CounterError:
            pass
        return CounterSnapshot(old_total if old_total and old_total > 0 else None,
                               "cached" if old_total else "unavailable",
                               "Last known total" if old_total else "Counter temporarily unavailable")

    if isinstance(old_total, int) and old_total > 0:
        return CounterSnapshot(old_total, "live" if state.get(key + "successful") else "cached",
                               "Cumulative app sessions · stored in GitHub" if state.get(key + "successful")
                               else "Last known total")
    return CounterSnapshot(None, "unavailable", "Counter temporarily unavailable")
