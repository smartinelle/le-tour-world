"""SIM mode physics: power-to-speed solver and virtual rider dynamics."""

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


@dataclass(frozen=True)
class DynamicsStep:
    """Result of advancing the virtual rider by one sample interval."""

    speed_mps: float
    distance_m: float


class RiderDynamics:
    """Integrate virtual rider speed from measured power with inertia.

    `SimPhysics.solve_speed` answers "what speed does this power sustain?" —
    the steady state. Riding feel lives in the transient: crossing onto a
    climb sheds speed over seconds as kinetic energy drains, not instantly.
    This integrates dv/dt = (F_propulsion - F_gravity - F_rolling - F_aero)/m
    between trainer samples, so app-computed speed (the virtual-world
    authority) responds to terrain the way a bike does.
    """

    GRAVITY = SimPhysics.GRAVITY
    DRIVETRAIN_LOSS = SimPhysics.DRIVETRAIN_LOSS
    MAX_SPEED = 30.0  # m/s; descent terminal velocities exceed the solver's 20
    MAX_STEP_S = 3.0  # clamp BLE gaps so one late sample cannot teleport
    SUBSTEP_S = 0.1
    # Below this speed, propulsive force is computed at this speed so P/v is
    # bounded; caps standing-start force at a realistic pedal push.
    MIN_PROPULSION_SPEED = 0.5

    def __init__(self, config: SimConfig):
        self.config = config
        self.speed_mps = 0.0

    def reset(self, speed_mps: float = 0.0) -> None:
        """Reset rider speed (session start, resume from pause)."""
        self.speed_mps = max(0.0, min(self.MAX_SPEED, speed_mps))

    def step(self, power_w: float, grade_pct: float, dt_s: float) -> DynamicsStep:
        """Advance the rider by one sample interval.

        Args:
            power_w: Rider power for the interval (W); 0 while coasting.
            grade_pct: Road grade over the interval (positive = uphill).
            dt_s: Time since the previous sample.

        Returns:
            New speed and the distance covered during the interval.
        """
        available_power = max(0.0, float(power_w) - self.DRIVETRAIN_LOSS)
        grade_rad = math.atan(float(grade_pct) / 100.0)
        weight_n = self.config.mass_kg * self.GRAVITY
        f_gravity = weight_n * math.sin(grade_rad)
        f_rolling = weight_n * self.config.crr * math.cos(grade_rad)

        remaining_s = max(0.0, min(float(dt_s), self.MAX_STEP_S))
        distance_m = 0.0
        speed = self.speed_mps
        while remaining_s > 0.0:
            substep_s = min(self.SUBSTEP_S, remaining_s)
            remaining_s -= substep_s

            f_propulsion = available_power / max(speed, self.MIN_PROPULSION_SPEED)
            f_aero = 0.5 * self.config.rho_kg_m3 * self.config.cda_m2 * speed**2
            # Rolling resistance opposes motion; it cannot push a stopped
            # rider backwards.
            f_resist = f_gravity + f_aero + (f_rolling if speed > 0.0 else 0.0)
            acceleration = (f_propulsion - f_resist) / self.config.mass_kg

            speed = max(0.0, min(self.MAX_SPEED, speed + acceleration * substep_s))
            distance_m += speed * substep_s

        self.speed_mps = speed
        return DynamicsStep(speed_mps=speed, distance_m=distance_m)
