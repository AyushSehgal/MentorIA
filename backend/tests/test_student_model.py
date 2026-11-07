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
