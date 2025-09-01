"""Tests for ERG PI controller."""

import pytest
from terminalride.modes.erg import ErgController


class TestErgController:
    """Test ERG PI controller behavior."""
    
    def test_controller_bounds(self):
        """Test that controller respects power bounds [100, 400]W."""
        controller = ErgController(kp=1.0, ki=0.1, kd=0.0)
        
        # Test lower bound
        result = controller.update(target_power=50, current_power=200, dt=1.0)
        assert result >= 100, "Output should be clamped to minimum 100W"
        
        # Test upper bound  
        controller.reset()
        result = controller.update(target_power=500, current_power=200, dt=1.0)
        assert result <= 400, "Output should be clamped to maximum 400W"
    
    def test_rate_limiting(self):
        """Test rate limiting: ±10W per 5s = ±2W per 1s."""
        controller = ErgController(kp=100.0, ki=0.0, kd=0.0)  # High gain
        controller._last_output = 200  # Set initial output
        
        # Large step should be rate limited
        result = controller.update(target_power=300, current_power=200, dt=1.0)
        expected_max = 200 + 2  # +2W max per second
        assert result <= expected_max, f"Rate limit violated: {result} > {expected_max}"
        
        # Large negative step should be rate limited
        controller._last_output = 200
        result = controller.update(target_power=100, current_power=200, dt=1.0)
        expected_min = 200 - 2  # -2W max per second
        assert result >= expected_min, f"Rate limit violated: {result} < {expected_min}"
    
    def test_step_response(self):
        """Test controller step response converges to target."""
        controller = ErgController(kp=0.8, ki=0.2, kd=0.1)
        target = 250
        current = 200
        
        # Simulate 10 seconds of control loop
        outputs = []
        for i in range(10):
            output = controller.update(target_power=target, current_power=current, dt=1.0)
            outputs.append(output)
            # Simulate plant response (simple first-order)
            current = current + 0.3 * (output - current)
        
        # Should converge close to target
        final_error = abs(outputs[-1] - target)
        assert final_error < 20, f"Final error {final_error}W too large"
        
        # Should be stable (not oscillating wildly)
        last_3_outputs = outputs[-3:]
        output_variance = max(last_3_outputs) - min(last_3_outputs)
        assert output_variance < 30, f"Output variance {output_variance} indicates instability"
    
    def test_anti_windup(self):
        """Test integrator anti-windup when output saturated."""
        controller = ErgController(kp=0.5, ki=1.0, kd=0.0)  # High integral gain
        
        # Drive controller into saturation with large persistent error
        for _ in range(20):
            output = controller.update(target_power=500, current_power=200, dt=1.0)
            assert output <= 400, "Output should remain clamped"
        
        # Now give step in opposite direction - should respond quickly
        # If integrator wasn't limited, it would take forever to unwind
        response_time = 0
        for i in range(10):
            output = controller.update(target_power=150, current_power=200, dt=1.0)
            response_time += 1
            if output < 390:  # Started responding
                break
        
        assert response_time <= 6, "Anti-windup failed - integrator took too long to unwind"
    
    def test_reset(self):
        """Test controller reset clears internal state."""
        controller = ErgController(kp=1.0, ki=0.1, kd=0.1)
        
        # Build up some internal state
        controller.update(target_power=300, current_power=200, dt=1.0)
        controller.update(target_power=300, current_power=210, dt=1.0)
        
        # Reset and verify clean state
        controller.reset()
        
        # First output after reset should only be proportional response
        output = controller.update(target_power=250, current_power=200, dt=1.0)
        expected_p_only = 200 + 1.0 * (250 - 200)  # P term only
        assert abs(output - expected_p_only) <= 5, "Reset didn't clear internal state"