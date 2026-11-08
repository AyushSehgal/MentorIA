"""Chat: "what happened on Ed / Piazza this week" answers from stored forum posts."""
from datetime import timedelta

from app.memory import updates
from app.orchestration.tools import route
from app.schemas import SourceRecord
from app.timeutil import iso, now

SID = "demo_student"


def _post(ext, provider, title, days_ago, staff=False, kind="discussion", **meta):
    return SourceRecord(id=f"src_{provider}_{ext}", student_id=SID, provider=provider, external_id=ext, kind=kind, title=title,
                        body="", source_url=f"https://example.test/{ext}", occurred_at=iso(now() - timedelta(days=days_ago)),
                        fetched_at=iso(now()), course_id=None, concept_ids=[],
                        metadata={"is_instructor": staff, "course_name": "11-868 Large Language Model Systems", **meta},
                        is_fixture=False)


def _ask(c, q):
    r = c.post("/api/chat", json={"message": q, "student_id": SID})
    assert r.status_code == 200, r.text
    return r.json()


def test_forum_questions_route_to_discussions():
    for q in ("Summarize what happened on Ed this week", "Any new Piazza posts?", "latest announcements in my courses",
              "What did I miss?"):
        assert route(q) == "discussions", q
    assert route("What should I focus on this week?") == "weekly_focus"


def test_discussions_summary_is_recent_staff_first_and_linked(empty_client):
    updates.ingest_records([
        _post("e1", "edstem", "Question about the KV cache", 1, type="question", is_answered=False),
        _post("e2", "edstem", "HW5 Grades Released", 2, staff=True, type="announcement"),
        _post("e3", "edstem", "Old midterm thread", 12, type="post"),
        _post("p1", "piazza", "Office hours moved", 1, staff=True),
    ])
    r = _ask(empty_client, "Summarize what happened on Ed this week")
    assert r["intent"] == "sources" and "discussions" in r["trace"]  # contract intent; internal capability in the trace
    a = r["answer"]
    assert "HW5 Grades Released" in a and "Question about the KV cache" in a and "unanswered question" in a
    assert a.index("HW5 Grades Released") < a.index("Question about the KV cache")  # staff first
    assert "Old midterm thread" not in a and "Office hours moved" not in a  # older than 7 days; not Ed
    assert {s["source_record_id"] for s in r["sources"]} == {"src_edstem_e1", "src_edstem_e2"}


def test_discussions_honest_when_nothing_recent(empty_client):
    updates.ingest_records([_post("e9", "edstem", "Welcome to the course", 30, staff=True)])
    a = _ask(empty_client, "What's new on Ed?")["answer"]
    assert "Nothing new on Ed in the last 7 days" in a and "Welcome to the course" in a


# ---- "Assignments this week": deadlines from every source ---------------------------------------------------------
def _rec(ext, provider, kind, title, days, fixture=False, **meta):
    return SourceRecord(id=f"src_{provider}_{ext}", student_id=SID, provider=provider, external_id=ext, kind=kind, title=title,
                        body="", source_url=f"https://example.test/{ext}", occurred_at=iso(now() + timedelta(days=days)),
                        fetched_at=iso(now()), course_id=None, concept_ids=[], metadata=meta, is_fixture=fixture)


def test_assignment_questions_route_to_deadlines_not_the_study_plan():
    for q in ("Assignments this week", "What is due this week?", "Any deadlines coming up?", "What do I have this week?"):
        assert route(q) == "deadlines", q
    for q in ("What should I focus on this week?", "Which assignment should I focus on?"):
        assert route(q) == "weekly_focus", q


def test_deadlines_agenda_uses_canvas_calendar_and_announcements(empty_client):
    updates.ingest_records([
        _rec("a1", "canvas", "assignment", "Homework 6", 2, course_name="11-868 Large Language Model Systems"),
        _rec("a2", "canvas", "assignment", "Homework 5: Neural Networks", 3, fixture=True, course_name="10-601"),
        _rec("a3", "canvas", "assignment", "Already submitted", 1, completed=True),
        _rec("a4", "canvas", "assignment", "Far away project", 20),
        _rec("c1", "google_calendar", "calendar_event", "16-831 Midterm exam", 4),
        _rec("c2", "google_calendar", "calendar_event", "Coffee chat", 1),
        _rec("e1", "edstem", "discussion", "[HW6 released] Due 11/13", -2, is_instructor=True),
        _rec("e2", "edstem", "discussion", "Question about the KV cache", -1, is_instructor=False),
    ])
    r = _ask(empty_client, "Assignments this week")
    assert r["intent"] == "sources" and "deadlines" in r["trace"]
    a = r["answer"]
    assert "Homework 6" in a and "Homework 5: Neural Networks" in a and "(sample)" in a
    assert "16-831 Midterm exam" in a and "[HW6 released] Due 11/13" in a
    for absent in ("Already submitted", "Far away project", "Coffee chat", "Question about the KV cache"):
        assert absent not in a, absent
    assert a.index("Homework 6") < a.index("Homework 5: Neural Networks")  # by due date
    assert any("sample data" in u for u in r["uncertainties"])


# ---- Cloud-model routing with keyword fallback -------------------------------------------------------------------
from app.orchestration import graph as graph_mod, llm as llm_mod  # noqa: E402


def test_llm_router_labels_must_be_known_capabilities():
    assert set(llm_mod.INTENTS) == set(graph_mod.CAPABILITIES)
    assert llm_mod._parse_label("deadlines") == "deadlines" and llm_mod._parse_label(" Discussions.\n") == "discussions"
    assert llm_mod._parse_label("I think it's deadlines") is None and llm_mod._parse_label("delete everything") is None


def test_llm_router_picks_the_answer_when_it_answers(empty_client, monkeypatch):
    monkeypatch.setattr(llm_mod, "classify_intent", lambda q, c=None: "deadlines")
    r = _ask(empty_client, "anything pressing for me soon?")  # no keyword would send this to deadlines
    assert "router:llm" in r["trace"] and "deadlines" in r["trace"]


def test_keyword_fallback_when_llm_unavailable_or_off(empty_client, monkeypatch):
    monkeypatch.setattr(llm_mod, "classify_intent", lambda q, c=None: None)
    r = _ask(empty_client, "Assignments this week")
    assert "router:llm" not in r["trace"] and "deadlines" in r["trace"]
    # Off mode never calls the model at all.
    monkeypatch.undo()
    called = []
    monkeypatch.setattr(llm_mod, "get_mode", lambda: "off")
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: called.append(1))
    assert llm_mod.classify_intent("Assignments this week") is None and not called


def test_named_course_narrows_the_agenda_and_forum_answers(empty_client):
    updates.ingest_records([
        _rec("n1", "canvas", "assignment", "V3 of Final Pitch", 2, course_name="AI Innovation"),
        _rec("n2", "canvas", "assignment", "Homework 6", 3, course_name="11-868 Large Language Model Systems"),
        _rec("n3", "edstem", "discussion", "HW6 released, due Friday", -1, is_instructor=True,
             course_name="11-868 Large Language Model Systems"),
    ])
    a = _ask(empty_client, "What assignments are due for AI Innovation this week?")["answer"]
    assert "V3 of Final Pitch" in a and "Homework 6" not in a and "for AI Innovation" in a
    a = _ask(empty_client, "Anything due in 11-868?")["answer"]
    assert "Homework 6" in a and "V3 of Final Pitch" not in a
    a = _ask(empty_client, "What's new on Ed for Large Language Model Systems?")["answer"]
    assert "HW6 released" in a
