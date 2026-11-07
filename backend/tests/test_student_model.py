"""Student Model page (T18): API behavior the map/inspector relies on."""
from app.memory import store, updates

SID = "demo_student"


def test_rapid_confidence_updates_all_apply(client):
    """Two slider saves within the same second must both land; the last one wins."""
    for v in (0.2, 0.35, 0.6):
        r = client.post("/api/memory/self_confidence", json={"student_id": SID, "concept_id": "cache_coherence", "value": v})
        assert r.status_code == 200 and r.json()["belief_updates"], r.text
    conf = store.get_belief(updates.confidence_belief_id(SID, "cache_coherence"))
    assert conf.value == 0.6
    obs = [o for o in store.list_observations(SID, "cache_coherence", "self_confidence") if o.event_id.startswith("obs_ui_conf_")]
    assert len(obs) == 3


# ---- About me: questions are answered from the model, never saved ------------------------------------------------
def _tell(c, msg):
    r = c.post("/api/chat", json={"message": msg, "student_id": SID, "mode": "tell"})
    assert r.status_code == 200, r.text
    return r.json()


def _saved():
    return (len(store.list_propositions(SID)), len(store.list_observations(SID)))


def test_about_me_question_is_answered_not_saved(empty_client):
    _tell(empty_client, "My career goal is to build robots that follow spoken instructions")
    before = _saved()
    r = _tell(empty_client, "What are my goals?")
    assert _saved() == before
    assert r["intent"] == "general" and "about_me" in r["trace"] and r["memory_updates"] == []
    assert "build robots that follow spoken instructions" in r["answer"] and r["llm_used"] is False


def test_about_me_question_with_self_report_words_is_not_saved(empty_client):
    before = _saved()
    for q in ("Am I confident in backpropagation?", "what do you know about me", "Tell me where I'm weakest"):
        r = _tell(empty_client, q)
        assert "about_me" in r["trace"], q
    assert _saved() == before


def test_about_me_statements_are_still_saved(empty_client):
    _tell(empty_client, "What I really want is to work on household robots")  # statement despite starting with "What"
    _tell(empty_client, "I prefer studying in the mornings")
    statements = [p.statement for p in store.list_propositions(SID)]
    assert any("household robots" in s for s in statements) and any("mornings" in s for s in statements)


def test_about_me_overview_is_honest_when_empty(empty_client):
    r = _tell(empty_client, "What do you know about me?")
    assert "don't know much about you yet" in r["answer"]
