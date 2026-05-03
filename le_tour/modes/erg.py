"""ERG mode PI controller with anti-windup and rate limiting."""

from typing import Optional


class ErgController:
    """PI controller for ERG mode with bounds, rate limiting, and anti-windup.

    Implements a discrete-time PI controller with:
    - Output bounds: [100, 400] watts
    - Rate limiting: ±10W per 5s (±2W per second)
    - Anti-windup: integrator clamping when output saturated
    - 1 Hz sampling rate recommended

    Args:
        kp: Proportional gain
        ki: Integral gain (per second)
        kd: Derivative gain (per second) - typically 0 for ERG mode
    """

    MIN_POWER = 100  # Minimum output power (W)
    MAX_POWER = 400  # Maximum output power (W)
    RATE_LIMIT = 2.0  # Maximum rate change per second (W/s)

    def __init__(self, kp: float = 0.8, ki: float = 0.2, kd: float = 0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        # Internal state
        self._integral = 0.0
        self._last_error: Optional[float] = None
        self._last_output: Optional[float] = None

    def update(self, target_power: int, current_power: int, dt: float) -> int:
        """Update controller and compute new target power.

        Args:
            target_power: Desired power setpoint (W)
            current_power: Current measured power (W)
            dt: Time step since last update (seconds)

        Returns:
            New target power command clamped to bounds (W)
        """
        error = target_power - current_power

        # Proportional term
        p_term = self.kp * error

        # Integral term with anti-windup
        self._integral += error * dt
        i_term = self.ki * self._integral

        # Derivative term
        d_term = 0.0
        if self._last_error is not None:
            d_term = self.kd * (error - self._last_error) / dt

        # Compute raw output
        raw_output = current_power + p_term + i_term + d_term

        # Apply rate limiting
        if self._last_output is not None:
            max_change = self.RATE_LIMIT * dt
            rate_limited_output = max(
                min(raw_output, self._last_output + max_change),
                self._last_output - max_change,
            )
        else:
            rate_limited_output = raw_output

        # Apply power bounds
        bounded_output = max(self.MIN_POWER, min(self.MAX_POWER, rate_limited_output))

        # Anti-windup: clamp integrator when output saturated
        if bounded_output != raw_output and abs(self.ki) > 1e-6:
            # Output was clamped, back-calculate what integrator should be
            allowed_change = bounded_output - current_power
            allowed_i_term = allowed_change - p_term - d_term
            allowed_integral = allowed_i_term / self.ki

            # Clamp integrator to allowed value
            self._integral = allowed_integral

        # Save state for next iteration
        self._last_error = error
        self._last_output = bounded_output

        return int(round(bounded_output))

    def reset(self) -> None:
        """Reset controller internal state.

        Call when starting new session or switching modes.
        """
        self._integral = 0.0
        self._last_error = None
        self._last_output = None
