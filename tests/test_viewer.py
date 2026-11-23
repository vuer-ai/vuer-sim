"""The editor's save/load protocol. The endpoint needs no vuer; ``attach`` does (heavy)."""

import asyncio
import json

import pytest

from vuer_sim import MaterialTable, PhysicsMaterial
from vuer_sim.viewer import EVENTS, MaterialsEndpoint, attach


def test_load_creates_empty_table(tmp_path):
    ep = MaterialsEndpoint(tmp_path)
    reply = ep.load()
    assert reply["revision"] == 0 and reply["saved"] is False
    assert MaterialTable.loads(reply["json"]) == MaterialTable()


def test_save_round_trip(tmp_path):
    ep = MaterialsEndpoint(tmp_path)
    t = MaterialTable(
        physics={"wood": PhysicsMaterial("wood", restitution=0.5, friction=(0.4, 0.005, 0.0001))},
        assign={"table_*": "wood"},
    )
    # The browser sends JSON text it built itself (any key order, any indent).
    sent = json.dumps(t.to_dict())
    reply = ep.save({"json": sent, "revision": 0})
    assert reply["saved"] and reply["revision"] == 1
    assert reply["json"] == t.dumps()  # stored form comes back
    assert MaterialTable.load(tmp_path) == t
    assert (tmp_path / "materials.json").read_text() == t.dumps()


def test_save_rejects_stale_revision_and_bad_tables(tmp_path):
    ep = MaterialsEndpoint(tmp_path)
    ok = ep.save({"json": MaterialTable().dumps(), "revision": 0})
    assert ok["revision"] == 1
    stale = ep.save({"json": MaterialTable().dumps(), "revision": 0})
    assert "stale" in stale["error"]
    bad = ep.save({"json": '{"assign": {"x": "missing"}}', "revision": 1})
    assert "unknown materials" in bad["error"]
    assert ep.revision == 1


class FakeApp:
    def __init__(self):
        self.handlers = {}

    def add_handler(self, etype, fn):
        self.handlers[etype] = fn


class FakeSession:
    def __init__(self):
        self.sent = []

    def send(self, event):
        self.sent.append(event)


class FakeEvent:
    def __init__(self, value):
        self.value = value


@pytest.mark.viewer
def test_attach_with_vuer_events(tmp_path):
    pytest.importorskip("vuer")
    app, session = FakeApp(), FakeSession()
    attach(app, tmp_path, scene=[{"name": "floor"}])
    assert set(app.handlers) == {EVENTS["load"], EVENTS["save"]}
    asyncio.run(app.handlers[EVENTS["load"]](FakeEvent({}), session))
    event = session.sent[-1]
    assert event.etype == EVENTS["table"]
    assert event.data["scene"] == [{"name": "floor"}]
    body = event._serialize()
    assert body["etype"] == "VUER_SIM_MATERIALS" and isinstance(body["data"]["json"], str)
    table = MaterialTable(physics={"m": PhysicsMaterial("m")})
    asyncio.run(app.handlers[EVENTS["save"]](FakeEvent({"json": table.dumps(), "revision": 0}), session))
    assert session.sent[-1].data["saved"] is True
    assert MaterialTable.load(tmp_path) == table
