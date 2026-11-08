"""Canvas connector with a fake Canvas API (no network)."""
from app.config import settings
from app.connectors.canvas import CanvasConnector

COURSES = [
    {"id": 1, "name": "Machine Learning in Production", "course_code": "17-645"},
    {"id": 2, "name": "Large Language Model Systems", "course_code": "11-868"},
]
ASSIGNMENTS = {
    1: [{"id": 101, "name": "Milestone 4", "due_at": "2026-11-13T22:00:00Z", "html_url": "https://canvas.example/a/101"}],
    2: [{"id": 201, "name": "Homework 3", "due_at": "2026-11-12T22:00:00Z", "html_url": "https://canvas.example/a/201"}],
}


def _fake_get(self, path, params=None):
    if path == "/users/self/courses":
        return COURSES
    return ASSIGNMENTS[int(path.split("/")[2])]


def _sync(monkeypatch, exclude):
    monkeypatch.setattr(settings, "canvas_base_url", "https://canvas.example")
    monkeypatch.setattr(settings, "canvas_token", "test-token")
    monkeypatch.setattr(settings, "canvas_exclude_courses", exclude)
    monkeypatch.setattr(CanvasConnector, "_get", _fake_get)
    return CanvasConnector().fetch_live("demo_student")


def test_excluded_course_is_never_synced(empty_client, monkeypatch):
    recs = _sync(monkeypatch, ["machine learning in production"])
    assert [r.metadata["course_name"] for r in recs] == ["Large Language Model Systems"]


def test_exclusion_by_code_or_id_and_default_keeps_all(empty_client, monkeypatch):
    assert len(_sync(monkeypatch, [])) == 2
    assert [r.title for r in _sync(monkeypatch, ["17-645"])] == ["Homework 3"]
    assert [r.title for r in _sync(monkeypatch, ["2"])] == ["Milestone 4"]
