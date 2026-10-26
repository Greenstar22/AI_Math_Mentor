"""Offline tests never consume the developer's real Streamlit credentials."""
import pytest


@pytest.fixture(autouse=True)
def offline_secrets(monkeypatch):
    import streamlit as st
    monkeypatch.setattr(st, "secrets", {})
    # The counter also accepts environment overrides; never use real credentials
    # merely because the developer has exported them in the launching shell.
    for name in ("VISIT_COUNTER_GITHUB_TOKEN", "VISIT_COUNTER_REPO", "VISIT_COUNTER_BRANCH"):
        monkeypatch.delenv(name, raising=False)
