"""SIM mode physics solver for power-to-speed calculation."""

import math
from dataclasses import dataclass


@dataclass
class SimConfig:
    """Configuration for SIM mode physics.

    Attributes:
        mass_kg: Total mass of rider + bike (kg)
        cda_m2: Aerodynamic drag coefficient × frontal area (m²)
        crr: Rolling resistance coefficient (dimensionless)
        rho_kg_m3: Air density (kg/m³)
    """

    mass_kg: float = 75.0  # Default rider + bike mass
    cda_m2: float = 0.33  # Default aerodynamic drag
    crr: float = 0.0045  # Default rolling resistance
    rho_kg_m3: float = 1.2  # Standard air density at sea level


class SimPhysics:
    """Physics solver for SIM mode power-to-speed calculation.

    Solves the power balance equation using Newton's method:
    P = 0.5 * ρ * CdA * v³ + m * g * Crr * v + m * g * sin(θ) * v + P₀

    Where:
    - P: total power (W)
    - ρ: air density (kg/m³)
    - CdA: drag coefficient × frontal area (m²)
    - v: speed (m/s)
    - m: mass (kg)
    - g: gravitational acceleration (9.81 m/s²)
    - Crr: rolling resistance coefficient
    - θ: grade angle (radians)
    - P₀: drivetrain losses (~5W)
    """

    GRAVITY = 9.81  # m/s²
    DRIVETRAIN_LOSS = 5.0  # W
    MIN_SPEED = 0.0  # m/s
    MAX_SPEED = 20.0  # m/s

    def __init__(self, config: SimConfig):
        self.config = config

    def solve_speed(self, power_w: float, grade_pct: float) -> float:
        """Solve for speed given power and grade using Newton's method.

        Args:
            power_w: Available power from rider (W)
            grade_pct: Road grade as percentage (positive = uphill)

        Returns:
            Speed in m/s, clamped to [0, 20] range
        """
        # Convert grade percentage to radians
        grade_rad = math.atan(grade_pct / 100.0)

        # Available power after drivetrain losses
        available_power = max(0, power_w - self.DRIVETRAIN_LOSS)

        # Handle zero/negative power case
        if available_power <= 0:
            return self.MIN_SPEED

        # Newton's method solver
        speed = self._newton_solve(available_power, grade_rad)

        # Clamp to physical bounds
        return max(self.MIN_SPEED, min(self.MAX_SPEED, speed))

    def _newton_solve(
        self,
        power_w: float,
        grade_rad: float,
        initial_guess: float = 10.0,
        tolerance: float = 0.01,
        max_iterations: int = 50,
    ) -> float:
        """Solve power equation using Newton's method.

        Solves: f(v) = P_required(v) - P_available = 0
        Where: P_required(v) = 0.5*ρ*CdA*v³ + m*g*Crr*v + m*g*sin(θ)*v
        """
        speed = initial_guess

        for _ in range(max_iterations):
            # Calculate required power at current speed
            p_aero = 0.5 * self.config.rho_kg_m3 * self.config.cda_m2 * speed**3
            p_rolling = self.config.mass_kg * self.GRAVITY * self.config.crr * speed
            p_gravity = self.config.mass_kg * self.GRAVITY * math.sin(grade_rad) * speed

            p_required = p_aero + p_rolling + p_gravity

            # Function value: f(v) = P_required - P_available
            f_v = p_required - power_w

            # Check convergence
            if abs(f_v) < tolerance:
                return speed

            # Calculate derivative: f'(v) = dP_required/dv
            df_dv = (
                1.5 * self.config.rho_kg_m3 * self.config.cda_m2 * speed**2
                + self.config.mass_kg * self.GRAVITY * self.config.crr
                + self.config.mass_kg * self.GRAVITY * math.sin(grade_rad)
            )

            # Avoid division by zero
            if abs(df_dv) < 1e-10:
                break

            # Newton step: v_new = v - f(v)/f'(v)
            speed_new = speed - f_v / df_dv

            # Ensure speed stays positive for stability
            speed = max(0.1, speed_new)

        # If Newton's method doesn't converge, fall back to bisection
        return self._bisection_solve(power_w, grade_rad)

    def _bisection_solve(
        self, power_w: float, grade_rad: float, max_iterations: int = 50
    ) -> float:
        """Fallback bisection method solver."""
        low, high = 0.1, 25.0

        for _ in range(max_iterations):
            mid = (low + high) / 2

            p_aero = 0.5 * self.config.rho_kg_m3 * self.config.cda_m2 * mid**3
            p_rolling = self.config.mass_kg * self.GRAVITY * self.config.crr * mid
            p_gravity = self.config.mass_kg * self.GRAVITY * math.sin(grade_rad) * mid

            p_required = p_aero + p_rolling + p_gravity

            if abs(p_required - power_w) < 1.0:  # 1W tolerance for bisection
                return mid

            if p_required < power_w:
                low = mid
            else:
                high = mid

        return (low + high) / 2
