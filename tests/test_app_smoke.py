from pathlib import Path

from streamlit.testing.v1 import AppTest


APP = Path(__file__).resolve().parents[1] / "app.py"


def test_home_page_runs_without_exception():
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    assert not app.exception


def test_all_navigation_pages_render():
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    assert not app.exception

    for page in ["Analyze", "Mastery", "About", "Settings", "Home"]:
        app.radio[0].set_value(page)
        app.run()
        assert not app.exception, f"{page} page raised an exception"


def test_learning_profile_and_analysis():
    app = AppTest.from_file(str(APP), default_timeout=60).run()
    app.radio[0].set_value("Settings").run()
    labels = {widget.label for widgets in [app.selectbox, app.text_input, app.radio] for widget in widgets}
    assert "Display name" in labels
    assert "Grade band" in labels
    assert not labels.intersection({"Country", "Region", "Language", "Interface language"})

    app.radio[0].set_value("Analyze").run()
    app.selectbox(key="problem_selector").set_value("ALG-LIN-001").run()
    next(button for button in app.button if button.label == "Analyze my solution ->").click().run()
    assert not app.exception
    assert not app.error
    report = app.session_state["last_report"]
    assert report["scores"]["overall_score"] == 100.0
    assert report["recommended_problem"]["problem_id"]
    assert "country" not in report["profile"]
    app.radio[0].set_value("Mastery").run()
    assert not app.exception
