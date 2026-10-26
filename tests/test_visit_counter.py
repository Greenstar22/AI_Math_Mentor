"""No network needed: exercise remote JSON read/write and Streamlit session rules."""
from __future__ import annotations

import base64
import json
from types import SimpleNamespace

import pytest

from visit_counter import (
    CounterConfig,
    CounterConflict,
    CounterError,
    DEFAULT_BRANCH,
    GitHubVisitCounter,
    snapshot_for_session,
)


class FakeGitHubCounter(GitHubVisitCounter):
    def __init__(self, starting=0):
        super().__init__(CounterConfig(token="fake_test_token"))
        self.total = starting
        self.sha = "sha-1"
        self.writes = 0
        self.conflicts = 0

    def _request(self, method, payload=None):
        if method == "GET":
            return {
                "sha": self.sha,
                "content": base64.b64encode(json.dumps({"total_visits": self.total}).encode()).decode(),
            }
        assert method == "PUT"
        if self.conflicts:
            self.conflicts -= 1
            self.total += 1  # a different visitor won the race
            self.sha = f"sha-{self.total + 1}"
            raise CounterConflict("Concurrent update")
        assert payload["branch"] == DEFAULT_BRANCH
        assert payload["sha"] == self.sha
        content = json.loads(base64.b64decode(payload["content"]))
        assert content["total_visits"] == self.total + 1
        assert "visitor" not in content  # only aggregates; no personal IDs
        self.total = content["total_visits"]
        self.sha = f"sha-{self.total + 1}"
        self.writes += 1
        return {"content": {"sha": self.sha}}


def test_counter_increment_and_persist_between_sessions():
    fake = FakeGitHubCounter()
    first_session = {}
    initial = snapshot_for_session(first_session, fake, now=10)
    assert initial.total == 1
    assert initial.status == "live"
    for _ in range(10):
        snapshot_for_session(first_session, fake, now=12)
    assert fake.total == 1
    assert fake.writes == 1

    second_session = {}
    assert snapshot_for_session(second_session, fake, now=15).total == 2
    assert fake.total == 2
    refreshed = snapshot_for_session(first_session, fake, now=45)
    assert refreshed.total == 2
    assert fake.writes == 2


def test_simulated_concurrent_update_is_retried():
    fake = FakeGitHubCounter(starting=7)
    fake.conflicts = 2
    assert fake.increment() == 10  # 7 + 2 concurrent visitors + this session
    assert fake.total == 10
    assert fake.writes == 1


def test_no_token_no_false_zero_or_unauthorized_write():
    session = {}
    snapshot = snapshot_for_session(session, None)
    assert snapshot.status == "setup"
    assert snapshot.total is None
    assert not session  # nothing marked as counted


def test_network_failure_does_not_duplicate_visit_on_rerun():
    class BrokenCounter(FakeGitHubCounter):
        def increment(self):
            self.writes += 1
            raise CounterError("GitHub unavailable")
    counter = BrokenCounter()
    session = {}
    first = snapshot_for_session(session, counter, now=1)
    another_run = snapshot_for_session(session, counter, now=2)
    assert first.total is None
    assert another_run.total is None
    assert counter.writes == 1


def test_validates_bad_remote_counter_without_resetting_to_zero():
    fake = FakeGitHubCounter()
    fake.total = -1
    with pytest.raises(CounterError, match="invalid"):
        fake.increment()


def test_counter_config_default_and_custom_secrets():
    default = CounterConfig()
    assert default.repository == "Greenstar22/AI_Math_Mentor"
    assert GitHubVisitCounter(default).url == (
        "https://api.github.com/repos/Greenstar22/AI_Math_Mentor/contents/data/visit_counter.json"
    )
    config = CounterConfig.from_secrets({
        "VISIT_COUNTER_GITHUB_TOKEN": "test_secret",
        "VISIT_COUNTER_REPO": "example-owner/example-counter",
        "VISIT_COUNTER_BRANCH": "visitor-stats",
    })
    assert config.token == "test_secret"
    assert config.repository == "example-owner/example-counter"
    assert config.branch == DEFAULT_BRANCH
    with pytest.raises(CounterError):
        CounterConfig(repository="other example")


def test_last_known_never_drops_to_zero_on_remote_reset():
    backend = FakeGitHubCounter(starting=100)
    session = {}
    assert snapshot_for_session(session, backend, now=0).total == 101
    backend.total = 0
    assert snapshot_for_session(session, backend, now=35).total == 101
