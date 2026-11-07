import os
import shutil
import time

import pytest

from app import synthetic
from app.config import settings
from app.memory import store

SID = "demo_student"


def test_world_file_parses():
    w = synthetic.parse_world(open(settings.synthetic_file, encoding="utf-8").read())
    assert {c["id"] for c in w["courses"]} == {"systems", "robot_learning"}
    assert len(w["concepts"]) == 8
    assert {k: len(v) for k, v in w["records"].items()} == {"canvas": 5, "google_calendar": 9, "gmail": 4, "piazza": 3}
    talk = next(r for r in w["records"]["gmail"] if r["external_id"] == "gmail_m1")
    assert talk["title"].startswith("Robotics Seminar") and "{when:d+3 16:00}" in talk["body"]
    assert w["profile"]["name"] == "Alex (demo student)" and len(w["profile"]["seed_observations"]) == 5


def test_bad_reference_gives_clear_error():
    text = open(settings.synthetic_file, encoding="utf-8").read().replace(
        "| canvas_a2 | systems | Proxy Lab checkpoint: concurrent proxy | d+9 23:59 | synchronization |",
        "| canvas_a2 | systems | Proxy Lab checkpoint: concurrent proxy | d+9 23:59 | sync_typo |")
    with pytest.raises(synthetic.SyntheticDataError, match="sync_typo"):
        synthetic.parse_world(text)


@pytest.fixture()
def world_copy(tmp_path, monkeypatch):
    path = tmp_path / "world.md"
    shutil.copy(settings.synthetic_file, path)
    monkeypatch.setattr(settings, "synthetic_file", path)
    synthetic.reset_cache()
    return path


def _edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new), encoding="utf-8")
    t = time.time() + 2  # make sure mtime changes even on coarse filesystems
    os.utime(path, (t, t))


def test_edit_shows_up_after_sync(client, world_copy):
    client.post("/api/demo/reset")
    _edit(world_copy, "Cache Lab Part B: coherence simulator", "Cache Lab Part B: MESI simulator (edited)")
    before = client.get("/api/dashboard").json()["cards"]["canvas"]["items"]
    assert not any("edited" in i["title"] for i in before)  # dashboard reflects synced data, not the raw file
    client.post("/api/connectors/sync")
    items = client.get("/api/dashboard").json()["cards"]["canvas"]["items"]
    assert any(i["title"] == "Cache Lab Part B: MESI simulator (edited)" for i in items)
    assert len(items) == 5  # replaced, not duplicated


def test_removed_record_disappears_after_sync(client, world_copy):
    client.post("/api/demo/reset")
    text = world_copy.read_text(encoding="utf-8")
    start = text.index("### Career Fair")
    end = text.index("### Systems Reading Group")
    world_copy.write_text(text[:start] + text[end:], encoding="utf-8")
    t = time.time() + 2
    os.utime(world_copy, (t, t))
    client.post("/api/connectors/sync")
    titles = [i["title"] for i in client.get("/api/dashboard").json()["cards"]["gmail"]["items"]]
    assert len(titles) == 3 and not any("Career Fair" in t for t in titles)


def test_invalid_edit_keeps_last_good_version(client, world_copy):
    client.post("/api/demo/reset")
    _edit(world_copy, "| cal_e2 | Computer Systems lecture | d+1 10:00 |", "| cal_e2 | Computer Systems lecture | sometime |")
    res = {r["provider"]: r for r in client.post("/api/connectors/sync").json()}
    cal = res["google_calendar"]
    assert cal["status"]["state"] == "demo_data" and "NOT loaded" in cal["status"]["detail"]
    assert cal["records_total"] == 9  # last valid version still served
    assert client.get("/api/dashboard").status_code == 200


def test_new_self_report_row_ingested_on_sync(client, world_copy):
    client.post("/api/demo/reset")
    _edit(world_copy, "| obs_seed_conf_vm |",
          "| obs_new_interest | d+0 09:00 | interest | reinforcement_learning | | I'm curious about RL for legged robots. |\n| obs_seed_conf_vm |")
    client.post("/api/connectors/sync")
    assert any("legged robots" in p.statement for p in store.list_propositions(SID))
    client.post("/api/connectors/sync")  # idempotent
    assert sum("legged robots" in p.statement for p in store.list_propositions(SID)) == 1
