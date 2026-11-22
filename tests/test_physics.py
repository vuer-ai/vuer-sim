import math
import xml.etree.ElementTree as ET

import pytest

from vuer_sim import (
    PhysicsMaterial,
    dampratio_to_restitution,
    mjcf_defaults,
    restitution_to_dampratio,
    solref_restitution,
)
from vuer_sim.physics import max_stable_timestep


@pytest.mark.parametrize("e", [0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99])
def test_restitution_dampratio_round_trip(e):
    z = restitution_to_dampratio(e)
    assert 0 < z < 1
    assert dampratio_to_restitution(z) == pytest.approx(e, abs=1e-12)


def test_restitution_limits():
    assert restitution_to_dampratio(0.0) == 1.0
    assert restitution_to_dampratio(1.0) == 0.0
    assert dampratio_to_restitution(1.0) == 0.0
    assert dampratio_to_restitution(3.0) == 0.0  # over-damped is lossy: maps back to e = 0
    assert dampratio_to_restitution(0.0) == 1.0
    with pytest.raises(ValueError):
        restitution_to_dampratio(1.5)
    with pytest.raises(ValueError):
        dampratio_to_restitution(-0.1)


def test_known_value():
    # z = 0.5 -> e = exp(-pi * 0.5 / sqrt(0.75)) = 0.163
    assert dampratio_to_restitution(0.5) == pytest.approx(math.exp(-math.pi / math.sqrt(3)))


def test_direct_solref():
    # direct form: -stiffness, -damping; z = b / (2 sqrt(k))
    assert solref_restitution((-10000.0, -100.0)) == pytest.approx(dampratio_to_restitution(0.5))
    m = PhysicsMaterial(solref=(-10000.0, -100.0), restitution=0.5)
    assert m.solref[0] == -10000.0
    assert solref_restitution(m.solref) == pytest.approx(0.5)


def test_restitution_sets_solref():
    m = PhysicsMaterial(restitution=0.5)
    assert m.solref == (0.02, pytest.approx(restitution_to_dampratio(0.5)))
    d = PhysicsMaterial(solref=(0.01, 0.3))
    assert d.restitution == pytest.approx(dampratio_to_restitution(0.3))
    assert PhysicsMaterial().restitution == 0.0


def test_dict_round_trip():
    m = PhysicsMaterial(
        "rubber",
        friction=(0.9, 0.01, 0.001),
        restitution=0.7,
        density=1200,
        solimp=(0.95, 0.99, 0.001, 0.5, 2),
        condim=4,
        priority=1,
        margin=0.001,
    )
    back = PhysicsMaterial.from_dict(m.to_dict(), name="rubber")
    assert back == m
    edited = m.to_dict() | {"restitution": 0.2}  # the editor changes restitution only
    assert PhysicsMaterial.from_dict(edited).solref[1] == pytest.approx(restitution_to_dampratio(0.2))


def test_short_vectors_and_validation():
    m = PhysicsMaterial(friction=0.5, solimp=(0.8, 0.9, 0.01))
    assert m.friction == (0.5, 0.005, 0.0001)
    assert m.solimp == (0.8, 0.9, 0.01, 0.5, 2.0)
    with pytest.raises(ValueError):
        PhysicsMaterial(condim=2)
    with pytest.raises(ValueError):
        PhysicsMaterial.from_dict({"frictoin": 1})


def test_mjcf_geom_round_trip():
    m = PhysicsMaterial("wood", friction=(0.4, 0.005, 0.0001), restitution=0.5, density=700, margin=0.002)
    el = ET.Element("geom", m.to_mjcf())
    back = PhysicsMaterial.from_mjcf(el, name="wood")
    assert back == m
    assert back.restitution == pytest.approx(0.5, abs=1e-12)
    text = ET.tostring(el, encoding="unicode")
    assert PhysicsMaterial.from_mjcf(text, name="wood") == m


def test_mjcf_number_format():
    attrs = PhysicsMaterial(friction=(1, 0.005, 0.0001)).to_mjcf()
    assert attrs["friction"] == "1 0.005 0.0001"
    assert attrs["solref"] == "0.02 1"
    assert attrs["density"] == "1000"


def test_mjcf_default_class_round_trip():
    m = PhysicsMaterial("glass", friction=(0.5, 0.005, 0.0001), restitution=0.6, density=2500)
    el = m.to_mjcf_default()
    assert el.get("class") == "glass"
    assert PhysicsMaterial.from_mjcf(el) == m


def test_mjcf_defaults_inheritance():
    root = ET.fromstring(
        """<mujoco><default>
             <geom friction="0.8" density="500"/>
             <default class="soft"><geom solref="0.02 0.3"/>
               <default class="softer"><geom friction="1.2 0.01"/></default>
             </default>
           </default></mujoco>"""
    )
    d = mjcf_defaults(root)
    assert set(d) == {"main", "soft", "softer"}
    assert d["main"].friction == (0.8, 0.005, 0.0001)
    assert d["soft"].density == 500 and d["soft"].friction[0] == 0.8
    assert d["soft"].restitution == pytest.approx(dampratio_to_restitution(0.3))
    assert d["softer"].friction == (1.2, 0.01, 0.0001)
    assert d["softer"].solref == (0.02, 0.3)


def test_partial_geom_keeps_defaults():
    m = PhysicsMaterial.from_mjcf({"friction": "0.3"})
    assert m.friction == (0.3, 0.005, 0.0001)
    assert m.solref == (0.02, 1.0) and m.density == 1000


def test_max_stable_timestep():
    assert max_stable_timestep(0.02, 0.0) == pytest.approx(0.01)  # MuJoCo's timeconst >= 2 dt
    assert max_stable_timestep(0.02, 0.8) == pytest.approx(0.02 * restitution_to_dampratio(0.8))
    assert PhysicsMaterial(restitution=0.9).max_stable_timestep() < 0.002
