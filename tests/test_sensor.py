"""Statistics of lidar_returns on synthetic frames (the shape robot-env's RayLidar produces)."""

import numpy as np
import pytest

from vuer_sim import SensorArrays, SensorMaterial, lidar_returns

N = 200_000


def frame(geom: int, r: float, n: int = N):
    return np.full(n, geom, np.int32), np.full(n, r, np.float64)


def test_no_hit_and_defaults():
    geom = np.array([-1, 0, 0, -1], np.int32)
    r = np.array([0.0, 5.0, 0.0, 3.0])
    out = lidar_returns(geom, r, {0: SensorMaterial()}, rng=0)
    assert out.valid.tolist() == [False, True, False, False]
    assert out.ranges.tolist() == [0, 5, 0, 0]
    assert out.intensity.tolist() == [0, 75, 0, 0]  # round(150 * 0.5)


@pytest.mark.parametrize("p", [0.05, 0.3, 0.7])
def test_dropout_rate(p):
    out = lidar_returns(*frame(0, 2.0), {0: SensorMaterial(dropout=p)}, rng=1)
    assert 1 - out.valid.mean() == pytest.approx(p, abs=4 / np.sqrt(N))


def test_depth_noise_std():
    out = lidar_returns(*frame(0, 5.0), {0: SensorMaterial(depth_noise_std=0.02)}, rng=2)
    err = out.ranges[out.valid] - 5.0
    assert abs(err.mean()) < 4 * 0.02 / np.sqrt(N)
    assert err.std() == pytest.approx(0.02, rel=0.02)


def test_glass_passes_most_rays():
    glass = SensorMaterial(lidar_reflectivity=0.08, transparent=True)
    out = lidar_returns(*frame(0, 2.0), {0: glass}, rng=3)
    assert out.valid.mean() == pytest.approx(0.08, abs=4 * np.sqrt(0.08 * 0.92 / N))
    far = lidar_returns(*frame(0, 100.0), {0: glass}, rng=3)  # glass ignores the range law
    assert far.valid.mean() == pytest.approx(0.08, abs=0.005)


def test_black_surface_range_law():
    black = SensorMaterial(lidar_reflectivity=0.025)  # reach = 40 * sqrt(0.25) = 20 m
    near = lidar_returns(*frame(0, 19.9, 1000), {0: black}, rng=4)
    far = lidar_returns(*frame(0, 20.1, 1000), {0: black}, rng=4)
    assert near.valid.all() and not far.valid.any()
    white = SensorMaterial(lidar_reflectivity=0.9)  # reach 120 m
    assert lidar_returns(*frame(0, 60.0, 10), {0: white}, rng=4).valid.all()
    shorter = lidar_returns(*frame(0, 15.0, 10), {0: black}, rng=4, range_at_10pct=20.0)
    assert not shorter.valid.any()  # 20 * sqrt(0.25) = 10 m


def test_intensity():
    mats = {0: SensorMaterial(lidar_reflectivity=0.2), 1: SensorMaterial(intensity=200)}
    geom = np.array([0, 1, 1], np.int32)
    out = lidar_returns(geom, np.ones(3), mats, rng=0)
    assert out.intensity.tolist() == [30, 200, 200]
    assert out.intensity.dtype == np.float32


def test_mixed_frame_per_geom_rates():
    rng = np.random.default_rng(5)
    geom = rng.integers(-1, 3, N).astype(np.int32)
    r = rng.uniform(0.5, 10.0, N)
    arrays = SensorArrays.from_materials(
        [
            SensorMaterial(),
            SensorMaterial(dropout=0.5),
            SensorMaterial(lidar_reflectivity=0.1, transparent=True),
        ]
    )
    out = lidar_returns(geom, r, arrays, rng=6)
    assert not out.valid[geom == -1].any()
    assert out.valid[geom == 0].all()
    assert out.valid[geom == 1].mean() == pytest.approx(0.5, abs=0.01)
    assert out.valid[geom == 2].mean() == pytest.approx(0.1, abs=0.01)


def test_deterministic_for_a_seed():
    a = lidar_returns(*frame(0, 3.0, 1000), {0: SensorMaterial(dropout=0.3, depth_noise_std=0.01)}, rng=7)
    b = lidar_returns(*frame(0, 3.0, 1000), {0: SensorMaterial(dropout=0.3, depth_noise_std=0.01)}, rng=7)
    assert np.array_equal(a.valid, b.valid) and np.array_equal(a.ranges, b.ranges)


def test_max_range_and_errors():
    out = lidar_returns(
        *frame(0, 50.0, 10), {0: SensorMaterial(lidar_reflectivity=1.0)}, rng=0, max_range=40.0
    )
    assert not out.valid.any()
    with pytest.raises(ValueError):
        lidar_returns(np.zeros(3, np.int32), np.ones(2), {}, rng=0)
    with pytest.raises(ValueError):
        lidar_returns(np.array([5]), np.ones(1), SensorArrays.from_materials([SensorMaterial()]), rng=0)
    with pytest.raises(ValueError):
        SensorMaterial(dropout=1.5)


def test_empty_table_and_unlisted_geoms():
    out = lidar_returns(np.array([-1, -1]), np.ones(2), [], rng=0)
    assert not out.valid.any()
    out = lidar_returns(np.array([3]), np.ones(1), {0: SensorMaterial(dropout=1.0)}, rng=0)
    assert out.valid.all()  # geom 3 has no material: default sensor material
