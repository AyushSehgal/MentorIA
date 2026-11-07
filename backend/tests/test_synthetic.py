"""Source-pack (.md) import: the synthetic world file is just a pack you can add."""
import pytest

from app import synthetic
from app.memory import store

from .conftest import PACK, SID, upload


def test_pack_parses():
    w = synthetic.parse_world(PACK.read_text(encoding="utf-8"))
    assert {c["id"] for c in w["courses"]} == {"systems", "robot_learning"}
    assert len(w["concepts"]) == 8
    assert {k: len(v) for k, v in w["records"].items()} == {"canvas": 5, "google_calendar": 9, "gmail": 4, "piazza": 3, "edstem": 0}
    assert len(w["profile"]["seed_observations"]) == 5


def test_bad_reference_gives_clear_error():
    text = PACK.read_text(encoding="utf-8").replace("| d+9 23:59 | synchronization |", "| d+9 23:59 | sync_typo |")
    with pytest.raises(synthetic.SyntheticDataError, match="sync_typo"):
        synthetic.parse_world(text)


def test_pack_referencing_unknown_course_is_rejected(empty_client):
    pack = "## Canvas assignments\n\n| id | course | title | due |\n|---|---|---|---|\n| x1 | nope | HW | d+1 10:00 |\n"
    r = upload(empty_client, PACK, data=pack.encode(), name="bad.md")
    assert r.status_code == 400 and "unknown course" in r.json()["detail"]


def test_reimport_edited_pack_updates_items(client):
    text = PACK.read_text(encoding="utf-8").replace("Cache Lab Part B: coherence simulator", "Cache Lab Part B (edited)")
    r = upload(client, PACK, data=text.encode(), name="world_v2.md")
    assert r.status_code == 200
    items = client.get("/api/dashboard").json()["cards"]["canvas"]["items"]
    assert any(i["title"] == "Cache Lab Part B (edited)" for i in items) and len(items) == 5


def test_invalid_pack_changes_nothing(client):
    before = len(store.list_records(SID))
    text = PACK.read_text(encoding="utf-8").replace("| cal_e2 | Computer Systems lecture | d+1 10:00 |",
                                                    "| cal_e2 | Computer Systems lecture | sometime |")
    r = upload(client, PACK, data=text.encode(), name="broken.md")
    assert r.status_code == 400 and "sometime" in r.json()["detail"]
    assert len(store.list_records(SID)) == before


def test_new_self_report_row_is_learned_once(client):
    text = PACK.read_text(encoding="utf-8").replace(
        "| obs_seed_conf_vm |",
        "| obs_new_interest | d+0 09:00 | interest | reinforcement_learning | | I'm curious about RL for legged robots. |\n| obs_seed_conf_vm |")
    upload(client, PACK, data=text.encode(), name="world_v3.md")
    upload(client, PACK, data=text.encode(), name="world_v3.md")
    assert sum("legged robots" in p.statement for p in store.list_propositions(SID)) == 1
