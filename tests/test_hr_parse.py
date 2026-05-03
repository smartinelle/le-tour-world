"""Unit tests for BLE Heart Rate Measurement parser.

Tests cover:
- Basic HR value parsing (8-bit and 16-bit)
- Sensor contact detection
- Energy expended field
- RR interval parsing
- Edge cases and malformed data
"""

import pytest
from le_tour.devices.hr_parse import parse_heart_rate_measurement


class TestBasicHrParsing:
    """Tests for basic heart rate value parsing."""

    def test_8bit_hr_value(self):
        """Parse 8-bit HR value (most common format)."""
        # Flags=0x00: 8-bit HR, no contact support, no energy, no RR
        data = bytes([0x00, 72])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 72
        assert parsed.flags == 0x00
        assert not parsed.sensor_contact_supported
        assert parsed.sensor_contact_detected is None

    def test_16bit_hr_value(self):
        """Parse 16-bit HR value (for HR > 255 or high precision devices)."""
        # Flags=0x01: 16-bit HR
        # HR = 180 = 0x00B4
        data = bytes([0x01, 0xB4, 0x00])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 180
        assert parsed.flags == 0x01

    def test_high_16bit_hr_value(self):
        """Parse 16-bit HR value above 255."""
        # This is rare but the spec allows it
        # HR = 300 = 0x012C
        data = bytes([0x01, 0x2C, 0x01])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 300

    def test_zero_hr(self):
        """Parse zero HR (no pulse detected)."""
        data = bytes([0x00, 0])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 0

    def test_max_8bit_hr(self):
        """Parse maximum 8-bit HR (255)."""
        data = bytes([0x00, 255])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 255


class TestSensorContact:
    """Tests for sensor contact detection."""

    def test_contact_not_supported(self):
        """Sensor contact not supported (bits 1-2 = 00)."""
        data = bytes([0x00, 72])  # Flags = 0b00000000
        parsed = parse_heart_rate_measurement(data)

        assert not parsed.sensor_contact_supported
        assert parsed.sensor_contact_detected is None

    def test_contact_supported_not_detected(self):
        """Sensor contact supported but not detected (bits 1-2 = 10)."""
        data = bytes([0x04, 72])  # Flags = 0b00000100
        parsed = parse_heart_rate_measurement(data)

        assert parsed.sensor_contact_supported
        assert parsed.sensor_contact_detected is False

    def test_contact_supported_and_detected(self):
        """Sensor contact supported and detected (bits 1-2 = 11)."""
        data = bytes([0x06, 72])  # Flags = 0b00000110
        parsed = parse_heart_rate_measurement(data)

        assert parsed.sensor_contact_supported
        assert parsed.sensor_contact_detected is True

    def test_contact_bits_01_not_supported(self):
        """Contact bits = 01 means not supported."""
        data = bytes([0x02, 72])  # Flags = 0b00000010
        parsed = parse_heart_rate_measurement(data)

        assert not parsed.sensor_contact_supported
        assert parsed.sensor_contact_detected is None


class TestEnergyExpended:
    """Tests for energy expended field."""

    def test_no_energy_field(self):
        """No energy expended field present."""
        data = bytes([0x00, 72])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.energy_expended_kj is None

    def test_energy_field_present(self):
        """Energy expended field present (bit 3 = 1)."""
        # Flags = 0x08: energy present
        # HR = 72
        # Energy = 150 kJ = 0x0096
        data = bytes([0x08, 72, 0x96, 0x00])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.energy_expended_kj == 150

    def test_energy_with_16bit_hr(self):
        """Energy field with 16-bit HR."""
        # Flags = 0x09: 16-bit HR + energy
        # HR = 180 = 0x00B4
        # Energy = 500 kJ = 0x01F4
        data = bytes([0x09, 0xB4, 0x00, 0xF4, 0x01])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 180
        assert parsed.energy_expended_kj == 500


class TestRRIntervals:
    """Tests for RR interval parsing."""

    def test_no_rr_intervals(self):
        """No RR intervals present."""
        data = bytes([0x00, 72])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.rr_intervals_ms == []

    def test_single_rr_interval(self):
        """Single RR interval present (bit 4 = 1)."""
        # Flags = 0x10: RR present
        # HR = 72
        # RR = 800 ms ≈ 819 in 1/1024 sec units (0x0333)
        rr_raw = int(800 * 1024 / 1000)  # Convert ms to 1/1024 sec
        data = bytes([0x10, 72, rr_raw & 0xFF, (rr_raw >> 8) & 0xFF])
        parsed = parse_heart_rate_measurement(data)

        assert len(parsed.rr_intervals_ms) == 1
        assert abs(parsed.rr_intervals_ms[0] - 800) < 2  # Allow rounding

    def test_multiple_rr_intervals(self):
        """Multiple RR intervals present."""
        # Flags = 0x10: RR present
        # HR = 72
        # RR1 = 800 ms, RR2 = 750 ms
        rr1_raw = int(800 * 1024 / 1000)
        rr2_raw = int(750 * 1024 / 1000)
        data = bytes(
            [
                0x10,
                72,
                rr1_raw & 0xFF,
                (rr1_raw >> 8) & 0xFF,
                rr2_raw & 0xFF,
                (rr2_raw >> 8) & 0xFF,
            ]
        )
        parsed = parse_heart_rate_measurement(data)

        assert len(parsed.rr_intervals_ms) == 2
        assert abs(parsed.rr_intervals_ms[0] - 800) < 2
        assert abs(parsed.rr_intervals_ms[1] - 750) < 2

    def test_rr_with_energy(self):
        """RR intervals with energy field."""
        # Flags = 0x18: energy + RR present
        # HR = 72
        # Energy = 100 kJ
        # RR = 850 ms
        rr_raw = int(850 * 1024 / 1000)
        data = bytes(
            [
                0x18,
                72,
                0x64,
                0x00,  # Energy = 100
                rr_raw & 0xFF,
                (rr_raw >> 8) & 0xFF,
            ]
        )
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 72
        assert parsed.energy_expended_kj == 100
        assert len(parsed.rr_intervals_ms) == 1
        assert abs(parsed.rr_intervals_ms[0] - 850) < 2


