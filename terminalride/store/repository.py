"""Data repository for training sessions and samples."""

import json
import sqlite3
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager
import logging

from .models import SessionModel, SampleModel, SessionSummary
from ..config import get_config
from ..analytics import calculate_training_metrics

logger = logging.getLogger(__name__)


class TrainingRepository:
    """Repository for training data storage and retrieval."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = get_config().get_data_dir()

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # JSONL files for raw storage
        self.sessions_file = self.data_dir / "sessions.jsonl"
        self.samples_file = self.data_dir / "samples.jsonl"

        # SQLite database for queries (optional optimization)
        self.db_file = self.data_dir / "terminalride.db"
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database with schema."""
        try:
            with self._get_db_connection() as conn:
                # Sessions table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        duration_s REAL,
                        trainer_name TEXT,
                        user_mass_kg REAL,
                        user_ftp_w INTEGER,
                        avg_power_w REAL,
                        max_power_w INTEGER,
                        avg_cadence_rpm REAL,
                        avg_speed_mps REAL,
                        total_distance_m REAL,
                        normalized_power_w REAL,
                        intensity_factor REAL,
                        training_stress_score REAL,
                        notes TEXT,
                        data_json TEXT  -- Full JSON for complex fields
                    )
                """)

                # Samples table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS samples (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        elapsed_s REAL NOT NULL,
                        power_w INTEGER,
                        cadence_rpm INTEGER,
                        speed_mps REAL,
                        distance_m REAL,
                        hr_bpm INTEGER,
                        erg_target_power_w INTEGER,
                        sim_grade_pct REAL,
                        FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                    )
                """)

                # Indexes for common queries
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_samples_session_id ON samples(session_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_samples_timestamp ON samples(timestamp)"
                )

                conn.commit()
                logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    @contextmanager
    def _get_db_connection(self):
        """Get database connection with automatic cleanup."""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def save_session(self, session: SessionModel) -> None:
        """Save training session to JSONL and database."""
        try:
            # Save to JSONL (primary storage)
            with open(self.sessions_file, "a", encoding="utf-8") as f:
                json_data = session.model_dump_json()
                f.write(json_data + "\n")

            # Save to database (for queries)
            with self._get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO sessions (
                        session_id, created_at, mode, start_time, end_time, duration_s,
                        trainer_name, user_mass_kg, user_ftp_w, avg_power_w, max_power_w,
                        avg_cadence_rpm, avg_speed_mps, total_distance_m,
                        normalized_power_w, intensity_factor, training_stress_score,
                        notes, data_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        session.session_id,
                        session.created_at.isoformat(),
                        session.mode.value,
                        session.start_time.isoformat(),
                        session.end_time.isoformat() if session.end_time else None,
                        session.duration_s,
                        session.trainer_name,
                        session.user_mass_kg,
                        session.user_ftp_w,
                        session.avg_power_w,
                        session.max_power_w,
                        session.avg_cadence_rpm,
                        session.avg_speed_mps,
                        session.total_distance_m,
                        session.normalized_power_w,
                        session.intensity_factor,
                        session.training_stress_score,
                        session.notes,
                        json_data,
                    ),
                )
                conn.commit()

            logger.info(f"Session {session.session_id} saved successfully")

        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            raise

    def save_sample(self, sample: SampleModel) -> None:
        """Save training sample to JSONL and database."""
        try:
            # Save to JSONL (primary storage)
            with open(self.samples_file, "a", encoding="utf-8") as f:
                json_data = sample.model_dump_json()
                f.write(json_data + "\n")

            # Save to database (for queries)
            with self._get_db_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO samples (
                        session_id, timestamp, elapsed_s, power_w, cadence_rpm,
                        speed_mps, distance_m, hr_bpm, erg_target_power_w, sim_grade_pct
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        sample.session_id,
                        sample.timestamp.isoformat(),
                        sample.elapsed_s,
                        sample.power_w,
                        sample.cadence_rpm,
                        sample.speed_mps,
                        sample.distance_m,
                        sample.hr_bpm,
                        sample.erg_target_power_w,
                        sample.sim_grade_pct,
                    ),
                )
                conn.commit()

        except Exception as e:
            logger.error(f"Failed to save sample: {e}")
            # Don't raise - sample loss is not critical

    def get_session(self, session_id: str) -> Optional[SessionModel]:
        """Get session by ID."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    "SELECT data_json FROM sessions WHERE session_id = ?", (session_id,)
                )
                row = cursor.fetchone()

                if row:
                    return SessionModel.model_validate_json(row["data_json"])
                return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionModel]:
        """List recent sessions."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT data_json FROM sessions 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """,
                    (limit, offset),
                )

                sessions = []
                for row in cursor:
                    try:
                        session = SessionModel.model_validate_json(row["data_json"])
                        sessions.append(session)
                    except Exception as e:
                        logger.warning(f"Failed to parse session data: {e}")
                        continue

                return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def get_session_samples(self, session_id: str) -> List[SampleModel]:
        """Get all samples for a session."""
        try:
            # For efficiency, read from JSONL file
            samples = []
            if not self.samples_file.exists():
                return samples

            with open(self.samples_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        sample_data = json.loads(line.strip())
                        if sample_data.get("session_id") == session_id:
                            sample = SampleModel.model_validate(sample_data)
                            samples.append(sample)
                    except Exception as e:
                        logger.debug(f"Failed to parse sample line: {e}")
                        continue

            # Sort by elapsed time
            samples.sort(key=lambda s: s.elapsed_s)
            return samples

        except Exception as e:
            logger.error(f"Failed to get samples for session {session_id}: {e}")
            return []

    def get_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        """Get session summary with calculated statistics."""
        session = self.get_session(session_id)
        if not session:
            return None

        try:
            samples = self.get_session_samples(session_id)
            if not samples:
                return None

            # Calculate statistics from samples
            power_values = [s.power_w for s in samples if s.power_w is not None]
            cadence_values = [
                s.cadence_rpm for s in samples if s.cadence_rpm is not None
            ]
            speed_values = [s.speed_mps for s in samples if s.speed_mps is not None]
            hr_values = [s.hr_bpm for s in samples if s.hr_bpm is not None]

            # Get final distance
            distance_samples = [
                s.distance_m for s in samples if s.distance_m is not None
            ]
            total_distance_m = max(distance_samples) if distance_samples else 0.0

            # Calculate training metrics (NP, IF, TSS) using analytics module
            duration_s = session.duration_s or 0.0
            normalized_power_w: Optional[float] = None
            intensity_factor: Optional[float] = None
            training_stress_score: Optional[float] = None

            if power_values and duration_s > 0:
                metrics = calculate_training_metrics(
                    power_samples=power_values,
                    duration_seconds=duration_s,
                    ftp_w=session.user_ftp_w,
                    sample_rate_hz=1.0,  # Assume 1Hz sampling
                )
                if metrics:
                    normalized_power_w = metrics.normalized_power_w
                    intensity_factor = metrics.intensity_factor
                    training_stress_score = metrics.training_stress_score

            return SessionSummary(
                session_id=session.session_id,
                mode=session.mode.value,
                duration_s=duration_s,
                start_time=session.start_time,
                total_distance_m=total_distance_m,
                avg_power_w=(
                    sum(power_values) / len(power_values) if power_values else None
                ),
                max_power_w=max(power_values) if power_values else None,
                avg_cadence_rpm=(
                    sum(cadence_values) / len(cadence_values)
                    if cadence_values
                    else None
                ),
                max_cadence_rpm=max(cadence_values) if cadence_values else None,
                avg_speed_mps=(
                    sum(speed_values) / len(speed_values) if speed_values else None
                ),
                max_speed_mps=max(speed_values) if speed_values else None,
                avg_hr_bpm=sum(hr_values) / len(hr_values) if hr_values else None,
                max_hr_bpm=max(hr_values) if hr_values else None,
                normalized_power_w=normalized_power_w,
                intensity_factor=intensity_factor,
                training_stress_score=training_stress_score,
            )

        except Exception as e:
            logger.error(f"Failed to calculate session summary: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete session and all its samples."""
        try:
            with self._get_db_connection() as conn:
                # Delete samples first
                conn.execute("DELETE FROM samples WHERE session_id = ?", (session_id,))

                # Delete session
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE session_id = ?", (session_id,)
                )

                conn.commit()

                deleted = cursor.rowcount > 0
                if deleted:
                    logger.info(f"Session {session_id} deleted successfully")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
