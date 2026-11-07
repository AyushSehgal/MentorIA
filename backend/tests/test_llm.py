import pytest

from app.config import settings
from app.orchestration import llm

SID = "demo_student"
Q = "What systems topics am I struggling with?"


class FakeResp:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


@pytest.fixture()
def fake_local(monkeypatch):
    """A fake OpenAI-compatible local server; records every request so tests can see what was sent."""
    calls = {"post": [], "reply": None}
    monkeypatch.setattr(settings, "llm_local_base_url", "http://localhost:11434/v1")
    monkeypatch.setattr(settings, "llm_local_model", "qwen2.5")
    monkeypatch.setattr(llm.requests, "get", lambda url, timeout: FakeResp({"data": [{"id": "qwen2.5:latest"}]}))

    def post(url, json, headers, timeout):
        calls["post"].append({"url": url, "json": json, "headers": headers})
        return FakeResp({"choices": [{"message": {"content": calls["reply"](json)}}]})

    monkeypatch.setattr(llm.requests, "post", post)
    return calls


def _draft_of(body):
    return body["messages"][1]["content"].split("DRAFT:\n", 1)[1]


def test_off_mode_makes_no_llm_call(client, fake_local):
    client.post("/api/documents/demo/graded_quiz")
    r = client.post("/api/chat", json={"message": Q}).json()
    assert r["llm_used"] is False and r["llm_provider"] is None and fake_local["post"] == []


def test_local_mode_rewords_and_reports_provider(client, fake_local):
    client.post("/api/documents/demo/graded_quiz")
    assert client.post("/api/settings/privacy", json={"mode": "local"}).json()["data_leaves_device"] is False
    fake_local["reply"] = lambda body: "<think>hmm</think>Reworded: " + _draft_of(body)
    r = client.post("/api/chat", json={"message": Q}).json()
    assert r["llm_used"] and r["llm_provider"] == "local:qwen2.5"
    assert r["answer"].startswith("Reworded:") and "<think>" not in r["answer"]
    assert fake_local["post"][0]["url"].startswith("http://localhost:11434/")


def test_rewrite_adding_numbers_is_discarded(client, fake_local):
    client.post("/api/documents/demo/graded_quiz")
    client.post("/api/settings/privacy", json={"mode": "local"})
    fake_local["reply"] = lambda body: _draft_of(body) + "\nYou scored 37% overall."
    r = client.post("/api/chat", json={"message": Q}).json()
    assert r["llm_used"] is False and "37" not in r["answer"] and "unsupported numbers" in r["llm_note"]


def test_rewrite_dropping_citations_is_discarded(client, fake_local):
    client.post("/api/documents/demo/graded_quiz")
    client.post("/api/settings/privacy", json={"mode": "local"})
    fake_local["reply"] = lambda body: "You are struggling with Cache Coherence (MESI) and Synchronization & Races."
    r = client.post("/api/chat", json={"message": Q}).json()
    assert r["llm_used"] is False and "Q2" in r["answer"] and "dropped grounded items" in r["llm_note"]


def test_local_unreachable_falls_back(client, monkeypatch):
    def down(url, timeout):
        raise ConnectionError("refused")

    monkeypatch.setattr(llm.requests, "get", down)
    client.post("/api/settings/privacy", json={"mode": "local"})
    r = client.post("/api/chat", json={"message": Q}).json()
    assert r["llm_used"] is False and "No local model server" in r["llm_note"]


def test_non_localhost_url_is_not_treated_as_local(client, fake_local, monkeypatch):
    monkeypatch.setattr(settings, "llm_local_base_url", "https://some-remote-host.example/v1")
    p = client.get("/api/settings/privacy").json()
    assert p["local_available"] is False and "not this machine" in p["local_detail"]


def test_cloud_unavailable_without_key(client, monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "")
    p = client.get("/api/settings/privacy").json()
    assert p["cloud_available"] is False


def test_openrouter_requests_no_data_collection(client, fake_local, monkeypatch):
    monkeypatch.setattr(settings, "llm_cloud_provider", "openrouter")
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key")
    monkeypatch.setattr(settings, "openrouter_model", "some/model")
    monkeypatch.setattr(settings, "openrouter_allow_data_collection", False)
    client.post("/api/documents/demo/graded_quiz")
    assert client.post("/api/settings/privacy", json={"mode": "cloud"}).json()["data_leaves_device"] is True
    fake_local["reply"] = _draft_of
    r = client.post("/api/chat", json={"message": Q}).json()
    sent = fake_local["post"][0]
    assert sent["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert sent["json"]["provider"] == {"data_collection": "deny"}
    assert r["llm_provider"] == "openrouter:some/model"


def test_privacy_choice_survives_demo_reset(client):
    client.post("/api/settings/privacy", json={"mode": "local"})
    client.post("/api/demo/reset")
    assert client.get("/api/settings/privacy").json()["mode"] == "local"


def test_default_mode_is_local(monkeypatch):
    from app.config import load_settings

    monkeypatch.delenv("LLM_MODE", raising=False)
    assert load_settings().llm_mode == "local"


def test_fresh_install_uses_local_until_user_changes_it(client, monkeypatch):
    from app import db

    monkeypatch.setattr(settings, "llm_mode", "local")
    db.execute("DELETE FROM meta WHERE key='llm_mode'")  # nothing chosen yet
    assert client.get("/api/settings/privacy").json()["mode"] == "local"
    assert client.get("/api/health").json()["llm"]["mode"] == "local"


def test_local_default_without_server_still_answers(client, monkeypatch):
    def down(url, timeout):
        raise ConnectionError("refused")

    monkeypatch.setattr(llm.requests, "get", down)
    monkeypatch.setattr(settings, "llm_mode", "local")
    r = client.post("/api/chat", json={"message": Q}).json()
    assert r["answer"] and r["llm_used"] is False and "No local model server" in r["llm_note"]
