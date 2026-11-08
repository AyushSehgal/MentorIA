"""Ed Discussion connector with a fake Ed API (no network)."""
from app.config import settings
from app.connectors.edstem import EdStemConnector, course_code
from app.services import aggregation

USER = {"courses": [
    {"course": {"id": 1, "code": "11868", "name": "Large Language Model Systems", "status": "active"}},
    {"course": {"id": 2, "code": "10-605", "name": "ML with Large Datasets", "status": "active"}},
    {"course": {"id": 3, "code": "99999", "name": "Old Course", "status": "archived"}},
]}
THREADS = {
    1: {"threads": [
        {"id": 11, "title": "HW6 released", "type": "announcement", "user_id": 7, "created_at": "2026-11-06T10:00:00+00:00",
         "document": "Homework 6 is out."},
        {"id": 12, "title": "Question about KV cache", "type": "question", "user_id": 8, "created_at": "2026-11-06T11:00:00+00:00",
         "document": "How big is it?"},
        {"id": 13, "title": "My grade (private)", "type": "question", "user_id": 8, "is_private": True,
         "created_at": "2026-11-06T12:00:00+00:00", "document": "secret"},
    ], "users": [{"id": 7, "course_role": "admin"}, {"id": 8, "course_role": "student"}]},
    2: {"threads": [
        {"id": 21, "title": "TA tip on all-reduce", "type": "post", "user_id": 9, "created_at": "2026-11-05T09:00:00+00:00",
         "document": "Ring all-reduce explained"},
    ], "users": [{"id": 9, "course_role": "mentor"}]},
}


def _fake_get(self, path, params=None):
    if path == "/user":
        return USER
    return THREADS[int(path.split("/")[2])]


def _setup(monkeypatch, exclude=()):
    monkeypatch.setattr(settings, "edstem_token", "test-token")
    monkeypatch.setattr(settings, "edstem_exclude_courses", list(exclude))
    monkeypatch.setattr(EdStemConnector, "_get", _fake_get)


def test_course_code_format():
    assert course_code("11868") == "11-868" and course_code("10-605") == "10-605" and course_code("") == ""


def test_threads_become_discussions_private_skipped(empty_client, monkeypatch):
    _setup(monkeypatch)
    recs = {r.external_id: r for r in EdStemConnector().fetch_live("demo_student")}
    assert set(recs) == {"11", "12", "21"}  # private thread 13 and the archived course are skipped
    assert recs["11"].metadata["is_instructor"] and recs["21"].metadata["is_instructor"]  # announcement; mentor
    assert not recs["12"].metadata["is_instructor"]
    assert recs["12"].metadata["course_name"] == "11-868 Large Language Model Systems"
    assert recs["12"].kind == "discussion" and recs["12"].source_url.endswith("/courses/1/discussion/12")
    assert recs["12"].course_id is None and recs["12"].concept_ids == []  # no MentorIA course 11-868 -> no links


def test_exclusion_by_name_or_code(empty_client, monkeypatch):
    _setup(monkeypatch, ["large language model systems"])
    assert {r.external_id for r in EdStemConnector().fetch_live("demo_student")} == {"21"}
    _setup(monkeypatch, ["10-605"])
    assert {r.external_id for r in EdStemConnector().fetch_live("demo_student")} == {"11", "12"}


def test_sync_marks_ed_connected_and_verified(empty_client, monkeypatch):
    _setup(monkeypatch)
    res = aggregation.sync_provider("edstem", "demo_student")
    assert res.status.state == "connected" and res.status.verified_live and res.records_total == 3
    st = {s.provider: s for s in aggregation.statuses("demo_student")}
    assert st["edstem"].state == "connected"
