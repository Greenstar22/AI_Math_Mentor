"""Offline tests never consume the developer's real Streamlit credentials."""
import pytest


@pytest.fixture(autouse=True)
def offline_secrets(monkeypatch):
    import streamlit as st
    monkeypatch.setattr(st, "secrets", {})