class TestComplexPackets:
    """Tests for complex packets with multiple fields."""

    def test_all_fields_present(self):
        """All optional fields present."""
        # Flags = 0x1F: 16-bit HR + contact + energy + RR
        # HR = 165 = 0x00A5
        # Energy = 200 kJ = 0x00C8
        # RR = 700 ms
        rr_raw = int(700 * 1024 / 1000)
        data = bytes(
            [
                0x1F,  # All flags
                0xA5,
                0x00,  # HR
                0xC8,
                0x00,  # Energy
                rr_raw & 0xFF,
                (rr_raw >> 8) & 0xFF,  # RR
            ]
        )
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 165
        assert parsed.sensor_contact_supported
        assert parsed.sensor_contact_detected is True
        assert parsed.energy_expended_kj == 200
        assert len(parsed.rr_intervals_ms) == 1

    def test_wahoo_tickr_typical_packet(self):
        """Typical packet from Wahoo TICKR."""
        # TICKR typically sends: 8-bit HR, contact supported+detected, RR intervals
        # Flags = 0x16: contact detected + RR present
        rr_raw = int(750 * 1024 / 1000)
        data = bytes([0x16, 145, rr_raw & 0xFF, (rr_raw >> 8) & 0xFF])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 145
        assert parsed.sensor_contact_supported
        assert parsed.sensor_contact_detected is True
        assert len(parsed.rr_intervals_ms) == 1

    def test_garmin_hrm_typical_packet(self):
        """Typical packet from Garmin HRM."""
        # Garmin HRM-Pro sends similar format
        rr1 = int(800 * 1024 / 1000)
        rr2 = int(790 * 1024 / 1000)
        data = bytes(
            [
                0x16,
                155,  # Flags + HR
                rr1 & 0xFF,
                (rr1 >> 8) & 0xFF,
                rr2 & 0xFF,
                (rr2 >> 8) & 0xFF,
            ]
        )
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 155
        assert len(parsed.rr_intervals_ms) == 2


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_too_short_data(self):
        """Data shorter than minimum 2 bytes raises error."""
        with pytest.raises(ValueError, match="too short"):
            parse_heart_rate_measurement(bytes([0x00]))

    def test_empty_data(self):
        """Empty data raises error."""
        with pytest.raises(ValueError, match="too short"):
            parse_heart_rate_measurement(bytes([]))

    def test_16bit_hr_missing_second_byte(self):
        """16-bit HR flag but only 2 bytes total raises error."""
        with pytest.raises(ValueError, match="too short for 16-bit"):
            parse_heart_rate_measurement(bytes([0x01, 72]))

    def test_energy_missing_bytes(self):
        """Energy flag but insufficient bytes raises error."""
        with pytest.raises(ValueError, match="too short for energy"):
            parse_heart_rate_measurement(bytes([0x08, 72, 0x00]))

    def test_truncated_rr_interval(self):
        """Single byte for RR interval is ignored (need 2 bytes)."""
        # RR flag set but only 1 extra byte - should parse HR but skip RR
        data = bytes([0x10, 72, 0x50])  # Only 1 byte for RR
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 72
        assert parsed.rr_intervals_ms == []  # Incomplete RR ignored

    def test_extra_bytes_ignored(self):
        """Extra bytes at end are ignored."""
        data = bytes([0x00, 72, 0xFF, 0xFF, 0xFF])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.hr_bpm == 72


class TestDataclass:
    """Tests for ParsedHrData dataclass."""

    def test_dataclass_is_frozen(self):
        """ParsedHrData is immutable."""
        data = bytes([0x00, 72])
        parsed = parse_heart_rate_measurement(data)

        with pytest.raises(AttributeError):
            parsed.hr_bpm = 100  # type: ignore

    def test_flags_preserved(self):
        """Original flags byte is preserved for debugging."""
        data = bytes([0x16, 72, 0x00, 0x03])
        parsed = parse_heart_rate_measurement(data)

        assert parsed.flags == 0x16
