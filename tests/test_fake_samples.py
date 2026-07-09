"""Tests for fake development sample source."""

from le_tour.domain.fake_samples import FakeTrainerSampleSource
from le_tour.domain.state import RideMode, RideSnapshot


def test_fake_source_emit_once_uses_domain_handlers():
    """Fake samples are delivered through the supplied sample handlers."""
    bike_samples = []
    hr_samples = []
    snapshot = RideSnapshot(active=True, session_state="active", mode=RideMode.FREE)
    source = FakeTrainerSampleSource(
        bike_samples.append,
        hr_samples.append,
        lambda: snapshot,
        seed=1,
    )

    source.emit_once(now_s=1_700_000_000.0)

    assert len(bike_samples) == 1
    assert len(hr_samples) == 1
    assert bike_samples[0]["power_w"] is not None
    assert bike_samples[0]["cadence_rpm"] is not None
    assert bike_samples[0]["speed_mps"] is not None
    assert hr_samples[0]["hr_bpm"] is not None


def test_fake_source_skips_inactive_or_paused_snapshots():
    """Fake source does not publish samples for inactive or paused rides."""
    bike_samples = []
    hr_samples = []
    snapshot = RideSnapshot(active=True, paused=True, session_state="paused")
    source = FakeTrainerSampleSource(
        bike_samples.append,
        hr_samples.append,
        lambda: snapshot,
        seed=1,
    )

    source.emit_once(now_s=1_700_000_000.0)

    assert bike_samples == []
    assert hr_samples == []


def test_fake_source_erg_tracks_target_power():
    """ERG fake samples move toward the requested target."""
    source = FakeTrainerSampleSource(
        lambda sample: None,
        lambda sample: None,
        lambda: RideSnapshot(
            active=True,
            session_state="active",
            mode=RideMode.ERG,
            erg_target_w=250,
        ),
        seed=1,
    )
    snapshot = RideSnapshot(
        active=True,
        session_state="active",
        mode=RideMode.ERG,
        erg_target_w=250,
    )

    first = source.next_bike_sample(snapshot, 1_700_000_000.0)
    second = source.next_bike_sample(snapshot, 1_700_000_001.0)

    assert second["power_w"] > first["power_w"]


def test_fake_source_hold_settles_onto_target_with_trainer_noise():
    """Holding a wattage looks like real trainer output: power approaches the
    target over a couple of seconds and every sample wobbles a few percent -
    never a flat line."""
    snapshot = RideSnapshot(active=True, session_state="active", mode=RideMode.FREE)
    source = FakeTrainerSampleSource(
        lambda sample: None,
        lambda sample: None,
        lambda: snapshot,
        seed=1,
    )

    source.set_manual_power(275)
    samples = [
        source.next_bike_sample(snapshot, 1_700_000_000.0 + second)
        for second in range(12)
    ]
    settled = [sample["power_w"] for sample in samples[5:]]

    # Settles near the target...
    assert all(abs(power - 275) < 275 * 0.08 for power in settled)
    # ...but is never a flat line (pedal-stroke wobble).
    assert len(set(settled)) > 1
    assert all(sample["cadence_rpm"] > 0 for sample in samples[3:])


def test_fake_source_ramp_builds_progressively():
    """A ramp climbs from the current effort to the target over the window."""
    snapshot = RideSnapshot(active=True, session_state="active", mode=RideMode.FREE)
    source = FakeTrainerSampleSource(
        lambda sample: None, lambda sample: None, lambda: snapshot, seed=1
    )
    source.set_effort("hold", power_w=120)
    for second in range(6):
        source.next_bike_sample(snapshot, 1_700_000_000.0 + second)

    source.set_effort("ramp", power_w=360, duration_s=30)
    powers = [
        source.next_bike_sample(snapshot, 1_700_000_010.0 + second)["power_w"]
        for second in range(40)
    ]

    # Monotonic-ish build: midpoint sits between start and target...
    assert 150 < powers[15] < 330
    # ...and the ramp lands on the target and holds it.
    assert abs(powers[-1] - 360) < 360 * 0.08
    assert source.effort["action"] == "hold"


def test_fake_source_sprint_attacks_peaks_and_sits_up():
    """A sprint rises fast, fades with fatigue, then returns to the base."""
    snapshot = RideSnapshot(active=True, session_state="active", mode=RideMode.FREE)
    source = FakeTrainerSampleSource(
        lambda sample: None, lambda sample: None, lambda: snapshot, seed=1
    )
    source.set_effort("hold", power_w=180)
    for second in range(8):
        source.next_bike_sample(snapshot, 1_700_000_000.0 + second)

    source.set_effort("sprint", power_w=700, duration_s=10)
    powers = [
        source.next_bike_sample(snapshot, 1_700_000_010.0 + second)["power_w"]
        for second in range(20)
    ]

    peak = max(powers[:10])
    assert peak > 550  # attacked hard
    assert powers[3] > powers[9] or peak > powers[9]  # fatigue fades the burst
    # After the sprint the rider sits up and returns toward the base effort.
    assert abs(powers[-1] - 180) < 60
    assert source.effort["action"] == "hold"


def test_fake_source_manual_power_zero_means_coasting():
    """Stopping pedaling reads as ~0 W within a couple of samples."""
    snapshot = RideSnapshot(active=True, session_state="active", mode=RideMode.FREE)
    source = FakeTrainerSampleSource(
        lambda sample: None, lambda sample: None, lambda: snapshot, seed=1
    )

    source.set_manual_power(0)
    samples = [
        source.next_bike_sample(snapshot, 1_700_000_000.0 + second)
        for second in range(4)
    ]

    assert samples[-1]["power_w"] < 3
    assert samples[-1]["cadence_rpm"] == 0


def test_fake_source_manual_power_clamps_and_clears():
    """Manual power is clamped to sane watts; None returns to auto mode."""
    snapshot = RideSnapshot(active=True, session_state="active", mode=RideMode.FREE)
    source = FakeTrainerSampleSource(
        lambda sample: None, lambda sample: None, lambda: snapshot, seed=1
    )

    assert source.set_manual_power(-50) == 0.0
    assert source.set_manual_power(9999) == 1500.0
    assert source.set_manual_power(None) is None
    assert source.manual_power_w is None
    assert source.effort["action"] == "auto"

    auto_sample = source.next_bike_sample(snapshot, 1_700_000_000.0)
    assert auto_sample["power_w"] > 0
