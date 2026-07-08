"""Tests for SIM mode physics solver."""

import math
from le_tour.modes.sim import RiderDynamics, SimConfig, SimPhysics


class TestSimPhysics:
    """Test SIM mode power-to-speed physics."""

    def test_flat_road_baseline(self):
        """Test 250W @ 0% grade with standard parameters gives expected speed range."""
        config = SimConfig(
            mass_kg=100.0,  # rider + bike
            cda_m2=0.33,  # drag coefficient * frontal area
            crr=0.0045,  # rolling resistance
            rho_kg_m3=1.2,  # air density
        )
        physics = SimPhysics(config)

        # Solve for speed at 250W on flat road
        speed_mps = physics.solve_speed(power_w=250, grade_pct=0.0)

        # Should be in expected range [9.0, 11.5] m/s per spec
        assert (
            9.0 <= speed_mps <= 11.5
        ), f"Speed {speed_mps:.2f} m/s outside expected range"

        # Sanity check - should be reasonable cycling speed
        speed_kph = speed_mps * 3.6
        assert 30 <= speed_kph <= 45, f"Speed {speed_kph:.1f} km/h unrealistic for 250W"

    def test_speed_increases_with_power(self):
        """Test that higher power gives higher speed."""
        config = SimConfig(mass_kg=75.0, cda_m2=0.3, crr=0.004, rho_kg_m3=1.2)
        physics = SimPhysics(config)

        speeds = []
        for power in [150, 200, 250, 300, 350]:
            speed = physics.solve_speed(power_w=power, grade_pct=0.0)
            speeds.append(speed)

        # Speeds should be monotonically increasing
        for i in range(1, len(speeds)):
            assert (
                speeds[i] > speeds[i - 1]
            ), f"Speed didn't increase: {speeds[i-1]:.2f} -> {speeds[i]:.2f}"

    def test_speed_decreases_with_grade(self):
        """Test that positive grade reduces speed for same power."""
        config = SimConfig(mass_kg=80.0, cda_m2=0.32, crr=0.0045, rho_kg_m3=1.2)
        physics = SimPhysics(config)

        power = 275
        flat_speed = physics.solve_speed(power_w=power, grade_pct=0.0)
        uphill_speed = physics.solve_speed(power_w=power, grade_pct=5.0)

        assert (
            uphill_speed < flat_speed
        ), f"Uphill speed {uphill_speed:.2f} should be less than flat {flat_speed:.2f}"

        # Should be significantly slower uphill
        speed_reduction = flat_speed - uphill_speed
        assert (
            speed_reduction > 1.0
        ), f"Speed reduction {speed_reduction:.2f} m/s too small for 5% grade"

    def test_downhill_speed_increase(self):
        """Test that negative grade increases speed."""
        config = SimConfig(mass_kg=70.0, cda_m2=0.28, crr=0.004, rho_kg_m3=1.2)
        physics = SimPhysics(config)

        power = 200
        flat_speed = physics.solve_speed(power_w=power, grade_pct=0.0)
        downhill_speed = physics.solve_speed(power_w=power, grade_pct=-3.0)

        assert (
            downhill_speed > flat_speed
        ), f"Downhill speed {downhill_speed:.2f} should be greater than flat {flat_speed:.2f}"

    def test_speed_bounds_enforced(self):
        """Test that speed is clamped to [0, 20] m/s range."""
        config = SimConfig(mass_kg=70.0, cda_m2=0.3, crr=0.004, rho_kg_m3=1.2)
        physics = SimPhysics(config)

        # Very low power should not give negative speed
        low_speed = physics.solve_speed(
            power_w=50, grade_pct=10.0
        )  # Low power, steep uphill
        assert low_speed >= 0.0, f"Speed {low_speed} should not be negative"

        # Very high power should be clamped to max speed
        high_speed = physics.solve_speed(
            power_w=1000, grade_pct=-5.0
        )  # High power, downhill
        assert high_speed <= 20.0, f"Speed {high_speed} should not exceed 20 m/s"

    def test_mass_effect(self):
        """Test that heavier rider goes slower uphill, similar speed on flat."""
        light_config = SimConfig(mass_kg=60.0, cda_m2=0.28, crr=0.004, rho_kg_m3=1.2)
        heavy_config = SimConfig(mass_kg=90.0, cda_m2=0.28, crr=0.004, rho_kg_m3=1.2)

        light_physics = SimPhysics(light_config)
        heavy_physics = SimPhysics(heavy_config)

        power = 250

        # On flat road, mass effect should be minimal (aerodynamics dominant)
        light_flat = light_physics.solve_speed(power_w=power, grade_pct=0.0)
        heavy_flat = heavy_physics.solve_speed(power_w=power, grade_pct=0.0)
        flat_diff = light_flat - heavy_flat
        assert (
            flat_diff < 1.0
        ), f"Mass effect on flat road too large: {flat_diff:.2f} m/s"

        # Uphill, mass effect should be significant
        light_uphill = light_physics.solve_speed(power_w=power, grade_pct=8.0)
        heavy_uphill = heavy_physics.solve_speed(power_w=power, grade_pct=8.0)
        uphill_diff = light_uphill - heavy_uphill
        assert uphill_diff > 0.5, f"Mass effect uphill too small: {uphill_diff:.2f} m/s"

    def test_physics_equation_balance(self):
        """Test that solved speed satisfies the power balance equation."""
        config = SimConfig(mass_kg=75.0, cda_m2=0.32, crr=0.0045, rho_kg_m3=1.2)
        physics = SimPhysics(config)

        power = 300
        grade = 4.0
        speed = physics.solve_speed(power_w=power, grade_pct=grade)

        # Manually calculate power components at solved speed
        # Use same angle conversion as in physics solver
        grade_rad = math.atan(grade / 100.0)

        # Aerodynamic drag: 0.5 * rho * CdA * v^3
        p_aero = 0.5 * config.rho_kg_m3 * config.cda_m2 * speed**3

        # Rolling resistance: m * g * Crr * v
        p_rolling = config.mass_kg * 9.81 * config.crr * speed

        # Gravity: m * g * sin(theta) * v
        p_gravity = config.mass_kg * 9.81 * math.sin(grade_rad) * speed

        # Account for drivetrain loss (5W as in spec) - this was already subtracted in solver
        total_calculated = p_aero + p_rolling + p_gravity

        # Should balance within solver tolerance (compare with available power after losses)
        available_power = power - 5.0  # Subtract drivetrain loss
        power_error = abs(total_calculated - available_power)
        assert power_error < 5.0, f"Power balance error {power_error:.2f}W too large"


