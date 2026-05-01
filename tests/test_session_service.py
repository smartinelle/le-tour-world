"""Tests for SessionService domain layer."""

from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from terminalride.domain.session_service import SessionService, get_session_service
from terminalride.store.models import SessionModel, SampleModel, SessionSummary


class TestSessionServiceBasics:
    """Test SessionService basic functionality."""

    def test_init_with_default_repository(self):
        """Test initialization creates default repository."""
        with patch(
            "terminalride.domain.session_service.TrainingRepository"
        ) as MockRepo:
            mock_repo = Mock()
            MockRepo.return_value = mock_repo

            service = SessionService()

            MockRepo.assert_called_once()
            assert service._repository is mock_repo

    def test_init_with_custom_repository(self):
        """Test initialization with custom repository."""
        mock_repo = Mock()

        service = SessionService(repository=mock_repo)

        assert service._repository is mock_repo


class TestSessionServiceWriteOperations:
    """Test write operations."""

    def test_save_session(self):
        """Test saving a session delegates to repository."""
        mock_repo = Mock()
        service = SessionService(repository=mock_repo)

        session = SessionModel(
            session_id="test-123",
            mode="erg",
            start_time=datetime.now(),
            trainer_name="Wahoo KICKR",
        )

        service.save_session(session)

        mock_repo.save_session.assert_called_once_with(session)

    def test_save_sample(self):
        """Test saving a sample delegates to repository."""
        mock_repo = Mock()
        service = SessionService(repository=mock_repo)

        sample = SampleModel(
            session_id="test-123",
            elapsed_s=0.0,
            ts=1234567890.0,
            power_w=200,
            cadence_rpm=90,
        )

        service.save_sample(sample)

        mock_repo.save_sample.assert_called_once_with(sample)

    def test_delete_session_success(self):
        """Test successful session deletion."""
        mock_repo = Mock()
        mock_repo.delete_session.return_value = True
        mock_repo.sessions_file = Path("/tmp/sessions.jsonl")
        mock_repo.samples_file = Path("/tmp/samples.jsonl")

        service = SessionService(repository=mock_repo)

        with patch.object(service, "_prune_jsonl") as mock_prune:
            result = service.delete_session("test-123")

        assert result is True
        mock_repo.delete_session.assert_called_once_with("test-123")
        # Should prune both files
        assert mock_prune.call_count == 2

    def test_delete_session_not_found(self):
        """Test session deletion when session doesn't exist."""
        mock_repo = Mock()
        mock_repo.delete_session.return_value = False

        service = SessionService(repository=mock_repo)

        with patch.object(service, "_prune_jsonl") as mock_prune:
            result = service.delete_session("nonexistent")

        assert result is False
        # Should not prune if delete failed
        mock_prune.assert_not_called()


class TestSessionServiceReadOperations:
    """Test read operations."""

    def test_get_session(self):
        """Test getting a session by ID."""
        mock_repo = Mock()
        expected_session = SessionModel(
            session_id="test-123",
            mode="free",
            start_time=datetime.now(),
            trainer_name="Test Trainer",
        )
        mock_repo.get_session.return_value = expected_session

        service = SessionService(repository=mock_repo)

        result = service.get_session("test-123")

        assert result == expected_session
        mock_repo.get_session.assert_called_once_with("test-123")

    def test_get_session_not_found(self):
        """Test getting a non-existent session."""
        mock_repo = Mock()
        mock_repo.get_session.return_value = None

        service = SessionService(repository=mock_repo)

        result = service.get_session("nonexistent")

        assert result is None

    def test_list_sessions(self):
        """Test listing sessions with pagination."""
        mock_repo = Mock()
        mock_repo.list_sessions.return_value = [
            SessionModel(
                session_id="1", mode="erg", start_time=datetime.now(), trainer_name="T"
            ),
            SessionModel(
                session_id="2", mode="free", start_time=datetime.now(), trainer_name="T"
            ),
        ]

        service = SessionService(repository=mock_repo)

        result = service.list_sessions(limit=10, offset=5)

        assert len(result) == 2
        mock_repo.list_sessions.assert_called_once_with(limit=10, offset=5)

    def test_list_sessions_default_params(self):
        """Test listing sessions with default parameters."""
        mock_repo = Mock()
        mock_repo.list_sessions.return_value = []

        service = SessionService(repository=mock_repo)

        service.list_sessions()

        mock_repo.list_sessions.assert_called_once_with(limit=50, offset=0)

    def test_get_session_samples(self):
        """Test getting samples for a session."""
        mock_repo = Mock()
        mock_repo.get_session_samples.return_value = [
            SampleModel(session_id="test-123", elapsed_s=1.0, power_w=200),
            SampleModel(session_id="test-123", elapsed_s=2.0, power_w=210),
        ]

        service = SessionService(repository=mock_repo)

        result = service.get_session_samples("test-123")

        assert len(result) == 2
        mock_repo.get_session_samples.assert_called_once_with("test-123")

    def test_get_session_summary(self):
        """Test getting session summary."""
        mock_repo = Mock()
        expected_summary = SessionSummary(
            session_id="test-123",
            mode="erg",
            duration_s=1800.0,
            start_time=datetime.now(),
            total_distance_m=15000.0,
            avg_power_w=200.0,
        )
        mock_repo.get_session_summary.return_value = expected_summary

        service = SessionService(repository=mock_repo)

        result = service.get_session_summary("test-123")

        assert result == expected_summary
        mock_repo.get_session_summary.assert_called_once_with("test-123")


