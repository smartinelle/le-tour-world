"""Tests for UI views."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from rich.console import Console
from rich.text import Text

from terminalride.ui.views import AppState, SummaryView, ViewState
from terminalride.store.models import SessionSummary


class TestSummaryView:
    """Tests for the SummaryView."""

    @staticmethod
    def _render_text(layout) -> str:
        console = Console(record=True, width=120)
        console.print(layout)
        return console.export_text()

    def test_summary_view_renders_with_valid_session(self):
        state = AppState()
        state.last_session_id = "test-session-123"

        summary = SessionSummary(
            session_id="test-session-123",
            mode="erg",
            duration_s=1800.0,
            start_time=datetime(2023, 1, 1, 10, 0, 0),
            total_distance_m=10000.0,
            avg_power_w=200.0,
            max_power_w=300,
            avg_cadence_rpm=90.0,
            avg_speed_mps=10000.0 / 1800.0,
        )

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc = MagicMock()
            svc_factory.return_value = svc
            svc.get_session_summary.return_value = summary

            view = SummaryView()
            layout = view.render(state)

        rendered = self._render_text(layout)
        assert "Good job" in rendered
        assert "00:30:00" in rendered
        assert "10.00 km" in rendered
        assert "200 W" in rendered
        assert "300 W" in rendered
        assert "90 rpm" in rendered
        assert "20.0 km/h" in rendered

    def test_summary_view_handles_missing_session(self):
        state = AppState()

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc_factory.return_value = MagicMock()
            view = SummaryView()

            layout = view.render(state)
            rendered = self._render_text(layout)

        assert "Duration" in rendered
        assert "00:00:00" in rendered
        assert "[s] Save and finish" in rendered

    def test_summary_view_handles_repository_error(self):
        state = AppState()
        state.last_session_id = "test-session-123"

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc = MagicMock()
            svc_factory.return_value = svc
            svc.get_session_summary.side_effect = Exception("Database error")

            view = SummaryView()
            layout = view.render(state)

        rendered = self._render_text(layout)
        assert "Duration" in rendered

    def test_summary_view_handles_incomplete_session_data(self):
        state = AppState()
        state.last_session_id = "test-session-123"

        summary = SessionSummary(
            session_id="test-session-123",
            mode="free",
            duration_s=0.0,
            start_time=datetime(2023, 1, 1, 10, 0, 0),
            total_distance_m=0.0,
        )

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc = MagicMock()
            svc_factory.return_value = svc
            svc.get_session_summary.return_value = summary

            view = SummaryView()
            layout = view.render(state)

        rendered = self._render_text(layout)
        assert "--- W" in rendered
        assert "--- rpm" in rendered
        assert "--- km/h" in rendered

    def test_summary_view_key_handling_keep_session(self):
        state = AppState()
        state.current_view = ViewState.SUMMARY

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc_factory.return_value = MagicMock()
            view = SummaryView()

            assert view.handle_key("s", state) == ViewState.HOME
            assert view.handle_key("escape", state) == ViewState.HOME

    def test_summary_view_key_handling_discard_session(self):
        state = AppState()
        state.current_view = ViewState.SUMMARY
        state.last_session_id = "test-session-123"

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc = MagicMock()
            svc_factory.return_value = svc
            svc.delete_session.return_value = True

            view = SummaryView()
            result = view.handle_key("d", state)

        assert result == ViewState.HOME
        svc.delete_session.assert_called_once_with("test-session-123")
        assert "discarded" in state.status_message.lower()

    def test_summary_view_key_handling_discard_failure(self):
        state = AppState()
        state.current_view = ViewState.SUMMARY
        state.last_session_id = "test-session-123"

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc = MagicMock()
            svc_factory.return_value = svc
            svc.delete_session.return_value = False

            view = SummaryView()
            result = view.handle_key("d", state)

        assert result == ViewState.HOME
        assert "failed" in state.status_message.lower()

    def test_summary_view_key_handling_unknown_key(self):
        state = AppState()
        state.current_view = ViewState.SUMMARY

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc_factory.return_value = MagicMock()
            view = SummaryView()

            result = view.handle_key("x", state)
        assert result is None or result == ViewState.SUMMARY

    def test_summary_controls_use_plain_text(self):
        state = AppState()

        with patch("terminalride.ui.views.get_session_service") as svc_factory:
            svc_factory.return_value = MagicMock()
            view = SummaryView()

            layout = view.render(state)
        controls_panel = layout["controls"].renderable

        assert isinstance(controls_panel.renderable, Text)
        assert controls_panel.renderable.plain.startswith("[s] Save and finish")
