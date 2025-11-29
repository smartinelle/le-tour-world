"""BLE Heart Rate Measurement characteristic parser.

Parses data from the standard Bluetooth Heart Rate Profile (0x180D).
This format is used by Wahoo TICKR, Garmin HRM, Polar, and most other
BLE heart rate monitors.

Reference:
    Bluetooth SIG Heart Rate Service Specification
    https://www.bluetooth.com/specifications/specs/heart-rate-service-1-0/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ParsedHrData:
    """Parsed heart rate measurement data.

    Attributes:
        hr_bpm: Heart rate in beats per minute.
        sensor_contact_supported: True if sensor supports contact detection.
        sensor_contact_detected: True if sensor has skin contact (None if not supported).
        energy_expended_kj: Cumulative energy in kilojoules (None if not present).
        rr_intervals_ms: List of RR intervals in milliseconds (empty if not present).
            RR intervals are the time between consecutive heartbeats.
        flags: Raw flags byte for debugging.
    """

    hr_bpm: int
    sensor_contact_supported: bool
    sensor_contact_detected: Optional[bool]
    energy_expended_kj: Optional[int]
    rr_intervals_ms: List[int]
    flags: int


def parse_heart_rate_measurement(data: bytes) -> ParsedHrData:
    """Parse BLE Heart Rate Measurement characteristic data.

    The Heart Rate Measurement characteristic (UUID 0x2A37) has the format:
        - Flags (1 byte)
        - Heart Rate Value (1 or 2 bytes depending on flags)
        - Energy Expended (2 bytes, optional)
        - RR-Intervals (2 bytes each, optional, variable count)

    Flags byte bits:
        - Bit 0: Heart Rate Value Format (0 = UINT8, 1 = UINT16)
        - Bit 1-2: Sensor Contact Status
        - Bit 3: Energy Expended Present
        - Bit 4: RR-Interval Present
        - Bits 5-7: Reserved

    Args:
        data: Raw bytes from BLE notification.

    Returns:
        ParsedHrData with heart rate and optional fields.

    Raises:
        ValueError: If data is too short or malformed.

    Example:
        >>> data = bytes([0x00, 72])  # Flags=0, HR=72 BPM
        >>> parsed = parse_heart_rate_measurement(data)
        >>> parsed.hr_bpm
        72
    """
    if len(data) < 2:
        raise ValueError(f"HR data too short: {len(data)} bytes, minimum 2")

    flags = data[0]
    offset = 1

    # Bit 0: Heart Rate Value Format
    hr_format_16bit = bool(flags & 0x01)

    # Bit 1-2: Sensor Contact Status
    # 00 or 01: Not supported
    # 10: Supported, contact not detected
    # 11: Supported, contact detected
    sensor_contact_bits = (flags >> 1) & 0x03
    sensor_contact_supported = sensor_contact_bits >= 2
    sensor_contact_detected: Optional[bool] = None
    if sensor_contact_supported:
        sensor_contact_detected = sensor_contact_bits == 3

    # Bit 3: Energy Expended Present
    energy_present = bool(flags & 0x08)

    # Bit 4: RR-Interval Present
    rr_present = bool(flags & 0x10)

    # Parse Heart Rate Value
    if hr_format_16bit:
        if len(data) < offset + 2:
            raise ValueError("HR data too short for 16-bit HR value")
        hr_bpm = int.from_bytes(data[offset : offset + 2], byteorder="little")
        offset += 2
    else:
        hr_bpm = data[offset]
        offset += 1

    # Parse Energy Expended (if present)
    energy_expended_kj: Optional[int] = None
    if energy_present:
        if len(data) < offset + 2:
            raise ValueError("HR data too short for energy expended field")
        energy_expended_kj = int.from_bytes(data[offset : offset + 2], byteorder="little")
        offset += 2

    # Parse RR-Intervals (if present)
    # Each RR interval is 2 bytes, in 1/1024 second units
    rr_intervals_ms: List[int] = []
    if rr_present:
        while offset + 2 <= len(data):
            rr_raw = int.from_bytes(data[offset : offset + 2], byteorder="little")
            # Convert from 1/1024 seconds to milliseconds
            rr_ms = int(rr_raw * 1000 / 1024)
            rr_intervals_ms.append(rr_ms)
            offset += 2

    return ParsedHrData(
        hr_bpm=hr_bpm,
        sensor_contact_supported=sensor_contact_supported,
        sensor_contact_detected=sensor_contact_detected,
        energy_expended_kj=energy_expended_kj,
        rr_intervals_ms=rr_intervals_ms,
        flags=flags,
    )

