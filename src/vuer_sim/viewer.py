"""The material editor's Python side: vuer events that load and save a ``MaterialTable``.

Needs vuer: ``pip install 'vuer-sim[viewer]'``. The editing UI is
``@vuer-ai/vuer-sim`` (``MaterialInspector``, ``PhysicsMaterialEditor``,
``SensorMaterialOverlay``, ``useMaterialTable``).

Wire protocol (vuer events; ``EVENTS`` holds the names):

=====================================  =======================================================
Client -> server                       Server -> client
=====================================  =======================================================
``VUER_SIM_MATERIALS_LOAD`` ``{}``     ``VUER_SIM_MATERIALS`` ``{json, path, saved: false,
                                       revision, scene}``
``VUER_SIM_MATERIALS_SAVE``            ``VUER_SIM_MATERIALS`` ``{json, path, saved: true,
``{json, revision}``                   revision}``, or ``{error, revision}`` when the table
                                       does not validate or the revision is stale
=====================================  =======================================================

The table travels as its stored JSON text, not as a msgpack map: vuer packs
server floats as float32 (``use_single_float``), which would change values
such as ``0.005`` on the way to the browser.

``revision`` counts the saves. A save whose ``revision`` is older than the
file's is refused, so a second browser tab cannot silently overwrite a newer
table.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .table import MaterialTable

EVENTS = {
    "load": "VUER_SIM_MATERIALS_LOAD",
    "save": "VUER_SIM_MATERIALS_SAVE",
    "table": "VUER_SIM_MATERIALS",
}


class MaterialsEndpoint:
    """The load/save logic, without vuer (tests call it directly)."""

    def __init__(self, bundle: str | os.PathLike, scene: list[dict[str, Any]] | None = None):
        self.path = MaterialTable.path(bundle)
        self.scene = scene
        self.revision = 0
        if not self.path.exists():
            MaterialTable().save(self.path)

    def load(self) -> dict[str, Any]:
        text = self.path.read_text(encoding="utf-8")
        return {
            "json": text,
            "path": str(self.path),
            "saved": False,
            "revision": self.revision,
            "scene": self.scene,
        }

    def save(self, value: Any) -> dict[str, Any]:
        value = value or {}
        revision = int(value.get("revision", self.revision))
        if revision != self.revision:
            return {
                "error": f"stale revision {revision}; the file is at {self.revision}. Reload first.",
                "revision": self.revision,
            }
        try:
            table = MaterialTable.loads(str(value["json"]))
        except Exception as e:  # report every validation error to the editor
            return {"error": f"{type(e).__name__}: {e}", "revision": self.revision}
        table.save(self.path)
        self.revision += 1
        return {
            "json": self.path.read_text(encoding="utf-8"),
            "path": str(self.path),
            "saved": True,
            "revision": self.revision,
        }


def attach(
    app: Any, bundle: str | os.PathLike | MaterialsEndpoint, scene: list[dict[str, Any]] | None = None
) -> MaterialsEndpoint:
    """Register the load and save handlers on a ``vuer.Vuer`` app. Return the endpoint."""
    from vuer.events import ServerEvent

    class MaterialsEvent(ServerEvent):
        etype = EVENTS["table"]

    endpoint = bundle if isinstance(bundle, MaterialsEndpoint) else MaterialsEndpoint(bundle, scene)

    async def on_load(event: Any, session: Any) -> None:
        session.send(MaterialsEvent(endpoint.load()))

    async def on_save(event: Any, session: Any) -> None:
        session.send(MaterialsEvent(endpoint.save(event.value)))

    app.add_handler(EVENTS["load"], on_load)
    app.add_handler(EVENTS["save"], on_save)
    return endpoint


def serve(
    bundle: str | os.PathLike, scene: list[dict[str, Any]] | None = None, port: int = 8012, **kwargs: Any
) -> None:
    """Run a vuer server that serves the table of ``bundle`` to the editor (blocks)."""
    from vuer import Vuer

    app = Vuer(port=port, **kwargs)
    endpoint = attach(app, bundle, scene)
    print(f"vuer-sim: editing {Path(endpoint.path)} on ws://localhost:{port}")
    app.run()
