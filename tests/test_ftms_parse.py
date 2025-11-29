"""Tests for FTMS Indoor Bike Data parsing."""

import pytest

from terminalride.devices.ftms_parse import parse_indoor_bike_data


def test_parse_all_fields():
    """Test parsing FTMS frame with all optional fields present.
    
    This hex fixture contains: flags=0x001A, power=355W, speed≈8.33m/s (30.0 km/h), cadence=85rpm
    TODO(FTMS: confirm field scaling and bit positions)
    """
    # Example frame with all fields (little-endian)
    # Bit order: power(1), speed(3), cadence(4) = 0x001A
    # Speed uses 0.01 km/h units per FTMS common practice.
    # 30.00 km/h => raw = 3000 => 0x0BB8 (little-endian = B8 0B)
    frame = bytes([
        0x1A, 0x00,  # flags (bit 1,3,4 set = power, speed, cadence present)
        0x63, 0x01,  # power: 355W (355 = 0x0163)
        0xB8, 0x0B,  # speed: 3000 * 0.01 km/h = 30.00 km/h => 8.333 m/s
        0xAA, 0x00   # cadence: 170 (85rpm * 2) = 0x00AA
    ])
    
    result = parse_indoor_bike_data(frame)
    
    assert result.power_w == 355
    assert result.cadence_rpm == 85
    assert abs(result.speed_mps - (30.0/3.6)) < 0.01
    assert result.flags == 0x001A


def test_parse_missing_speed():
    """Test parsing FTMS frame with speed field missing."""
    # Frame with power and cadence only (speed bit not set in flags)
    frame = bytes([
        0x12, 0x00,  # flags (bit 1,4 set = power, cadence present)
        0xF4, 0x01,  # power: 500W (500 = 0x01F4)
        0xB4, 0x00   # cadence: 180 (90rpm * 2) = 0x00B4
    ])
    
    result = parse_indoor_bike_data(frame)
    
    assert result.power_w == 500
    assert result.cadence_rpm == 90
    assert result.speed_mps is None
    assert result.flags == 0x0012


def test_parse_invalid_length():
    """Test that invalid frame length raises ValueError."""
    # Frame too short
    frame = bytes([0x16])
    
    with pytest.raises(ValueError, match="Invalid frame length"):
        parse_indoor_bike_data(frame)
    
    # Frame with flags indicating fields but not enough data
    frame = bytes([0x16, 0x2A, 0x63])  # Says power present but incomplete
    
    with pytest.raises(ValueError, match="Invalid frame"):
        parse_indoor_bike_data(frame)
