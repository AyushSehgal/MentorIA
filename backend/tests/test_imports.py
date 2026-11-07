"""v1.2/v1.3: start empty, add data manually, merge goals across sources, 'About me' input."""
from app.memory import store
from app.services import demo_assets

from .conftest import SID, upload

STEP = {a["step"]: a["name"] for a in demo_assets._manifest()}


def add(c, step):
    r = c.post(f"/api/imports/demo/{STEP[step]}")
    assert r.status_code == 200, r.text
    return r.json()


def test_starts_empty(empty_client):
    d = empty_client.get("/api/dashboard").json()
    assert all(v == 0 for v in d["knowledge"].values())
    assert d["insights"] == [] and d["recommendations"] == []
    assert {s["provider"]: s["state"] for s in d["connectors"]}["canvas"] == "not_available"
    r = empty_client.post("/api/chat", json={"message": "What ML topics am I struggling with?"}).json()
    assert "don't know about any of your courses" in r["answer"]


def test_course_overview_defines_course_and_concepts(empty_client):
    r = add(empty_client, 1)
    assert r["kind"] == "course_overview" and r["concepts_added"] == 19
    m = empty_client.get("/api/memory/model").json()
    assert [c["label"] for c in m["courses"]] == ["Introduction to Machine Learning (10-601)"]
    assert all(c["mastery"] is None for c in m["concepts"])


def test_10605_shares_concepts_with_10601(empty_client):
    for step in (1, 3):
        add(empty_client, step)
    m = {c["concept_id"]: c for c in empty_client.get("/api/memory/model").json()["concepts"]}
    assert m["backpropagation"]["course_id"] == "10-601"
    assert m["backpropagation"]["also_in"] == ["10-605"] and m["lsh"]["also_in"] == []
    add(empty_client, 6)   # 10-601 quiz: 2 wrong on backprop
    before = empty_client.get("/api/memory/model").json()
    b1 = next(c for c in before["concepts"] if c["concept_id"] == "backpropagation")
    add(empty_client, 8)   # 10-605 lecture quizzes: autodiff miss counts toward the same concept
    after = empty_client.get("/api/memory/model").json()
    b2 = next(c for c in after["concepts"] if c["concept_id"] == "backpropagation")
    assert b2["incorrect"] == b1["incorrect"] + 1 and b2["mastery"] < b1["mastery"]
    r = empty_client.post("/api/chat", json={"message": "What 10-605 topics am I struggling with?"}).json()
    assert "Backpropagation" in r["answer"] and "10-605" in r["answer"]
    g = empty_client.get("/api/memory/graph").json()
    assert {e["source"] for e in g["edges"] if e["target"] == "concept:backpropagation" and e["relation"] == "contains"} == {"course:10-601", "course:10-605"}


def test_prepopulated_start(empty_client, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "prepopulate", True)
    empty_client.post("/api/demo/reset")
    k = empty_client.get("/api/dashboard").json()["knowledge"]
    assert (k["courses"], k["imports"]) == (3, 16)


def test_quiz_before_overview_warns_then_maps_after(empty_client):
    r = add(empty_client, 6)
    assert r["warnings"] and "course overview first" in r["warnings"][0]
    add(empty_client, 1)
    r = add(empty_client, 6)
    assert any("Backpropagation: 0.12" in c for c in r["changes"])


def test_full_demo_sequence(empty_client):
    for step in sorted(STEP):
        add(empty_client, step)
    d = empty_client.get("/api/dashboard").json()
    k = d["knowledge"]
    assert (k["courses"], k["concepts"], k["graded_answers"], k["imports"]) == (3, 48, 18, 16)
    assert all(s["state"] == "imported" for s in d["connectors"] if s["provider"] != "documents")
    opps = {o["record"]["title"][:20]: o for o in d["cards"]["gmail"]["opportunities"]}
    assert opps["Robotics Seminar: Te"]["relevance_score"] >= 0.5 and opps["Robotics Seminar: Te"]["event_start"]
    assert opps["Quant Finance Club: "]["relevance_score"] < 0.3
    assert all(a["added"] for a in empty_client.get("/api/imports/demo").json())
    w = empty_client.post("/api/chat", json={"message": "What should I focus on this week?"}).json()
    assert "Backpropagation" in w["answer"] and "Policy Gradients" in w["answer"] and "Linked to your goal" in w["answer"]


