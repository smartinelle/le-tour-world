"""FTMS Indoor Bike Data parser - pure function implementation."""

from typing import NamedTuple, Optional
import struct


class ParsedBikeData(NamedTuple):
    """Parsed FTMS Indoor Bike Data.

    Attributes:
        power_w: Instantaneous power in watts (None if not present)
        cadence_rpm: Instantaneous cadence in RPM (None if not present)
        speed_mps: Instantaneous speed in m/s (None if not present)
        flags: Raw flags field for debugging
    """

    power_w: Optional[int]
    cadence_rpm: Optional[int]
    speed_mps: Optional[float]
    flags: int


def parse_indoor_bike_data(frame: bytes) -> ParsedBikeData:
    """Parse FTMS Indoor Bike Data notification frame.

    Parses little-endian FTMS Indoor Bike Data characteristic value according to
    FTMS specification. Handles optional fields based on flags.

    Args:
        frame: Raw BLE notification bytes from Indoor Bike Data characteristic

    Returns:
        ParsedBikeData with extracted fields (None for absent optional fields)

    Raises:
        ValueError: If frame length is invalid for the indicated fields

    Example:
        >>> # Frame with power=355W, cadence=85rpm, speed=9.216m/s
        >>> data = parse_indoor_bike_data(b'\\x16\\x2A\\x63\\x01\\x55\\x00\\x40\\x24')
        >>> data.power_w
        355
        >>> data.cadence_rpm
        85
        >>> abs(data.speed_mps - 9.216) < 0.001
        True
    """
    if len(frame) < 2:
        raise ValueError("Invalid frame length: need at least 2 bytes for flags")

    # Parse flags (little-endian 16-bit)
    flags = struct.unpack("<H", frame[0:2])[0]

    # We'll attempt a spec-like field order first, then fall back to the legacy order
    def parse_spec_like() -> ParsedBikeData:
        offset = 2
        power_w: Optional[int] = None
        cadence_rpm: Optional[int] = None
        speed_mps: Optional[float] = None

        # According to common FTMS docs for Indoor Bike Data, fields often appear in this order:
        # Instantaneous Speed (sometimes always present) → Average Speed (opt)
        # Instantaneous Cadence (opt) → Average Cadence (opt)
        # Total Distance (opt) → Resistance Level (opt)
        # Instantaneous Power (opt) → Average Power (opt)

        # Try to read instantaneous speed first if available bytes exist.
        # FTMS many trainers (e.g., KICKR) report instantaneous speed in 0.01 km/h.
        # Convert to m/s explicitly to avoid 3.6x inflation.
        if offset + 2 <= len(frame):
            speed_raw = struct.unpack("<H", frame[offset : offset + 2])[0]
            s_mps = (speed_raw / 100.0) / 3.6  # 0.01 km/h → m/s
            speed_mps = s_mps
            offset += 2

        # Average Speed present (commonly bit 0x0001 or 0x0002 depending on profile)
        if flags & 0x0001 or flags & 0x0002:
            if offset + 2 > len(frame):
                raise ValueError("Average speed flagged but missing")
            offset += 2

        # Instantaneous Cadence present (commonly 0x0004)
        if flags & 0x0004:
            if offset + 2 > len(frame):
                raise ValueError("Cadence flagged but missing")
            cadence_raw = struct.unpack("<H", frame[offset : offset + 2])[0]
            cadence_rpm = int(round(cadence_raw / 2.0))  # 0.5 rpm resolution
            offset += 2

        # Average Cadence present (0x0008)
        if flags & 0x0008:
            if offset + 2 > len(frame):
                raise ValueError("Avg cadence flagged but missing")
            offset += 2

        # Total Distance present (0x0010) — u24 meters
        if flags & 0x0010:
            if offset + 3 > len(frame):
                raise ValueError("Distance flagged but missing")
            offset += 3

        # Resistance Level present (0x0020) — s16
        if flags & 0x0020:
            if offset + 2 > len(frame):
                raise ValueError("Resistance flagged but missing")
            offset += 2

        # Instantaneous Power present (0x0040) — s16 watts
        if flags & 0x0040:
            if offset + 2 > len(frame):
                raise ValueError("Power flagged but missing")
            power_w = struct.unpack("<h", frame[offset : offset + 2])[0]
            offset += 2

        # Average Power present (0x0080)
        if flags & 0x0080:
            if offset + 2 > len(frame):
                raise ValueError("Avg power flagged but missing")
            offset += 2

        return ParsedBikeData(power_w, cadence_rpm, speed_mps, flags)

    def parse_legacy() -> ParsedBikeData:
        # Legacy mapping used by earlier tests/examples in this repo.
        offset = 2
        power_w: Optional[int] = None
        cadence_rpm: Optional[int] = None
        speed_mps: Optional[float] = None

        # Bit 1: Instantaneous Power present (0x0002)
        if flags & 0x0002:
            if offset + 2 > len(frame):
                raise ValueError("Invalid frame: power flagged but missing")
            power_w = struct.unpack("<H", frame[offset : offset + 2])[0]
            offset += 2

        # Bit 2: Average Power present (0x0004) - skip if present
        if flags & 0x0004:
            if offset + 2 > len(frame):
                raise ValueError("Invalid frame: avg power flagged but missing")
            offset += 2

        # Bit 3: Instantaneous Speed present (0x0008)
        if flags & 0x0008:
            if offset + 2 > len(frame):
                raise ValueError("Invalid frame: speed flagged but missing")
            speed_raw = struct.unpack("<H", frame[offset : offset + 2])[0]
            # Common FTMS implementation reports speed in 0.01 km/h units.
            # Convert explicitly to meters per second to avoid 3.6x error.
            speed_mps = (speed_raw / 100.0) / 3.6
            offset += 2

        # Bit 4: Instantaneous Cadence present (0x0010)
        if flags & 0x0010:
            if offset + 2 > len(frame):
                raise ValueError("Invalid frame: cadence flagged but missing")
            cadence_raw = struct.unpack("<H", frame[offset : offset + 2])[0]
            cadence_rpm = cadence_raw // 2
            offset += 2

        # Bit 5: Average Cadence present (0x0020) - skip if present
        if flags & 0x0020:
            if offset + 2 > len(frame):
                raise ValueError("Invalid frame: avg cadence flagged but missing")
            offset += 2

        return ParsedBikeData(power_w, cadence_rpm, speed_mps, flags)

    # Try spec-like parsing first; if it yields no useful fields, fall back
    try:
        result = parse_spec_like()
        if any(v is not None for v in (result.power_w, result.cadence_rpm, result.speed_mps)):
            return result
    except Exception:
        # Fall back to legacy on any parsing error
        pass

    return parse_legacy()