class TestSessionServicePruneJsonl:
    """Test JSONL pruning functionality."""

    def test_prune_nonexistent_file(self, tmp_path):
        """Test pruning a file that doesn't exist."""
        mock_repo = Mock()
        service = SessionService(repository=mock_repo)

        nonexistent = tmp_path / "nonexistent.jsonl"

        # Should not raise
        service._prune_jsonl(nonexistent, "test-123")

    def test_prune_removes_matching_entries(self, tmp_path):
        """Test pruning removes entries with matching session_id."""
        mock_repo = Mock()
        service = SessionService(repository=mock_repo)

        jsonl_file = tmp_path / "sessions.jsonl"
        jsonl_file.write_text(
            '{"session_id": "keep-1", "data": "a"}\n'
            '{"session_id": "remove-me", "data": "b"}\n'
            '{"session_id": "keep-2", "data": "c"}\n'
            '{"session_id": "remove-me", "data": "d"}\n'
        )

        service._prune_jsonl(jsonl_file, "remove-me")

        content = jsonl_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 2
        assert "keep-1" in lines[0]
        assert "keep-2" in lines[1]
        assert "remove-me" not in content

    def test_prune_preserves_malformed_lines(self, tmp_path):
        """Test that malformed JSON lines are preserved."""
        mock_repo = Mock()
        service = SessionService(repository=mock_repo)

        jsonl_file = tmp_path / "sessions.jsonl"
        jsonl_file.write_text(
            '{"session_id": "keep-1", "data": "a"}\n'
            "this is not valid json\n"
            '{"session_id": "remove-me", "data": "b"}\n'
        )

        service._prune_jsonl(jsonl_file, "remove-me")

        content = jsonl_file.read_text()
        lines = content.strip().split("\n")

        assert len(lines) == 2
        assert "keep-1" in lines[0]
        assert "this is not valid json" in lines[1]

    def test_prune_handles_empty_file(self, tmp_path):
        """Test pruning an empty file."""
        mock_repo = Mock()
        service = SessionService(repository=mock_repo)

        jsonl_file = tmp_path / "empty.jsonl"
        jsonl_file.write_text("")

        # Should not raise
        service._prune_jsonl(jsonl_file, "test-123")

        assert jsonl_file.read_text() == ""

    def test_prune_cleans_up_temp_file_on_error(self, tmp_path):
        """Test that temp file is cleaned up if error occurs."""
        mock_repo = Mock()
        service = SessionService(repository=mock_repo)

        jsonl_file = tmp_path / "sessions.jsonl"
        jsonl_file.write_text('{"session_id": "test"}\n')

        with patch("builtins.open", side_effect=PermissionError("No access")):
            # Should not raise, but should try to clean up
            service._prune_jsonl(jsonl_file, "test")

        # Original file should still exist
        assert jsonl_file.exists()


class TestSessionServiceSingleton:
    """Test singleton instance management."""

    def test_get_session_service_returns_instance(self):
        """Test get_session_service returns a SessionService instance."""
        # Reset singleton
        import terminalride.domain.session_service as module

        module._session_service = None

        with patch("terminalride.domain.session_service.TrainingRepository"):
            service = get_session_service()

        assert isinstance(service, SessionService)

    def test_get_session_service_returns_same_instance(self):
        """Test get_session_service returns the same instance."""
        import terminalride.domain.session_service as module

        module._session_service = None

        with patch("terminalride.domain.session_service.TrainingRepository"):
            service1 = get_session_service()
            service2 = get_session_service()

        assert service1 is service2
