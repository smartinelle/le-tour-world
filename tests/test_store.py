"""Tests for data storage and export functionality."""

import tempfile
from datetime import datetime, timedelta, UTC
from pathlib import Path
import csv

from terminalride.store.models import SessionModel, SampleModel, TrainingMode
from terminalride.store.repository import TrainingRepository
from terminalride.store.export import DataExporter


class TestDataModels:
    """Test data models."""

    def test_session_model_creation(self):
        """Test SessionModel creation and validation."""
        session = SessionModel(
            mode=TrainingMode.ERG,
            start_time=datetime.now(UTC),
            user_mass_kg=75.0,
            user_ftp_w=250,
            erg_target_power_w=200,
        )

        assert session.mode == TrainingMode.ERG
        assert session.session_id is not None
        assert len(session.session_id) > 10  # UUID should be long
        assert session.user_mass_kg == 75.0
        assert session.erg_target_power_w == 200

    def test_sample_model_creation(self):
        """Test SampleModel creation and computed fields."""
        sample = SampleModel(
            session_id="test-session",
            elapsed_s=120.0,
            power_w=250,
            cadence_rpm=85,
            speed_mps=10.0,
        )

        assert sample.session_id == "test-session"
        assert sample.elapsed_s == 120.0
        assert sample.power_w == 250
        assert sample.speed_kph == 36.0  # 10 m/s * 3.6

    def test_session_serialization(self):
        """Test session JSON serialization."""
        session = SessionModel(
            mode=TrainingMode.FREE, start_time=datetime.now(UTC), notes="Test session"
        )

        # Should serialize to JSON without errors
        json_str = session.model_dump_json()
        assert "free" in json_str
        assert "Test session" in json_str

        # Should deserialize back correctly
        restored = SessionModel.model_validate_json(json_str)
        assert restored.mode == TrainingMode.FREE
        assert restored.notes == "Test session"


class TestTrainingRepository:
    """Test training data repository."""

    def setup_method(self):
        """Set up test with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo = TrainingRepository(Path(self.temp_dir))

    def test_save_and_get_session(self):
        """Test saving and retrieving sessions."""
        session = SessionModel(
            mode=TrainingMode.ERG,
            start_time=datetime.now(UTC),
            user_ftp_w=300,
            notes="Test ERG session",
        )

        # Save session
        self.repo.save_session(session)

        # Retrieve session
        retrieved = self.repo.get_session(session.session_id)

        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        assert retrieved.mode == TrainingMode.ERG
        assert retrieved.user_ftp_w == 300
        assert retrieved.notes == "Test ERG session"

    def test_save_and_get_samples(self):
        """Test saving and retrieving training samples."""
        session_id = "test-session-123"

        # Create test samples
        samples = [
            SampleModel(
                session_id=session_id,
                elapsed_s=i * 1.0,
                power_w=200 + i,
                cadence_rpm=80 + i,
                speed_mps=8.0 + i * 0.1,
            )
            for i in range(5)
        ]

        # Save samples
        for sample in samples:
            self.repo.save_sample(sample)

        # Retrieve samples
        retrieved = self.repo.get_session_samples(session_id)

        assert len(retrieved) == 5
        assert retrieved[0].elapsed_s == 0.0
        assert retrieved[0].power_w == 200
        assert retrieved[4].elapsed_s == 4.0
        assert retrieved[4].power_w == 204

    def test_list_sessions(self):
        """Test listing sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = SessionModel(
                mode=TrainingMode.FREE,
                start_time=datetime.now(UTC) + timedelta(minutes=i),
                notes=f"Session {i}",
            )
            sessions.append(session)
            self.repo.save_session(session)

        # List sessions (should be in reverse chronological order)
        listed = self.repo.list_sessions(limit=10)

        assert len(listed) == 3
        # Most recent first
        assert "Session 2" in listed[0].notes
        assert "Session 0" in listed[2].notes

    def test_session_summary_calculation(self):
        """Test session summary calculation."""
        # Create session
        session = SessionModel(
            mode=TrainingMode.ERG,
            start_time=datetime.now(UTC),
            duration_s=300.0,  # 5 minutes
        )
        self.repo.save_session(session)

        # Add sample data
        for i in range(5):
            sample = SampleModel(
                session_id=session.session_id,
                elapsed_s=i * 60.0,  # Every minute
                power_w=200 + i * 10,  # Increasing power
                cadence_rpm=80,
                distance_m=i * 500.0,  # 500m per minute
            )
            self.repo.save_sample(sample)

        # Get summary
        summary = self.repo.get_session_summary(session.session_id)

        assert summary is not None
        assert summary.duration_s == 300.0
        assert summary.total_distance_km == 2.0  # 2000m total
        assert summary.avg_power_w == 220.0  # Average of 200,210,220,230,240
        assert summary.max_power_w == 240


