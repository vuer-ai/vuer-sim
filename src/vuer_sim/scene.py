"""A light, JSON-ready description of the geoms of a MuJoCo model, for the editor."""

from __future__ import annotations

from typing import Any

GEOM_TYPES = {
    0: "plane",
    1: "hfield",
    2: "sphere",
    3: "capsule",
    4: "ellipsoid",
    5: "cylinder",
    6: "box",
    7: "mesh",
    8: "sdf",
}


def scene_summary(
    model: Any, data: Any = None, groups: tuple[int, ...] | None = None
) -> list[dict[str, Any]]:
    """One dict per geom: name, id, type, size, world pos and quat (w, x, y, z), rgba, material.

    Mesh, height-field and SDF geoms are given as their bounding box (``type``
    ``"box"``, ``source_type`` the real type). ``groups`` keeps only those geom
    groups. Needs ``mujoco`` to compute the world poses when ``data`` is ``None``.
    """
    import mujoco
    import numpy as np

    if data is None:
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
    out = []
    for gid in range(model.ngeom):
        group = int(model.geom_group[gid])
        if groups is not None and group not in groups:
            continue
        kind = GEOM_TYPES.get(int(model.geom_type[gid]), "box")
        mat = data.geom_xmat[gid].reshape(3, 3)
        pos = data.geom_xpos[gid].copy()
        size = model.geom_size[gid].copy()
        source = kind
        if kind in ("mesh", "hfield", "sdf"):
            center, half = model.geom_aabb[gid][:3], model.geom_aabb[gid][3:]
            pos = pos + mat @ center
            size, kind = half, "box"
        quat = np.zeros(4)
        mujoco.mju_mat2Quat(quat, mat.reshape(-1))
        matid = int(model.geom_matid[gid])
        out.append(
            {
                "id": gid,
                "name": model.geom(gid).name or f"#{gid}",
                "type": kind,
                "source_type": source,
                "size": [round(float(v), 6) for v in size],
                "pos": [round(float(v), 6) for v in pos],
                "quat": [round(float(v), 6) for v in quat],
                "rgba": [
                    round(float(v), 4)
                    for v in (model.mat_rgba[matid] if matid >= 0 else model.geom_rgba[gid])
                ],
                "material": model.material(matid).name if matid >= 0 else None,
                "body": model.body(int(model.geom_bodyid[gid])).name,
                "group": group,
            }
        )
    return out
