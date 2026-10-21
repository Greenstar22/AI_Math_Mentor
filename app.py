from __future__ import annotations

import hashlib
import html
import json
import random
from typing import Any

import pandas as pd
import streamlit as st

from visit_counter import CounterConfig, CounterError, CounterSnapshot, GitHubVisitCounter, snapshot_for_session

from math_mentor import (
    ADVISOR,
    AUTHOR,
    FEEDBACK_STYLES,
    PROBLEM_BANK,
    PROBLEMS_BY_ID,
    StudentProfile,
    load_student_history,
    record_feedback_reward,
    report_to_markdown,
    run_mentor_attempt,
    weakness_summary,
)

GITHUB_URL = "https://github.com/qxiao2ub/AI_Math_Mentor"
LIVE_APP_URL = "https://math-ai-mentor.streamlit.app/"
PAGE_ORDER = ["Home", "Analyze", "Mastery", "About", "Settings"]
LEVEL_OPTIONS = ["beginner", "intermediate", "advanced"]
TOPICS = sorted({problem.topic for problem in PROBLEM_BANK})

DEFAULT_STEPS = {
    "ARITH-001": "3/4 + 2/3\n9/12 + 8/12\n17/12\n1 + 5/12",
    "ALG-LIN-001": "2*x + 3 = 11\n2*x = 8\nx = 4",
    "ALG-QUAD-001": "x**2 - 5*x + 6 = 0\n(x - 2)*(x - 3) = 0\nx = 2\nx = 3",
    "CALC-DERIV-001": "Derivative(x**3 - 4*x + 7, x)\n3*x**2 - 4 + 0\n3*x**2 - 4",
    "PROB-001": "P_none = (1/2)**2\nP_at_least_one = 1 - P_none\nP_at_least_one = 3/4",
    "DE-EXP-001": "1/y\nlog(y) = 3*t + C\ny = C*exp(3*t)\ny = 2*exp(3*t)",
}

st.set_page_config(
    page_title="MathMentor AI | Anchit Nayak",
    page_icon="\U0001F9E0",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "top_nav": "Home",
        "theme": "Dark",
        "display_name": "Demo Student",
        "grade_band": "Grades 9-12",
        "preferred_feedback": "socratic",
        "school_class": "",
        "accessibility_notes": "",
        "problem_selector": "ALG-QUAD-001",
        "feedback_recorded": False,
    }
    for topic in TOPICS:
        defaults[f"level_{topic}"] = "intermediate" if topic in {"Algebra", "Probability"} else "beginner"
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    requested = st.session_state.pop("_nav_request", None)
    if requested in PAGE_ORDER:
        st.session_state["top_nav"] = requested


def safe_student_id(display_name: str) -> str:
    base = (display_name or "student").strip().lower().encode("utf-8")
    return "streamlit_" + hashlib.sha256(base).hexdigest()[:12]


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def go_to(page: str) -> None:
    st.session_state["_nav_request"] = page
    st.rerun()


def current_profile() -> StudentProfile:
    return StudentProfile(
        student_id=safe_student_id(st.session_state["display_name"]),
        display_name=st.session_state["display_name"] or "Student",
        grade_band=st.session_state["grade_band"],
        current_levels={topic: st.session_state[f"level_{topic}"] for topic in TOPICS},
        preferred_feedback=st.session_state["preferred_feedback"],
        accessibility_notes=st.session_state["accessibility_notes"],
    )

def update_current_profile() -> None:
    st.session_state["display_name"] = st.session_state["display_name_input"]
    st.session_state["grade_band"] = st.session_state["grade_band_input"]
    st.session_state["school_class"] = st.session_state["school_class_input"]
    st.session_state["preferred_feedback"] = st.session_state["preferred_feedback_input"]
    st.session_state["accessibility_notes"] = st.session_state["accessibility_notes_input"]
    for topic in TOPICS:
        st.session_state[f"level_{topic}"] = st.session_state[f"level_{topic}_input"]


def update_topic_level(topic: str) -> None:
    st.session_state[f"level_{topic}"] = st.session_state[f"mastery_level_{topic}_input"]


def update_theme() -> None:
    st.session_state["theme"] = st.session_state["theme_input"]