class TestDataExporter:
    """Test data export functionality."""

    def setup_method(self):
        """Set up test with temporary repository and exporter."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo = TrainingRepository(Path(self.temp_dir))
        self.exporter = DataExporter(self.repo)

    def test_csv_export(self):
        """Test CSV export functionality."""
        # Create session with samples
        session = SessionModel(
            mode=TrainingMode.ERG, start_time=datetime.now(UTC), notes="CSV export test"
        )
        self.repo.save_session(session)

        # Add samples
        for i in range(3):
            sample = SampleModel(
                session_id=session.session_id,
                elapsed_s=i * 30.0,
                power_w=250 + i * 5,
                cadence_rpm=85,
                speed_mps=9.0,
                erg_target_power_w=250,
            )
            self.repo.save_sample(sample)

        # Export to CSV
        output_path = Path(self.temp_dir) / "test_export.csv"
        success = self.exporter.export_session_to_csv(session.session_id, output_path)

        assert success
        assert output_path.exists()

        # Verify CSV content
        with open(output_path, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            assert len(rows) == 3
            assert rows[0]["power_w"] == "250"
            assert rows[0]["cadence_rpm"] == "85"
            assert rows[0]["speed_kph"] == "32.4"  # 9.0 * 3.6
            assert rows[0]["mode"] == "erg"
            assert rows[1]["power_w"] == "255"
            assert rows[2]["power_w"] == "260"

    def test_csv_export_preserves_zero_speed_and_distance(self):
        """Zero-valued metrics are valid samples, not missing data."""
        session = SessionModel(mode=TrainingMode.FREE, start_time=datetime.now(UTC))
        self.repo.save_session(session)
        self.repo.save_sample(
            SampleModel(
                session_id=session.session_id,
                elapsed_s=0.0,
                power_w=0,
                cadence_rpm=0,
                speed_mps=0.0,
                distance_m=0.0,
            )
        )

        output_path = Path(self.temp_dir) / "zero_export.csv"
        success = self.exporter.export_session_to_csv(session.session_id, output_path)

        assert success
        with open(output_path, "r") as f:
            rows = list(csv.DictReader(f))

        assert rows[0]["speed_mps"] == "0.0"
        assert rows[0]["speed_kph"] == "0.0"
        assert rows[0]["distance_m"] == "0.0"
        assert rows[0]["distance_km"] == "0.0"

    def test_auto_export_filename(self):
        """Test automatic export with proper filename generation."""
        session = SessionModel(
            mode=TrainingMode.SIM,
            start_time=datetime(2024, 3, 15, 14, 30, 0),
            notes="Auto export test",
        )
        self.repo.save_session(session)

        # Add at least one sample
        sample = SampleModel(session_id=session.session_id, elapsed_s=0.0, power_w=200)
        self.repo.save_sample(sample)

        # Export automatically
        export_dir = Path(self.temp_dir) / "exports"
        exported_path = self.exporter.auto_export_session(
            session.session_id, export_dir
        )

        assert exported_path is not None
        assert exported_path.exists()

        # Check filename format
        filename = exported_path.name
        assert filename.startswith("le-tour_2024-03-15_14-30_sim_")
        assert filename.endswith(".csv")

    def test_export_formats_list(self):
        """Test export formats listing."""
        formats = self.exporter.get_export_formats()

        assert len(formats) >= 2
        assert any(fmt["name"] == "CSV (Training Data)" for fmt in formats)
        assert any(fmt["extension"] == ".csv" for fmt in formats)
