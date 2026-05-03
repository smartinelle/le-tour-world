"""Base protocol interfaces for trainer and heart rate devices."""

from typing import Protocol, Callable, Optional, TypedDict, runtime_checkable, Dict, Any
from abc import abstractmethod


class BikeSample(TypedDict):
    """Sample data from indoor bike trainer.

    Attributes:
        ts: Timestamp (seconds since epoch)
        power_w: Instantaneous power in watts (None if not available)
        cadence_rpm: Instantaneous cadence in RPM (None if not available)
        speed_mps: Instantaneous speed in m/s (None if not available)
    """

    ts: float
    power_w: Optional[int]
    cadence_rpm: Optional[int]
    speed_mps: Optional[float]


class HrSample(TypedDict):
    """Heart rate sample data.

    Attributes:
        ts: Timestamp (seconds since epoch)
        hr_bpm: Heart rate in beats per minute (None if not available)
    """

    ts: float
    hr_bpm: Optional[int]


@runtime_checkable
class TrainerDevice(Protocol):
    """Protocol for indoor trainer devices (FTMS, ANT+ FE-C, etc.).

    Defines the interface that all trainer devices must implement,
    allowing different transport layers (BLE, ANT+) behind same API.
    """

    @abstractmethod
    async def scan_and_connect(self, timeout_s: float = 10.0) -> None:
        """Scan for and connect to trainer device.

        Args:
            timeout_s: Maximum time to spend scanning/connecting

        Raises:
            DeviceNotFoundError: If no compatible trainer found
            ConnectionError: If connection fails
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from trainer device."""
        ...

    @abstractmethod
    async def subscribe_bike_data(self, callback: Callable[[BikeSample], None]) -> None:
        """Subscribe to live bike data notifications.

        Args:
            callback: Function called with each new BikeSample
        """
        ...

    @abstractmethod
    async def request_control(self) -> None:
        """Request control of trainer for ERG/SIM modes.

        Raises:
            ControlNotGrantedError: If trainer rejects control request
        """
        ...

    @abstractmethod
    async def start_session(self) -> None:
        """Start training session on trainer."""
        ...

    @abstractmethod
    async def stop_session(self) -> None:
        """Stop training session on trainer."""
        ...

    @abstractmethod
    async def set_target_power(self, watts: int) -> None:
        """Set target power for ERG mode.

        Args:
            watts: Target power in watts [100-400]

        Raises:
            ControlNotAvailableError: If control not granted
            ValueError: If watts outside valid range
        """
        ...

    @abstractmethod
    async def set_simulation_params(
        self,
        grade_pct: float,
        wind_speed_mps: float = 0.0,
        rolling_resistance: float = 0.0045,
    ) -> None:
        """Set simulation parameters for SIM mode.

        Args:
            grade_pct: Road grade as percentage (positive = uphill)
            wind_speed_mps: Wind speed in m/s (positive = headwind)
            rolling_resistance: Rolling resistance coefficient

        Raises:
            ControlNotAvailableError: If control not granted
        """
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True if device is connected."""
        ...

    @property
    @abstractmethod
    def has_control(self) -> bool:
        """True if we have control of the trainer."""
        ...

    @property
    @abstractmethod
    def device_info(self) -> Dict[str, Any]:
        """Device information (model, firmware, etc.)."""
        ...


@runtime_checkable
class HrDevice(Protocol):
    """Protocol for heart rate monitoring devices."""

    @abstractmethod
    async def scan_and_connect(self, timeout_s: float = 10.0) -> None:
        """Scan for and connect to heart rate device.

        Args:
            timeout_s: Maximum time to spend scanning/connecting

        Raises:
            DeviceNotFoundError: If no HR device found
            ConnectionError: If connection fails
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from heart rate device."""
        ...

    @abstractmethod
    async def subscribe_hr_data(self, callback: Callable[[HrSample], None]) -> None:
        """Subscribe to heart rate notifications.

        Args:
            callback: Function called with each new HrSample
        """
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True if device is connected."""
        ...

    @property
    @abstractmethod
    def device_info(self) -> Dict[str, Any]:
        """Device information (model, battery, etc.)."""
        ...


# Custom exceptions for device protocols
class DeviceError(Exception):
    """Base exception for device-related errors."""

    pass


class DeviceNotFoundError(DeviceError):
    """Raised when no compatible device found during scan."""

    pass


class ConnectionError(DeviceError):
    """Raised when device connection fails."""

    pass


class ControlNotGrantedError(DeviceError):
    """Raised when trainer rejects control request."""

    pass


class ControlNotAvailableError(DeviceError):
    """Raised when attempting control operations without control."""

    pass
