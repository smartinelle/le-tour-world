"""Tests for UI views."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from terminalride.ui.views import AppState, SummaryView, ViewState
from terminalride.store.models import SessionModel, TrainingMode


class TestSummaryView:
    """Tests for the SummaryView."""

    def test_summary_view_renders_with_valid_session(self):
        """Test that SummaryView renders correctly with valid session data."""
        view = SummaryView()
        
        # Mock state with session ID
        state = AppState()
        state.last_session_id = "test-session-123"
        
        # Mock session data
        mock_session = SessionModel(
            session_id="test-session-123",
            mode=TrainingMode.ERG,
            start_time=datetime(2023, 1, 1, 10, 0, 0),
            end_time=datetime(2023, 1, 1, 10, 30, 0),
            duration_s=1800.0,  # 30 minutes
            trainer_name="Test Trainer",
            total_distance_m=10000.0,  # 10 km
            avg_power_w=200.0,
            max_power_w=300.0,
            avg_cadence_rpm=90.0,
        )
        
        with patch('terminalride.ui.views.TrainingRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_session.return_value = mock_session
            
            result = view.render(state)
            result_str = str(result)
            
            # Check that session data is displayed
            assert "Good job" in result_str
            assert "30:00" in result_str  # Duration HH:MM
            assert "10.0" in result_str   # Distance km
            assert "200" in result_str    # Avg Power
            assert "90" in result_str     # Avg Cadence
            assert "300" in result_str    # Max Power
            
            # Check that controls are shown
            assert "s" in result_str or "Esc" in result_str  # Keep session
            assert "d" in result_str  # Discard session

    def test_summary_view_handles_missing_session(self):
        """Test that SummaryView gracefully handles missing session data."""
        view = SummaryView()
        
        state = AppState()
        state.last_session_id = None
        
        result = view.render(state)
        result_str = str(result)
        
        # Should show fallback message
        assert "No session" in result_str or "Error" in result_str

    def test_summary_view_handles_repository_error(self):
        """Test that SummaryView handles repository errors gracefully."""
        view = SummaryView()
        
        state = AppState()
        state.last_session_id = "test-session-123"
        
        with patch('terminalride.ui.views.TrainingRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_session.side_effect = Exception("Database error")
            
            result = view.render(state)
            result_str = str(result)
            
            # Should not crash and show error handling
            assert len(result_str) > 0  # Some content rendered

    def test_summary_view_handles_incomplete_session_data(self):
        """Test that SummaryView handles sessions with missing optional fields."""
        view = SummaryView()
        
        state = AppState()
        state.last_session_id = "test-session-123"
        
        # Mock session with minimal data
        mock_session = SessionModel(
            session_id="test-session-123",
            mode=TrainingMode.FREE,
            start_time=datetime(2023, 1, 1, 10, 0, 0),
            trainer_name="Test Trainer",
        )
        # Intentionally leave end_time, duration_s, etc. as None
        
        with patch('terminalride.ui.views.TrainingRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.get_session.return_value = mock_session
            
            result = view.render(state)
            result_str = str(result)
            
            # Should still render without crashing
            assert "Good job" in result_str
            # Should handle missing data gracefully (show N/A or 0)

    def test_summary_view_key_handling_keep_session(self):
        """Test handling of 's' key to keep session."""
        view = SummaryView()
        
        state = AppState()
        state.current_view = ViewState.SUMMARY
        
        # Test 's' key
        result = view.handle_key('s', state)
        assert result == ViewState.HOME
        
        # Test 'escape' key
        result = view.handle_key('escape', state)
        assert result == ViewState.HOME

    def test_summary_view_key_handling_discard_session(self):
        """Test handling of 'd' key to discard session."""
        view = SummaryView()
        
        state = AppState()
        state.current_view = ViewState.SUMMARY
        state.last_session_id = "test-session-123"
        
        with patch('terminalride.ui.views.TrainingRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.delete_session.return_value = True
            
            result = view.handle_key('d', state)
            
            # Should return to HOME view
            assert result == ViewState.HOME
            
            # Should have called delete_session
            mock_repo.delete_session.assert_called_once_with("test-session-123")
            
            # Should have set status message
            assert "discarded" in state.status_message.lower()

    def test_summary_view_key_handling_discard_failure(self):
        """Test handling of 'd' key when discard fails."""
        view = SummaryView()
        
        state = AppState()
        state.current_view = ViewState.SUMMARY
        state.last_session_id = "test-session-123"
        
        with patch('terminalride.ui.views.TrainingRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_repo.delete_session.return_value = False
            
            result = view.handle_key('d', state)
            
            # Should still return to HOME
            assert result == ViewState.HOME
            
            # Should have set failure message
            assert "failed" in state.status_message.lower()

    def test_summary_view_key_handling_unknown_key(self):
        """Test handling of unknown keys."""
        view = SummaryView()
        
        state = AppState()
        state.current_view = ViewState.SUMMARY
        
        # Unknown keys should not change view
        result = view.handle_key('x', state)
        assert result is None or result == ViewState.SUMMARY