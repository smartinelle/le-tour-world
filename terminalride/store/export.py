"""Export functionality for training data."""

import csv
from pathlib import Path
from typing import List, Optional, Dict
import logging

from .repository import TrainingRepository

logger = logging.getLogger(__name__)


class DataExporter:
    """Export training data to various formats."""

    def __init__(self, repository: Optional[TrainingRepository] = None):
        self.repository = repository or TrainingRepository()

    def export_session_to_csv(self, session_id: str, output_path: Path) -> bool:
        """Export session samples to CSV format.

        Args:
            session_id: Session to export
            output_path: Output file path

        Returns:
            True if export successful, False otherwise
        """
        try:
            session = self.repository.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False

            samples = self.repository.get_session_samples(session_id)
            if not samples:
                logger.warning(f"No samples found for session {session_id}")

            # CSV header matching specification
            fieldnames = [
                "timestamp_iso",
                "elapsed_s",
                "power_w",
                "cadence_rpm",
                "speed_mps",
                "speed_kph",
                "distance_m",
                "distance_km",
                "hr_bpm",
                "mode",
                "erg_target_w",
                "sim_grade_pct",
            ]

            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for sample in samples:
                    row = {
                        "timestamp_iso": sample.timestamp.isoformat(),
                        "elapsed_s": sample.elapsed_s,
                        "power_w": sample.power_w,
                        "cadence_rpm": sample.cadence_rpm,
                        "speed_mps": sample.speed_mps,
                        "speed_kph": (
                            sample.speed_mps * 3.6 if sample.speed_mps else None
                        ),
                        "distance_m": sample.distance_m,
                        "distance_km": (
                            sample.distance_m / 1000.0 if sample.distance_m else None
                        ),
                        "hr_bpm": sample.hr_bpm,
                        "mode": session.mode.value,
                        "erg_target_w": sample.erg_target_power_w,
                        "sim_grade_pct": sample.sim_grade_pct,
                    }
                    writer.writerow(row)

            logger.info(f"Session {session_id} exported to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export session {session_id} to CSV: {e}")
            return False

    def export_session_summary_csv(self, output_path: Path, limit: int = 100) -> bool:
        """Export session summaries to CSV.

        Args:
            output_path: Output file path
            limit: Maximum number of sessions to export

        Returns:
            True if export successful, False otherwise
        """
        try:
            sessions = self.repository.list_sessions(limit=limit)
            if not sessions:
                logger.warning("No sessions found to export")
                return False

            fieldnames = [
                "session_id",
                "start_time_iso",
                "mode",
                "duration_s",
                "duration_min",
                "trainer_name",
                "total_distance_km",
                "avg_power_w",
                "max_power_w",
                "avg_cadence_rpm",
                "avg_speed_kph",
                "avg_hr_bpm",
                "max_hr_bpm",
                "normalized_power_w",
                "intensity_factor",
                "training_stress_score",
                "notes",
            ]

            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for session in sessions:
                    row = {
                        "session_id": session.session_id,
                        "start_time_iso": session.start_time.isoformat(),
                        "mode": session.mode.value,
                        "duration_s": session.duration_s,
                        "duration_min": (
                            session.duration_s / 60.0 if session.duration_s else None
                        ),
                        "trainer_name": session.trainer_name,
                        "total_distance_km": (
                            session.total_distance_m / 1000.0
                            if session.total_distance_m
                            else None
                        ),
                        "avg_power_w": session.avg_power_w,
                        "max_power_w": session.max_power_w,
                        "avg_cadence_rpm": session.avg_cadence_rpm,
                        "avg_speed_kph": (
                            session.avg_speed_mps * 3.6
                            if session.avg_speed_mps
                            else None
                        ),
                        "avg_hr_bpm": session.avg_hr_bpm,
                        "max_hr_bpm": session.max_hr_bpm,
                        "normalized_power_w": session.normalized_power_w,
                        "intensity_factor": session.intensity_factor,
                        "training_stress_score": session.training_stress_score,
                        "notes": session.notes,
                    }
                    writer.writerow(row)

            logger.info(f"Session summaries exported to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export session summaries: {e}")
            return False

    def auto_export_session(
        self, session_id: str, export_dir: Optional[Path] = None
    ) -> Optional[Path]:
        """Automatically export session with standard filename.

        Args:
            session_id: Session to export
            export_dir: Directory for exports (uses default if None)

        Returns:
            Path to exported file if successful, None otherwise
        """
        try:
            session = self.repository.get_session(session_id)
            if not session:
                return None

            if export_dir is None:
                from ..config import get_config

                export_dir = get_config().get_data_dir() / "exports"

            export_dir = Path(export_dir)
            export_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename: le-tour_YYYY-MM-DD_HH-MM_MODE_ID.csv
            timestamp_str = session.start_time.strftime("%Y-%m-%d_%H-%M")
            filename = (
                f"le-tour_{timestamp_str}_{session.mode.value}_{session_id[:8]}.csv"
            )
            output_path = export_dir / filename

            success = self.export_session_to_csv(session_id, output_path)
            return output_path if success else None

        except Exception as e:
            logger.error(f"Failed to auto-export session {session_id}: {e}")
            return None

    def get_export_formats(self) -> List[Dict[str, str]]:
        """Get list of available export formats.

        Returns:
            List of format dictionaries with 'name', 'extension', 'description'
        """
        return [
            {
                "name": "CSV (Training Data)",
                "extension": ".csv",
                "description": "Comma-separated values with all training samples",
            },
            {
                "name": "CSV (Session Summary)",
                "extension": "_summary.csv",
                "description": "Session summary with aggregate statistics",
            },
            # Future formats:
            # - FIT files
            # - TCX files
            # - GPX files (for virtual routes)
        ]