def inject_css() -> None:
    dark = st.session_state["theme"] == "Dark"
    if dark:
        colors = {
            "bg": "#080808",
            "fg": "#f7f7f7",
            "surface": "#121212",
            "surface2": "#181818",
            "muted": "#a6a6a6",
            "border": "#292929",
            "primary": "#0047ff",
            "primary2": "#2e6bff",
            "danger": "#ff4b55",
            "shadow": "rgba(0,71,255,.18)",
        }
    else:
        colors = {
            "bg": "#fafafa",
            "fg": "#111111",
            "surface": "#ffffff",
            "surface2": "#eef1f7",
            "muted": "#5f6572",
            "border": "#d8dce5",
            "primary": "#003ed1",
            "primary2": "#0b55ff",
            "danger": "#d62436",
            "shadow": "rgba(0,62,209,.14)",
        }

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&display=swap');
        :root {{
            --mm-bg: {colors['bg']};
            --mm-fg: {colors['fg']};
            --mm-surface: {colors['surface']};
            --mm-surface-2: {colors['surface2']};
            --mm-muted: {colors['muted']};
            --mm-border: {colors['border']};
            --mm-primary: {colors['primary']};
            --mm-primary-2: {colors['primary2']};
            --mm-danger: {colors['danger']};
            --mm-shadow: {colors['shadow']};
        }}
        html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
        html {{ scroll-behavior: smooth; }}
        body {{ background: var(--mm-bg); color: var(--mm-fg); }}
        .stApp {{
            background:
                radial-gradient(circle at 88% 4%, var(--mm-shadow), transparent 26rem),
                var(--mm-bg);
            color: var(--mm-fg);
        }}
        [data-testid="stHeader"], [data-testid="stToolbar"], footer {{ display: none !important; }}
        [data-testid="stAppViewContainer"] > .main {{ background: transparent; }}
        .block-container {{ max-width: 1280px; padding: 1.4rem 2rem 3rem; }}
        h1, h2, h3, h4, h5, h6, .mm-display {{
            font-family: 'Archivo Black', 'Arial Black', sans-serif !important;
            letter-spacing: -0.045em;
            color: var(--mm-fg);
        }}
        p, li, label, .stMarkdown {{ color: var(--mm-fg); }}
        a {{ color: var(--mm-primary-2); }}
        hr {{ border-color: var(--mm-border) !important; }}
        .mm-nav-shell {{
            border: 1px solid var(--mm-border);
            border-left: 4px solid var(--mm-primary);
            background: color-mix(in srgb, var(--mm-bg) 88%, transparent);
            box-shadow: 0 12px 48px rgba(0,0,0,.14);
            padding: 1rem 1.15rem;
            margin-bottom: .3rem;
        }}
        .mm-visitbar {{
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: .6rem 1.15rem;
            margin-bottom: 1rem;
            padding: .75rem 1.05rem;
            background: linear-gradient(100deg, var(--mm-surface), var(--mm-bg));
            border: 1px solid var(--mm-border);
            border-left: 3px solid var(--mm-primary);
        }}
        .mm-visitlabel {{ color: var(--mm-muted); font-size: .65rem; font-weight: 700; letter-spacing: .15em; text-transform: uppercase; }}
        .mm-visitpill {{ display: inline-flex; align-items: baseline; gap: .55rem; flex-wrap: wrap; }}
        .mm-visitnum {{ color: var(--mm-fg); font-family: 'Archivo Black', 'Arial Black', sans-serif; font-size: 1.75rem; letter-spacing: -.04em; line-height: 1; }}
        .mm-visitdesc {{ color: var(--mm-primary-2); font-size: .70rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }}
        .mm-visitstatus {{ color: var(--mm-muted); font-size: .69rem; }}
        .mm-visitdot {{ color: var(--mm-primary-2); font-size: .8rem; margin-right: .22rem; }}
        .mm-footer-visits {{ display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: .5rem; margin: 1.3rem auto 0; color: var(--mm-muted); font-size: .74rem; letter-spacing: .1em; text-transform: uppercase; }}
        .mm-footer-visits strong {{ color: var(--mm-primary-2); font-size: 1.1rem; font-family: 'Archivo Black', sans-serif; }}
        .mm-brand {{ font-family: 'Archivo Black', 'Arial Black', sans-serif; font-size: 1.2rem; letter-spacing: -.04em; }}
        .mm-brand span, .mm-accent {{ color: var(--mm-primary-2); }}
        .mm-byline {{ color: var(--mm-muted); font-size: .68rem; letter-spacing: .15em; text-transform: uppercase; margin-top: .35rem; }}
        .st-key-top_nav div[role="radiogroup"] {{ justify-content: flex-end; gap: .25rem; flex-wrap: wrap; }}
        .st-key-top_nav label {{
            padding: .48rem .72rem !important;
            border: 1px solid transparent;
            color: var(--mm-muted) !important;
            text-transform: uppercase;
            letter-spacing: .1em;
            font-size: .73rem !important;
            font-weight: 700;
        }}
        .st-key-top_nav label > div:first-child {{ display: none !important; }}
        .st-key-top_nav label:has(input:checked) {{ color: var(--mm-primary-2) !important; border-color: var(--mm-primary); background: var(--mm-surface); }}
        .mm-hero {{ padding: clamp(4rem, 9vw, 8rem) 0 clamp(3rem, 7vw, 6rem); border-bottom: 1px solid var(--mm-border); }}
        .mm-display-title {{
            font-family: 'Archivo Black', 'Arial Black', sans-serif;
            font-size: clamp(3.2rem, 8.8vw, 7.7rem);
            line-height: .87;
            letter-spacing: -.065em;
            margin: 0 0 2.2rem;
            max-width: 1100px;
            color: var(--mm-fg);
        }}
        .mm-lead {{ color: var(--mm-muted); font-size: clamp(1.05rem, 2vw, 1.45rem); line-height: 1.65; max-width: 760px; }}
        .mm-kicker {{ color: var(--mm-muted); font-size: .7rem; text-transform: uppercase; letter-spacing: .2em; font-weight: 700; margin-bottom: .8rem; }}
        .mm-section {{ padding: clamp(3.5rem, 7vw, 6.5rem) 0; border-bottom: 1px solid var(--mm-border); }}
        .mm-section-title {{ font-size: clamp(2.1rem, 4.5vw, 4.6rem); line-height: .95; margin: 0 0 1.5rem; }}
        .mm-panel, .mm-card, div[data-testid="stMetric"], div[data-testid="stExpander"], [data-testid="stForm"] {{
            background: color-mix(in srgb, var(--mm-surface) 92%, transparent) !important;
            border: 1px solid var(--mm-border) !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }}
        .mm-panel {{ padding: clamp(1.25rem, 2.5vw, 2.2rem); }}
        .mm-card {{ padding: 1.5rem; height: 100%; transition: border-color .18s ease, transform .18s ease, box-shadow .18s ease; }}
        .mm-card:hover {{ border-color: var(--mm-primary) !important; transform: translateY(-2px); box-shadow: 0 14px 40px var(--mm-shadow) !important; }}
        .mm-step-number {{ font-family: 'Archivo Black', sans-serif; color: var(--mm-primary-2); font-size: 3.6rem; line-height: 1; margin-bottom: 1rem; }}
        .mm-card-title {{ font-family: 'Archivo Black', sans-serif; color: var(--mm-fg); font-size: 1.35rem; line-height: 1.05; margin-bottom: .8rem; }}
        .mm-card-copy {{ color: var(--mm-muted); line-height: 1.65; font-size: .98rem; }}
        .mm-mock {{ margin-top: 1.25rem; padding: 1rem; background: var(--mm-bg); border: 1px solid var(--mm-border); color: var(--mm-fg); min-height: 8rem; }}
        .mm-mock-label {{ color: var(--mm-muted); font-size: .65rem; text-transform: uppercase; letter-spacing: .15em; margin-bottom: .75rem; }}
        .mm-profile-strip {{ display: flex; flex-wrap: wrap; gap: .55rem; margin: 1.5rem 0 2rem; }}
        .mm-chip {{ border: 1px solid var(--mm-border); background: var(--mm-surface); color: var(--mm-muted); padding: .45rem .65rem; font-size: .72rem; letter-spacing: .08em; text-transform: uppercase; }}
        .mm-chip strong {{ color: var(--mm-fg); }}
        .mm-problem {{ padding: 1.4rem; border: 1px solid var(--mm-border); border-left: 4px solid var(--mm-primary); background: var(--mm-surface); margin: .8rem 0 1.25rem; }}
        .mm-problem-text {{ font-size: clamp(1.25rem, 2.2vw, 1.8rem); line-height: 1.35; color: var(--mm-fg); margin: .6rem 0; }}
        .mm-meta {{ color: var(--mm-muted); font-size: .72rem; text-transform: uppercase; letter-spacing: .12em; }}
        .mm-review-card {{ padding: 1.35rem; border: 1px solid var(--mm-border); border-left: 4px solid var(--mm-primary); background: var(--mm-surface); margin-bottom: 1rem; }}
        .mm-review-card.bad {{ border-left-color: var(--mm-danger); }}
        .mm-review-top {{ display: flex; flex-wrap: wrap; gap: .75rem 1.25rem; align-items: center; margin-bottom: .85rem; }}
        .mm-label {{ color: var(--mm-muted); font-size: .67rem; text-transform: uppercase; letter-spacing: .14em; }}
        .mm-label.good {{ color: var(--mm-primary-2); }}
        .mm-label.bad {{ color: var(--mm-danger); }}
        .mm-submitted {{ color: var(--mm-fg); font-size: 1.12rem; font-weight: 600; margin-bottom: 1rem; overflow-wrap: anywhere; }}
        .mm-detail-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem; margin-bottom: 1rem; }}
        .mm-detail {{ border: 1px solid var(--mm-border); background: var(--mm-bg); padding: .85rem; }}
        .mm-detail-value {{ color: var(--mm-fg); margin-top: .3rem; overflow-wrap: anywhere; }}
        .mm-mentor-note {{ border-left: 2px solid var(--mm-primary); padding-left: .85rem; color: var(--mm-primary-2); line-height: 1.55; }}
        .mm-progress-track {{ height: .52rem; border: 1px solid var(--mm-border); background: var(--mm-bg); margin: .65rem 0 .45rem; }}
        .mm-progress-fill {{ height: 100%; background: var(--mm-primary); }}
        .mm-workflow {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .8rem; }}
        .mm-workflow-card {{ border: 1px solid var(--mm-border); background: var(--mm-surface); padding: 1.1rem; min-height: 10.5rem; }}
        .mm-workflow-index {{ color: var(--mm-primary-2); font-family: 'Archivo Black', sans-serif; font-size: 1.7rem; }}
        .mm-workflow-title {{ font-weight: 700; color: var(--mm-fg); margin: .7rem 0 .45rem; }}
        .mm-workflow-copy {{ color: var(--mm-muted); font-size: .85rem; line-height: 1.5; }}
        .mm-footer {{ padding: 4.5rem 0 1rem; }}
        .mm-footer-mark {{ font-family: 'Archivo Black', sans-serif; font-size: clamp(3.3rem, 11vw, 9rem); line-height: .82; letter-spacing: -.075em; text-align: center; border-bottom: 1px solid var(--mm-border); padding-bottom: 3rem; }}
        .mm-footer-copy {{ text-align: center; color: var(--mm-muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .1em; padding-top: 1.5rem; }}
        .stButton > button, .stDownloadButton > button, [data-testid="stLinkButton"] a {{
            border-radius: 0 !important;
            border: 1px solid var(--mm-border) !important;
            background: var(--mm-surface) !important;
            color: var(--mm-fg) !important;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-weight: 700;
            min-height: 2.8rem;
            transition: all .18s ease;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover, [data-testid="stLinkButton"] a:hover {{ border-color: var(--mm-primary) !important; color: var(--mm-primary-2) !important; box-shadow: 0 10px 30px var(--mm-shadow); }}
        .stButton > button[kind="primary"] {{ background: var(--mm-primary) !important; border-color: var(--mm-primary) !important; color: white !important; }}
        input, textarea, [data-baseweb="select"] > div {{
            background: var(--mm-bg) !important;
            color: var(--mm-fg) !important;
            border-color: var(--mm-border) !important;
            border-radius: 0 !important;
        }}
        [data-testid="stMetricValue"] {{ color: var(--mm-fg); font-family: 'Archivo Black', sans-serif; }}
        [data-testid="stMetricLabel"] {{ color: var(--mm-muted); text-transform: uppercase; letter-spacing: .08em; }}
        [data-testid="stDataFrame"] {{ border: 1px solid var(--mm-border); }}
        div[data-testid="stProgress"] > div > div > div {{ background: var(--mm-primary); }}
        .stAlert {{ border-radius: 0 !important; }}
        @media (max-width: 900px) {{
            .block-container {{ padding: 1rem 1rem 2.5rem; }}
            .mm-workflow {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
            .mm-detail-grid {{ grid-template-columns: 1fr; }}
            .st-key-top_nav div[role="radiogroup"] {{ justify-content: flex-start; }}
        }}
        @media (max-width: 560px) {{
            .mm-display-title {{ font-size: 3.25rem; }}
            .mm-workflow {{ grid-template-columns: 1fr; }}
            .mm-footer-mark {{ font-size: 3.4rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def current_visit_snapshot() -> CounterSnapshot:
    """Record one new-session visit and load a globally persisted count.

    The file is stored on a separate GitHub branch, never on ephemeral cloud
    disk. If the token isn't configured, the app remains usable and honestly
    displays a dash / setup message rather than pretending its total is 0.
    """
    try:
        config = CounterConfig.from_secrets(st.secrets)
        backend = GitHubVisitCounter(config) if config.token else None
        return snapshot_for_session(st.session_state, backend)
    except CounterError as err:
        return CounterSnapshot(None, "unavailable", str(err))


def render_visit_bar(snapshot: CounterSnapshot) -> None:
    value = f"{snapshot.total:,}" if snapshot.total is not None and snapshot.total > 0 else "—"
    status = {
        "live": "LIVE / PERSISTENT",
        "cached": "LAST KNOWN TOTAL",
        "setup": "SETUP REQUIRED",
        "unavailable": "TEMPORARILY UNAVAILABLE",
    }.get(snapshot.status, "STATUS UNKNOWN")
    st.markdown(
        f'''<div class="mm-visitbar" role="status" aria-live="polite">
            <div class="mm-visitlabel"><span class="mm-visitdot">●</span> MathMentor AI · Community activity</div>
            <div class="mm-visitpill"><span class="mm-visitnum">{esc(value)}</span><span class="mm-visitdesc">Cumulative App Visits</span></div>
            <div class="mm-visitstatus" title="{esc(snapshot.message)}">{esc(status)}</div>
        </div>''',
        unsafe_allow_html=True,
    )


def render_navigation() -> str:
    left, right = st.columns([1.25, 3.75])
    with left:
        st.markdown(
            f"""
            <div class="mm-nav-shell">
                <div class="mm-brand">MATHMENTOR <span>AI</span></div>
                <div class="mm-byline">Author {esc(AUTHOR)}<br>Advisor {esc(ADVISOR)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        return st.radio(
            "Primary navigation",
            PAGE_ORDER,
            horizontal=True,
            label_visibility="collapsed",
            key="top_nav",
        )


def render_page_header(title: str, subtitle: str, accent: str | None = None) -> None:
    shown = esc(title)
    if accent and accent in title:
        shown = esc(title).replace(esc(accent), f'<span class="mm-accent">{esc(accent)}</span>')
    st.markdown(
        f"""
        <section class="mm-hero">
            <div class="mm-kicker">MathMentor AI prototype</div>
            <h1 class="mm-display-title">{shown}</h1>
            <p class="mm-lead">{esc(subtitle)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_profile_strip(profile: StudentProfile) -> None:
    chips = [
        f"Student <strong>{esc(profile.display_name)}</strong>",
        f"Grade <strong>{esc(profile.grade_band)}</strong>",
        f"Feedback <strong>{esc(profile.preferred_feedback.replace('_', ' '))}</strong>",
    ]
    chips.extend(
        f"{esc(topic)} <strong>{esc(level)}</strong>"
        for topic, level in profile.current_levels.items()
        if topic in {"Algebra", "Calculus", "Probability", "Differential Equations"}
    )
    st.markdown(
        '<div class="mm-profile-strip">' + "".join(f'<div class="mm-chip">{item}</div>' for item in chips) + "</div>",
        unsafe_allow_html=True,
    )


def render_home() -> None:
    st.markdown(
        """
        <section class="mm-hero">
            <div class="mm-kicker">Step-level mathematical feedback</div>
            <h1 class="mm-display-title">Solve it.<br><span class="mm-accent">Then understand it.</span></h1>
            <p class="mm-lead">MathMentor AI reviews your solution step by step, pinpoints exactly where the reasoning changes, explains how to repair it, and builds a living mastery profile as you improve.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, _ = st.columns([1.35, 1.2, 2.45])
    with c1:
        if st.button("Start analyzing ->", type="primary", use_container_width=True):
            go_to("Analyze")
    with c2:
        if st.button("See how it works", use_container_width=True):
            go_to("About")

    st.markdown(
        """
        <section class="mm-section">
            <div class="mm-kicker">How it works</div>
            <h2 class="mm-section-title">Three steps to <span class="mm-accent">mastery</span></h2>
        </section>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    cards = [
        (
            "01",
            "Enter the problem",
            "Choose a calibrated problem from the built-in bank. The profile and stated level help match the challenge to the learner.",
            "<div class='mm-mock-label'>Your problem</div><strong>Solve for x: 3x&sup2; - 12x + 9 = 0</strong><div style='height:4px;width:80px;background:var(--mm-primary);margin-top:1.25rem'></div>",
        ),
        (
            "02",
            "Show your work",
            "Write one mathematical step per line. The system reads the submitted pathway instead of returning an answer without context.",
            "<div class='mm-mock-label'>Your solution</div>1. Factor out 3<br>2. Factor the quadratic<br>3. State both roots",
        ),
        (
            "03",
            "Get targeted feedback",
            "Each step is checked symbolically, diagnosed, explained, stored in the attempt history, and used to recommend the next problem.",
            "<div class='mm-mock-label'>Review</div><span style='color:var(--mm-primary-2)'>Correct: steps 1-2</span><br><span style='color:var(--mm-danger)'>Revise: one root is missing</span>",
        ),
    ]
    for col, (number, title, copy, mock) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div class="mm-card">
                    <div class="mm-step-number">{number}</div>
                    <div class="mm-card-title">{title}</div>
                    <div class="mm-card-copy">{copy}</div>
                    <div class="mm-mock">{mock}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <section class="mm-section">
            <div class="mm-kicker">Get started</div>
            <h2 class="mm-section-title">Pick your <span class="mm-accent">path</span></h2>
        </section>
        """,
        unsafe_allow_html=True,
    )
    options = [
        ("Analyze", "Analyze a problem", "Open the full workspace and receive a scored, step-by-step review."),
        ("Mastery", "View your mastery", "See attempts, weak concepts, current mastery, and topic-level progress."),
        ("About", "Explore the workflow", "Understand the symbolic, ML, database, personalization, and feedback pipeline."),
        ("Settings", "Personalize the tutor", "Set level, grade band, feedback style, accessibility notes, and appearance."),
    ]
    for col, (page, title, copy) in zip(st.columns(4), options):
        with col:
            st.markdown(f'<div class="mm-card"><div class="mm-card-title">{esc(title)}</div><div class="mm-card-copy">{esc(copy)}</div></div>', unsafe_allow_html=True)
            if st.button("Go ->", key=f"home_{page}", use_container_width=True):
                go_to(page)


def render_review(report: dict[str, Any], profile: StudentProfile) -> None:
    scores = report["scores"]
    st.markdown('<div class="mm-kicker">Mentor analysis</div><h2 class="mm-section-title">Step-by-step <span class="mm-accent">review</span></h2>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Overall score", f"{scores['overall_score']:.1f} / 100")
    c2.metric("Step accuracy", f"{100 * scores['step_accuracy']:.1f}%")
    c3.metric("Expected-path coverage", f"{100 * scores['coverage']:.1f}%")

    feedback_by_step = {item["step"]: item for item in report["feedback"]}
    for evaluation in report["evaluations"]:
        correct = bool(evaluation["is_correct"])
        status = "Correct" if correct else "Needs revision"
        css = "" if correct else " bad"
        label_css = "good" if correct else "bad"
        feedback = feedback_by_step[evaluation["student_step_index"]]
        detail = ""
        if not correct:
            detail = f"""
                <div class="mm-detail-grid">
                    <div class="mm-detail"><div class="mm-label">Expected step</div><div class="mm-detail-value">{esc(evaluation['expected_step'])}</div></div>
                    <div class="mm-detail"><div class="mm-label">Concept</div><div class="mm-detail-value">{esc(evaluation['concept'].replace('_', ' '))}</div></div>
                </div>"""
        st.markdown(
            f"""
            <div class="mm-review-card{css}">
                <div class="mm-review-top">
                    <span class="mm-label">Step {evaluation['student_step_index']}</span>
                    <span class="mm-label {label_css}">{esc(status)}</span>
                    <span class="mm-label">{esc(evaluation['error_type'].replace('_', ' '))}</span>
                    <span class="mm-label">Confidence {100 * float(evaluation['confidence']):.0f}%</span>
                </div>
                <div class="mm-submitted">{esc(evaluation['student_step'])}</div>{detail}
                <div class="mm-mentor-note"><strong>{esc(feedback['style'].replace('_', ' ').title())}:</strong> {esc(feedback['feedback'])}<br><span style="color:var(--mm-muted)">{esc(evaluation['explanation'])}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    recommendation = report["recommended_problem"]
    with st.container(border=True):
        recommendation_text, recommendation_button = st.columns([3, 1], vertical_alignment="center")
        with recommendation_text:
            st.markdown(
                f"""<div class="mm-meta">Recommended next problem</div>
<div class="mm-problem-text">{esc(recommendation['prompt'])}</div>
<div class="mm-meta">{esc(recommendation['problem_id'])} / {esc(recommendation['topic'])} / Difficulty {recommendation['difficulty']}</div>""",
                unsafe_allow_html=True,
            )
        with recommendation_button:
            if st.button("Move on to next problem", type="primary", use_container_width=True):
                st.session_state["_problem_request"] = recommendation["problem_id"]
                st.rerun()

    snapshot = pd.DataFrame(report.get("weakness_summary", []))
    if not snapshot.empty:
        st.markdown("### Mastery snapshot")
        for _, row in snapshot.head(5).iterrows():
            value = max(0.0, min(1.0, float(row["mastery"])))
            st.markdown(
                f"""
                <div class="mm-panel" style="margin-bottom:.7rem;padding:1rem">
                    <div style="display:flex;justify-content:space-between;gap:1rem"><strong>{esc(row['topic'])}: {esc(str(row['concept']).replace('_', ' '))}</strong><span class="mm-meta">{100 * value:.0f}% mastery</span></div>
                    <div class="mm-progress-track"><div class="mm-progress-fill" style="width:{100 * value:.1f}%"></div></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    incorrect = [evaluation for evaluation in report["evaluations"] if not evaluation["is_correct"]]
    if incorrect and not st.session_state.get("feedback_recorded", False):
        st.caption("Help the adaptive feedback prototype learn which response style works for this error type.")
        first = incorrect[0]
        first_feedback = feedback_by_step[first["student_step_index"]]
        b1, b2 = st.columns(2)
        if b1.button("Feedback was helpful", key=f"helpful_{report.get('attempt_id')}", use_container_width=True):
            record_feedback_reward(profile.student_id, first["error_type"], first_feedback["style"], 1.0)
            st.session_state["feedback_recorded"] = True
            st.success("Feedback preference recorded for this prototype session.")
        if b2.button("Feedback needs improvement", key=f"unhelpful_{report.get('attempt_id')}", use_container_width=True):
            record_feedback_reward(profile.student_id, first["error_type"], first_feedback["style"], -1.0)
            st.session_state["feedback_recorded"] = True
            st.info("Feedback preference recorded for this prototype session.")

    d1, d2 = st.columns(2)
    d1.download_button(
        "Download Markdown report",
        data=report_to_markdown(report),
        file_name=f"math_mentor_attempt_{report.get('attempt_id') or 'latest'}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    d2.download_button(
        "Download JSON report",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        file_name=f"math_mentor_attempt_{report.get('attempt_id') or 'latest'}.json",
        mime="application/json",
        use_container_width=True,
    )

    with st.expander("Open the diagnostic table"):
        frame = pd.DataFrame(report["evaluations"])
        visible = ["student_step_index", "student_step", "is_correct", "error_type", "confidence", "concept", "expected_step"]
        st.dataframe(frame[visible], use_container_width=True, hide_index=True)


def render_analyze() -> None:
    pending_problem = st.session_state.pop("_problem_request", None)
    if pending_problem in PROBLEMS_BY_ID:
        st.session_state["problem_selector"] = pending_problem
        st.session_state.pop("last_report", None)
        st.session_state["feedback_recorded"] = False

    render_page_header(
        "Analyze",
        "Solve one problem at a time. MathMentor AI checks every submitted line, explains the first miss, records the attempt, and recommends the next challenge.",
    )
    profile = current_profile()
    render_profile_strip(profile)

    left, right = st.columns([1.45, 0.85])
    with left:
        problem_id = st.selectbox(
            "Choose a problem",
            options=[problem.problem_id for problem in PROBLEM_BANK],
            format_func=lambda pid: f"{pid} | {PROBLEMS_BY_ID[pid].topic} | Difficulty {PROBLEMS_BY_ID[pid].difficulty}",
            key="problem_selector",
        )
        problem = PROBLEMS_BY_ID[problem_id]
        st.markdown(
            f"""
            <div class="mm-problem">
                <div class="mm-meta">Your problem</div>
                <div class="mm-problem-text">{esc(problem.prompt)}</div>
                <div class="mm-meta">Concept {esc(problem.subtopic)} / Skills {esc(' / '.join(problem.skills))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("Hints and learning targets"):
            for index, hint in enumerate(problem.hints, start=1):
                st.markdown(f"**Hint {index}:** {hint}")
            st.caption("Expected learning pathway: " + " -> ".join(step.concept.replace("_", " ") for step in problem.expected_steps))

        solution_key = f"solution_steps_{problem_id}"
        solution = st.text_area(
            "Your solution - one mathematical step per line",
            value=DEFAULT_STEPS.get(problem_id, ""),
            height=220,
            key=solution_key,
            help="Use explicit notation such as 2*x + 3 = 11, x^2, x**2, exp(3*t), or Derivative(expression, x).",
        )
        a1, a2 = st.columns([1.25, 1])
        analyze = a1.button("Analyze my solution ->", type="primary", use_container_width=True)
        if a2.button("Choose a random problem", use_container_width=True):
            alternatives = [p.problem_id for p in PROBLEM_BANK if p.problem_id != problem_id]
            st.session_state["_problem_request"] = random.choice(alternatives)
            st.rerun()

    with right:
        st.markdown(
            """
            <div class="mm-panel">
                <div class="mm-kicker">Evaluation pipeline</div>
                <div class="mm-card-title">What happens after submit</div>
                <div class="mm-card-copy">
                    1. Parse each line with SymPy.<br><br>
                    2. Compare it with the expected mathematical pathway.<br><br>
                    3. Diagnose errors with transparent rules plus ML and DNN classifiers.<br><br>
                    4. Save the attempt to SQLite.<br><br>
                    5. Update weakness and mastery estimates.<br><br>
                    6. Select a feedback style and recommend the next problem.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.info("Prototype note: the symbolic checker is the mathematical validator. ML components diagnose likely error categories; they are not the sole source of truth.")
        if st.button("Open mastery dashboard", use_container_width=True):
            go_to("Mastery")

    if analyze:
        steps = [line.strip() for line in solution.splitlines() if line.strip()]
        if not steps:
            st.error("Enter at least one mathematical step before running the analysis.")
        else:
            try:
                with st.spinner("Checking the mathematical pathway and building feedback..."):
                    report = run_mentor_attempt(profile, problem_id, steps, save=True)
                st.session_state["last_report"] = report
                st.session_state["feedback_recorded"] = False
            except Exception as exc:
                st.error(f"The prototype could not analyze this submission: {exc}")

    report = st.session_state.get("last_report")
    if report and report.get("problem", {}).get("problem_id") == problem_id:
        st.markdown('<section class="mm-section">', unsafe_allow_html=True)
        render_review(report, profile)
        st.markdown("</section>", unsafe_allow_html=True)


def weighted_topic_metrics(summary: pd.DataFrame, topic: str) -> tuple[float, float, int]:
    subset = summary[summary["topic"] == topic] if not summary.empty else pd.DataFrame()
    if subset.empty:
        return 0.0, 0.0, 0
    weights = subset["attempted_steps"].astype(float)
    total = int(weights.sum())
    if total <= 0:
        return 0.0, 0.0, 0
    mastery = float((subset["mastery"] * weights).sum() / weights.sum())
    error_rate = float((subset["error_rate"] * weights).sum() / weights.sum())
    return mastery, error_rate, total


def render_mastery() -> None:
    render_page_header(
        "Mastery",
        "See progress by topic, select a starting level, inspect concept performance, and use recorded attempts to focus future practice.",
    )
    profile = current_profile()
    history = load_student_history(profile.student_id)
    summary = weakness_summary(profile.student_id)

    if history.empty:
        attempts = 0
        average_score = 0.0
        topics_practiced = 0
    else:
        attempt_summary = history[["attempt_id", "problem_id", "topic", "difficulty", "overall_score", "submitted_at"]].drop_duplicates("attempt_id")
        attempts = int(attempt_summary.shape[0])
        average_score = float(attempt_summary["overall_score"].mean())
        topics_practiced = int(attempt_summary["topic"].nunique())
    m1, m2, m3 = st.columns(3)
    m1.metric("Attempts", attempts)
    m2.metric("Average score", f"{average_score:.1f}")
    m3.metric("Topics practiced", topics_practiced)

    st.markdown('<div class="mm-kicker" style="margin-top:2.5rem">Topic mastery</div><h2 class="mm-section-title">Your learning <span class="mm-accent">map</span></h2>', unsafe_allow_html=True)
    st.caption("Starting levels influence problem recommendations. Mastery grows from correct work, repeated practice, and problem difficulty.")

    for topic in TOPICS:
        mastery, error_rate, attempted_steps = weighted_topic_metrics(summary, topic)
        with st.container(border=True):
            title_col, level_col = st.columns([2.2, 1])
            with title_col:
                st.markdown(f"### {topic}")
                st.caption(f"Mastery {mastery:.2f} | Attempted steps {attempted_steps} | Error rate {100 * error_rate:.0f}%")
            with level_col:
                st.session_state[f"mastery_level_{topic}_input"] = st.session_state[f"level_{topic}"]
                st.selectbox(
                    "Starting level",
                    LEVEL_OPTIONS,
                    key=f"mastery_level_{topic}_input",
                    format_func=lambda value: value.title(),
                    on_change=update_topic_level,
                    args=(topic,),
                )
            st.progress(max(0.0, min(1.0, mastery)))
            subset = summary[summary["topic"] == topic] if not summary.empty else pd.DataFrame()
            with st.expander("Open concept details"):
                if subset.empty:
                    available = [p for p in PROBLEM_BANK if p.topic == topic]
                    st.info("No saved attempts for this topic yet.")
                    for item in available:
                        st.markdown(f"**{item.subtopic}** - difficulty {item.difficulty}: {item.prompt}")
                else:
                    for _, row in subset.sort_values("mastery").iterrows():
                        value = max(0.0, min(1.0, float(row["mastery"])))
                        st.markdown(f"**{str(row['concept']).replace('_', ' ').title()}** - {100 * value:.0f}% mastery")
                        st.progress(value)
                        st.caption(f"{int(row['correct_steps'])}/{int(row['attempted_steps'])} correct steps | Error rate {100 * float(row['error_rate']):.0f}%")

    if history.empty:
        st.info("No attempt history is saved for this learner yet. Analyze a solution to populate the dashboard.")
        if st.button("Analyze the first problem", type="primary"):
            go_to("Analyze")
    else:
        st.markdown("### Attempt history")
        attempt_summary = (
            history[["attempt_id", "problem_id", "topic", "difficulty", "overall_score", "submitted_at"]]
            .drop_duplicates("attempt_id")
            .sort_values("attempt_id", ascending=False)
        )
        st.dataframe(attempt_summary, use_container_width=True, hide_index=True)
        if not summary.empty:
            chart = summary[["topic", "concept", "mastery"]].copy()
            chart["skill"] = chart["topic"] + ": " + chart["concept"].str.replace("_", " ")
            st.markdown("### Concept mastery comparison")
            st.bar_chart(chart.set_index("skill")["mastery"])


def workflow_html() -> str:
    stages = [
        ("01", "Learner profile", "Grade band, topic level, feedback preference, and accessibility context."),
        ("02", "Problem selection", "A calibrated problem bank supplies prompts, expected steps, concepts, skills, and hints."),
        ("03", "Step parsing", "Each submitted line is normalized and parsed into a symbolic mathematical statement."),
        ("04", "Symbolic validation", "SymPy checks equivalence and compares the submitted pathway with expected transformations."),
        ("05", "Error diagnosis", "Rules, logistic regression, and a compact neural network classify the likely error type."),
        ("06", "Attempt history", "SQLite stores attempts and step evaluations for later analysis and reporting."),
        ("07", "Mastery and feedback", "Weakness estimates, a contextual bandit, and learning preferences shape the response."),
        ("08", "Next action", "The app produces a downloadable report and recommends the next targeted problem."),
    ]
    cards = "".join(
        f"<div class='mm-workflow-card'><div class='mm-workflow-index'>{number}</div><div class='mm-workflow-title'>{esc(title)}</div><div class='mm-workflow-copy'>{esc(copy)}</div></div>"
        for number, title, copy in stages
    )
    return f'<div class="mm-workflow">{cards}</div>'


def render_about() -> None:
    render_page_header(
        "About",
        "MathMentor AI does not just give answers. It teaches the miss, explains the repair, and turns every attempt into a more focused next step.",
    )
    st.markdown(
        """
        <section class="mm-section">
            <div class="mm-kicker">The learning problem</div>
            <h2 class="mm-section-title">Feedback should respond to <span class="mm-accent">your work</span></h2>
            <p class="mm-lead">Many tools provide a final answer, a generic video, or a broad hint. MathMentor AI instead reads the learner's submitted pathway, identifies the first mathematically meaningful divergence, names the type of mistake, and connects the correction to the underlying concept.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="mm-kicker" style="margin-top:3rem">Complete prototype workflow</div><h2 class="mm-section-title">From profile to <span class="mm-accent">personalized next step</span></h2>', unsafe_allow_html=True)
    st.markdown(workflow_html(), unsafe_allow_html=True)

    st.markdown('<section class="mm-section"><div class="mm-kicker">Project team</div><h2 class="mm-section-title">Built for learning, reviewed for <span class="mm-accent">rigor</span></h2></section>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="mm-card">
                <div class="mm-meta">Author</div>
                <div class="mm-card-title" style="font-size:2rem;margin-top:.75rem">{esc(AUTHOR)}</div>
                <div class="mm-card-copy">Product author and student developer. The project combines mathematical reasoning, educational feedback design, data tracking, and an accessible web experience.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f"""
            <div class="mm-card">
                <div class="mm-meta">Advisor</div>
                <div class="mm-card-title" style="font-size:2rem;margin-top:.75rem">{esc(ADVISOR)}</div>
                <div class="mm-card-copy">Project advisor supporting AI, data science, mathematical modeling, product architecture, prototype validation, and deployment strategy.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Explore the project")
    l1, l2 = st.columns(2)
    l1.link_button("Open GitHub repository", GITHUB_URL, use_container_width=True)
    l2.link_button("Open live Streamlit app", LIVE_APP_URL, use_container_width=True)

    st.markdown("### Technology and prototype boundaries")
    t1, t2, t3 = st.columns(3)
    with t1:
        st.markdown("**Mathematics**\n\nSymPy parsing, symbolic equivalence, expected-step trajectories, concept tags, and deterministic validation.")
    with t2:
        st.markdown("**AI and analytics**\n\nRule-assisted diagnosis, TF-IDF plus logistic regression, compact MLP classifier, weakness analytics, recommendation scoring, and an epsilon-greedy feedback bandit.")
    with t3:
        st.markdown("**Product platform**\n\nStreamlit, Python, pandas, SQLite, responsive CSS, downloadable reports, GitHub deployment, and preserved React/Tailwind design source.")
    st.warning("Educational prototype only. The starter problem bank is intentionally small, cloud SQLite storage can reset on redeploy, and the product is not a substitute for a qualified teacher or formal assessment system.")

    st.markdown('<section class="mm-section"><div class="mm-kicker">Feedback and collaboration</div><h2 class="mm-section-title">Tell us what to improve <span class="mm-accent">next</span></h2></section>', unsafe_allow_html=True)
    with st.form("feedback_form", clear_on_submit=True):
        f1, f2 = st.columns(2)
        name = f1.text_input("Name")
        email = f2.text_input("Email")
        category = st.selectbox("Message type", ["Product feedback", "Bug report", "Feature idea", "Education partnership", "Other"])
        message = st.text_area("Message", height=150)
        submitted = st.form_submit_button("Submit prototype feedback", type="primary")
        if submitted:
            if not message.strip():
                st.error("Please add a short message.")
            else:
                st.success(f"Thank you, {name or 'student'}. This demonstration form validated your {category.lower()} message locally; it does not transmit or store personal data.")


def render_settings() -> None:
    render_page_header(
        "Settings",
        "Manage appearance, learner profile, topic levels, feedback preferences, and accessibility context for the prototype.",
    )
    st.markdown("## Display")
    st.caption("Choose the brightness that feels best for studying. The attached UI uses dark mode by default.")
    st.session_state.setdefault("theme_input", st.session_state["theme"])
    st.radio("Appearance", ["Dark", "Light"], horizontal=True, key="theme_input", on_change=update_theme)

    st.markdown("## Learner profile")
    st.session_state.setdefault("display_name_input", st.session_state["display_name"])
    st.session_state.setdefault("grade_band_input", st.session_state["grade_band"])
    st.session_state.setdefault("school_class_input", st.session_state["school_class"])
    st.session_state.setdefault("preferred_feedback_input", st.session_state["preferred_feedback"])
    st.session_state.setdefault("accessibility_notes_input", st.session_state["accessibility_notes"])
    for topic in TOPICS:
        st.session_state.setdefault(f"level_{topic}_input", st.session_state[f"level_{topic}"])
    with st.form("profile_form"):
        p1, p2 = st.columns(2)
        p1.text_input("Display name", key="display_name_input")
        p2.selectbox(
            "Grade band",
            ["Grades 5-7", "Grades 7-10", "Grades 9-12", "Grades 9-12 / College", "College / AP", "College"],
            key="grade_band_input",
        )
        p1.text_input("School / class (optional)", key="school_class_input")
        p2.selectbox(
            "Preferred feedback style",
            FEEDBACK_STYLES,
            key="preferred_feedback_input",
            format_func=lambda value: value.replace("_", " ").title(),
        )
        st.text_area(
            "Accessibility or learning notes (optional)",
            key="accessibility_notes_input",
            help="Examples: shorter explanations, more worked examples, larger chunks, or extra notation reminders.",
        )
        st.markdown("### Current topic level")
        level_columns = st.columns(3)
        for index, topic in enumerate(TOPICS):
            with level_columns[index % 3]:
                st.selectbox(topic, LEVEL_OPTIONS, key=f"level_{topic}_input", format_func=lambda value: value.title())
        saved = st.form_submit_button(
            "Save learner settings", type="primary", on_click=update_current_profile,
        )
        if saved:
            st.success("Learner settings saved for this browser session.")

    st.markdown("## Data and privacy")
    profile = current_profile()
    history = load_student_history(profile.student_id)
    st.markdown(
        "This prototype stores attempts in a local SQLite file on the running server. On Streamlit Community Cloud, that storage is ephemeral and may reset when the app restarts or redeploys. A production version should use authenticated accounts, a managed database, encryption, retention controls, and child-safety review."
    )
    if not history.empty:
        st.download_button(
            "Download my prototype attempt history",
            data=history.to_csv(index=False),
            file_name="mathmentor_attempt_history.csv",
            mime="text/csv",
        )
    else:
        st.caption("No attempt history is currently available for this learner profile.")

    st.info("This prototype intentionally does not collect or save passwords, payment data, or account credentials.")


def render_footer(snapshot: CounterSnapshot) -> None:
    st.markdown(
        f"""
        <div class="mm-footer">
            <div class="mm-footer-mark">MATHMENTOR <span class="mm-accent">AI</span></div>
            <div class="mm-footer-copy">Author {esc(AUTHOR)} &nbsp; / &nbsp; Advisor {esc(ADVISOR)} &nbsp; / &nbsp; Step-by-step feedback that teaches</div>
            <div class="mm-footer-visits"><span>Cumulative App Visits</span>
              <strong>{esc(f'{snapshot.total:,}' if snapshot.total is not None and snapshot.total > 0 else '—')}</strong>
              <span>· {esc('Live' if snapshot.status == 'live' else 'Last Known' if snapshot.status == 'cached' else 'Unavailable / Setup Required')}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


initialize_state()
inject_css()
visitor_snapshot = current_visit_snapshot()
render_visit_bar(visitor_snapshot)
page = render_navigation()

if page == "Home":
    render_home()
elif page == "Analyze":
    render_analyze()
elif page == "Mastery":
    render_mastery()
elif page == "About":
    render_about()
elif page == "Settings":
    render_settings()

render_footer(visitor_snapshot)
