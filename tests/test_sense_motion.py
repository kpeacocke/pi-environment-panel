from pi_environment_panel.collectors.sense import _movement_g


def test_movement_g_stationary_gravity_vector():
    assert _movement_g({"x": 0.0, "y": 0.0, "z": 1.0}) == 0.0


def test_movement_g_detects_acceleration_change():
    assert round(_movement_g({"x": 0.0, "y": 0.0, "z": 1.2}), 3) == 0.2


def test_movement_g_handles_missing_axes():
    assert _movement_g({}) == 1.0
