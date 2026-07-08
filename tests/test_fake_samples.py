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


def test_fake_source_manual_power_is_exact_and_deterministic():
    """The virtual trainer emits rider-set watts exactly — step inputs for
    feel testing carry no wave or noise."""
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
        for second in range(5)
    ]

    assert all(sample["power_w"] == 275 for sample in samples)
    assert all(sample["cadence_rpm"] > 0 for sample in samples)


def test_fake_source_manual_power_zero_means_coasting():
    """0 W pins power and cadence to a coasting rider."""
    snapshot = RideSnapshot(active=True, session_state="active", mode=RideMode.FREE)
    source = FakeTrainerSampleSource(
        lambda sample: None, lambda sample: None, lambda: snapshot, seed=1
    )

    source.set_manual_power(0)
    sample = source.next_bike_sample(snapshot, 1_700_000_000.0)

    assert sample["power_w"] == 0
    assert sample["cadence_rpm"] == 0


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

    auto_sample = source.next_bike_sample(snapshot, 1_700_000_000.0)
    assert auto_sample["power_w"] > 0