class TestRiderDynamics:
    """Inertia-based virtual rider integration (the app-side speed authority)."""

    def _dynamics(self) -> RiderDynamics:
        return RiderDynamics(SimConfig())

    def _ride(self, dynamics, power_w, grade_pct, seconds):
        speeds = []
        for _ in range(seconds):
            step = dynamics.step(power_w=power_w, grade_pct=grade_pct, dt_s=1.0)
            speeds.append(step.speed_mps)
        return speeds

    def test_converges_to_steady_state_solver(self):
        """Dynamics settle onto the same equilibrium the solver computes."""
        physics = SimPhysics(SimConfig())
        dynamics = self._dynamics()

        for power, grade in [(150, 0.0), (250, 0.0), (200, 5.6), (120, -3.0)]:
            dynamics.reset()
            speeds = self._ride(dynamics, power, grade, seconds=120)
            expected = physics.solve_speed(power_w=power, grade_pct=grade)
            assert abs(speeds[-1] - expected) < max(
                0.02 * expected, 0.05
            ), f"P={power} grade={grade}: {speeds[-1]:.2f} vs solver {expected:.2f}"

    def test_standing_start_builds_speed_gradually(self):
        """No teleport to cruising speed from a standstill."""
        speeds = self._ride(self._dynamics(), power_w=200, grade_pct=0.0, seconds=20)

        assert speeds[0] < 4.0
        assert speeds[0] < speeds[4] < speeds[19]

    def test_grade_step_sheds_speed_over_seconds(self):
        """Hitting a climb decays speed smoothly instead of stepping it."""
        dynamics = self._dynamics()
        self._ride(dynamics, power_w=200, grade_pct=0.0, seconds=90)
        flat_speed = dynamics.speed_mps

        climb_speeds = self._ride(dynamics, power_w=200, grade_pct=5.6, seconds=30)

        # First second sheds only a fraction of the total speed loss.
        assert flat_speed - climb_speeds[0] < 0.35 * (flat_speed - climb_speeds[-1])
        # And the decay is monotonic toward the climb equilibrium.
        assert all(a >= b for a, b in zip(climb_speeds, climb_speeds[1:]))

    def test_zero_power_uphill_stops_and_stays_stopped(self):
        """A stopped rider does not creep up a climb."""
        dynamics = self._dynamics()
        speeds = self._ride(dynamics, power_w=0, grade_pct=8.0, seconds=30)

        assert speeds[-1] == 0.0

    def test_coasting_downhill_accelerates_toward_terminal_velocity(self):
        """Gravity is a propulsive force on descents."""
        dynamics = self._dynamics()
        speeds = self._ride(dynamics, power_w=0, grade_pct=-8.0, seconds=180)

        assert speeds[0] > 0.0
        assert speeds[-1] > 14.0
        assert speeds[-1] <= RiderDynamics.MAX_SPEED
        # Terminal: acceleration has flattened out.
        assert speeds[-1] - speeds[-10] < 0.05

    def test_sample_gaps_are_clamped(self):
        """One late BLE sample cannot teleport the rider."""
        dynamics = self._dynamics()
        self._ride(dynamics, power_w=200, grade_pct=0.0, seconds=30)

        step = dynamics.step(power_w=200, grade_pct=0.0, dt_s=60.0)

        assert step.distance_m <= dynamics.speed_mps * RiderDynamics.MAX_STEP_S + 1.0

    def test_distance_integrates_speed(self):
        """Reported distance matches the speed trace."""
        dynamics = self._dynamics()
        total = 0.0
        speeds = []
        for _ in range(60):
            step = dynamics.step(power_w=250, grade_pct=0.0, dt_s=1.0)
            total += step.distance_m
            speeds.append(step.speed_mps)

        # Distance must sit between lower/upper Riemann sums of the trace.
        assert total > 0.0
        assert total <= sum(speeds) + 1.0