def test_goal_merges_across_statement_email_and_chat(empty_client):
    for step in (1, 2, 9, 10):
        add(empty_client, step)
    r = empty_client.post("/api/chat", json={"message": "I want a job at a startup that makes robots understand language"}).json()
    assert "backed by 3 sources" in r["memory_updates"][0]
    goal = next(p for p in store.list_propositions(SID) if "startup" in p.statement and p.category == "goal")
    assert len(goal.evidence_ids) == 3
    labels = [e["label"] for e in empty_client.get("/api/memory/model").json()["proposition_evidence"][goal.id]]
    assert any(l.startswith("Career goals") for l in labels) and any(l.startswith("Email you sent") for l in labels)


def test_received_email_is_not_mined_for_goals(empty_client):
    add(empty_client, 2)
    add(empty_client, 11)  # seminar announcement, not written by the student
    assert store.list_propositions(SID) == []


def test_readd_is_idempotent(empty_client):
    add(empty_client, 1)
    assert add(empty_client, 1)["changes"] == ["Already added — nothing new was learned from this file."]


def test_unsupported_file_rejected(empty_client):
    r = upload(empty_client, None, data=b"hello", name="notes.txt")
    assert r.status_code == 400 and "Unsupported file type" in r.json()["detail"]


def test_authored_upload_learns_goals(empty_client):
    from app.demo_content import OUT
    path = OUT / STEP[9]
    r = upload(empty_client, path, authored=True, name="my_statement.pdf")
    assert r.json()["kind"] == "personal_document" and r.json()["goals_added"] >= 1


def test_reset_empties_but_keeps_privacy_mode(empty_client):
    empty_client.post("/api/settings/privacy", json={"mode": "local"})
    add(empty_client, 1)
    empty_client.post("/api/demo/reset")
    d = empty_client.get("/api/dashboard").json()
    assert d["knowledge"]["concepts"] == 0
    assert empty_client.get("/api/settings/privacy").json()["mode"] == "local"


# ---- About me (tell mode) --------------------------------------------------------
def tell(c, msg):
    return c.post("/api/chat", json={"message": msg, "mode": "tell"}).json()


def test_tell_saves_pattern_statements(empty_client):
    r = tell(empty_client, "My career goal is to build robots that follow spoken instructions")
    assert r["intent"] == "memory_update" and r["memory_updates"][0].startswith("Saved goal")
    assert "route:tell" in r["trace"] and r["llm_used"] is False


def test_tell_saves_anything_as_closest_category(empty_client):
    tell(empty_client, "Robotics competitions are my favorite thing")  # no pattern, no keyword -> note
    tell(empty_client, "Group study in the evenings works for me")      # keyword -> preference
    cats = {p.statement[:20]: p.category for p in store.list_propositions(SID)}
    assert cats["Robotics competition"] == "other" and cats["Group study in the e"] == "preference"


def test_tell_confidence_is_separate_from_mastery(empty_client):
    add(empty_client, 1)
    add(empty_client, 6)
    r = tell(empty_client, "I'm confident about backpropagation")
    assert "Kept separate from your quiz-based mastery" in r["answer"] and "blind spot" in r["answer"]
    m = {c["concept_id"]: c for c in empty_client.get("/api/memory/model").json()["concepts"]}
    assert m["backpropagation"]["mastery"] < 0.2 and m["backpropagation"]["self_confidence"] == 0.8


def test_ask_mode_question_is_not_saved(empty_client):
    empty_client.post("/api/chat", json={"message": "What should I focus on this week?", "mode": "ask"})
    assert store.list_propositions(SID) == []
