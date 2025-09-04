"""Tests for UI widgets."""

import pytest
from unittest.mock import MagicMock

from terminalride.ui.widgets import DistanceProgressBar
from terminalride.ui.views import AppState


class TestDistanceProgressBar:
    """Tests for the DistanceProgressBar widget."""

    def test_progress_calculation_basic(self):
        """Test basic progress calculations."""
        widget = DistanceProgressBar()
        
        # Test 500m into first km (50%)
        state = AppState()
        state.metrics = {"distance_m": 500.0}
        
        result = widget.render(state)
        assert "KM 1" in str(result)
        assert "50%" in str(result)
        assert "500 m" in str(result)

    def test_progress_calculation_multiple_km(self):
        """Test progress across multiple kilometers."""
        widget = DistanceProgressBar()
        
        # Test 2.3 km (300m into 3rd km = 30%)
        state = AppState()
        state.metrics = {"distance_m": 2300.0}
        
        result = widget.render(state)
        assert "KM 3" in str(result)
        assert "30%" in str(result)
        assert "300 m" in str(result)

    def test_progress_calculation_exact_km(self):
        """Test progress at exact kilometer boundaries."""
        widget = DistanceProgressBar()
        
        # Test exactly 2km (0% into 3rd km)
        state = AppState()
        state.metrics = {"distance_m": 2000.0}
        
        result = widget.render(state)
        assert "KM 3" in str(result)
        assert "0%" in str(result)
        assert "0 m" in str(result)

    def test_progress_calculation_zero_distance(self):
        """Test progress with zero distance."""
        widget = DistanceProgressBar()
        
        state = AppState()
        state.metrics = {"distance_m": 0.0}
        
        result = widget.render(state)
        assert "KM 1" in str(result)
        assert "0%" in str(result)
        assert "0 m" in str(result)

    def test_progress_calculation_no_distance(self):
        """Test progress with missing distance metric."""
        widget = DistanceProgressBar()
        
        state = AppState()
        state.metrics = {}
        
        result = widget.render(state)
        assert "KM 1" in str(result)
        assert "0%" in str(result)
        assert "0 m" in str(result)

    def test_progress_calculation_negative_distance(self):
        """Test progress with negative distance (edge case)."""
        widget = DistanceProgressBar()
        
        state = AppState()
        state.metrics = {"distance_m": -100.0}
        
        result = widget.render(state)
        assert "KM 1" in str(result)
        assert "0%" in str(result)
        assert "0 m" in str(result)

    def test_progress_bar_rendering(self):
        """Test that progress bar renders correctly."""
        widget = DistanceProgressBar()
        
        state = AppState()
        state.metrics = {"distance_m": 750.0}  # 75% through first km
        
        result = widget.render(state)
        result_str = str(result)
        
        # Should contain progress elements
        assert "KM 1" in result_str
        assert "75%" in result_str
        assert "750 m" in result_str
        
        # Should have visual progress bar representation
        # (The exact characters depend on Rich implementation)
        assert len(result_str) > 20  # Should be substantial content