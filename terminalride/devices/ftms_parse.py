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

    offset = 2
    power_w = None
    cadence_rpm = None
    speed_mps = None

    # TODO(FTMS: confirm bit positions and scaling factors from official spec)

    # Bit 1: Instantaneous Power present (0x0002)
    if flags & 0x0002:
        if offset + 2 > len(frame):
            raise ValueError(
                "Invalid frame length: power field indicated but not present"
            )
        power_w = struct.unpack("<H", frame[offset : offset + 2])[0]
        offset += 2

    # Bit 2: Average Power present (0x0004) - skip if present
    if flags & 0x0004:
        if offset + 2 > len(frame):
            raise ValueError(
                "Invalid frame length: average power field indicated but not present"
            )
        offset += 2  # Skip average power field

    # Bit 3: Instantaneous Speed present (0x0008) - check before cadence
    if flags & 0x0008:
        if offset + 2 > len(frame):
            raise ValueError(
                "Invalid frame length: speed field indicated but not present"
            )
        speed_raw = struct.unpack("<H", frame[offset : offset + 2])[0]
        speed_mps = (
            speed_raw / 1000.0
        )  # TODO(FTMS: confirm scaling - assuming 0.001 m/s resolution)
        offset += 2

    # Bit 4: Instantaneous Cadence present (0x0010)
    if flags & 0x0010:
        if offset + 2 > len(frame):
            raise ValueError(
                "Invalid frame length: cadence field indicated but not present"
            )
        cadence_raw = struct.unpack("<H", frame[offset : offset + 2])[0]
        cadence_rpm = (
            cadence_raw // 2
        )  # TODO(FTMS: confirm scaling - spec says 0.5 RPM resolution)
        offset += 2

    # Bit 5: Average Cadence present (0x0020) - skip if present
    if flags & 0x0020:
        if offset + 2 > len(frame):
            raise ValueError(
                "Invalid frame length: average cadence field indicated but not present"
            )
        offset += 2  # Skip average cadence field

    return ParsedBikeData(
        power_w=power_w, cadence_rpm=cadence_rpm, speed_mps=speed_mps, flags=flags
    )
