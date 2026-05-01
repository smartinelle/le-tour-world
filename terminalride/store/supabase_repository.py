"""Supabase-based repository for training data.

This module provides a cloud-based data repository that replaces the local
JSONL/SQLite storage for multi-user support.
"""

import logging
from typing import List, Optional, Any
from datetime import datetime

from ..supabase_client import get_supabase
from .models import SessionModel, SampleModel, TrainingMode

logger = logging.getLogger(__name__)


class SupabaseRepository:
    """Repository for training data using Supabase PostgreSQL.

    Row-Level Security (RLS) policies in the database ensure users
    can only access their own data. The user_id is enforced at
    the database level.

    Usage:
        repo = SupabaseRepository(user_id="uuid-string")
        await repo.save_session(session)
        sessions = await repo.list_sessions(limit=10)
    """

    def __init__(self, user_id: str) -> None:
        """Initialize repository for a specific user.

        Args:
            user_id: UUID of the authenticated user
        """
        if not user_id:
            raise ValueError("user_id is required")

        self.user_id = user_id
        self._supabase = None

    @property
    def supabase(self):
        """Lazy-load Supabase client."""
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    # =========================================================================
    # Session Operations
    # =========================================================================

    async def save_session(self, session: SessionModel) -> str:
        """Save or update a training session.

        Args:
            session: SessionModel to save

        Returns:
            Session ID
        """
        data = {
            "id": session.session_id,
            "user_id": self.user_id,
            "mode": (
                session.mode.value
                if isinstance(session.mode, TrainingMode)
                else session.mode
            ),
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "duration_s": session.duration_s,
            "trainer_name": session.trainer_name,
            "hr_device_name": session.hr_device_name,
            "total_distance_m": session.total_distance_m,
            "avg_power_w": session.avg_power_w,
            "max_power_w": session.max_power_w,
            "avg_cadence_rpm": session.avg_cadence_rpm,
            "avg_speed_mps": session.avg_speed_mps,
            "avg_hr_bpm": session.avg_hr_bpm,
            "max_hr_bpm": session.max_hr_bpm,
            "normalized_power_w": session.normalized_power_w,
            "intensity_factor": session.intensity_factor,
            "training_stress_score": session.training_stress_score,
            "user_ftp_w": session.user_ftp_w,
            "user_mass_kg": session.user_mass_kg,
            "erg_target_power_w": session.erg_target_power_w,
            "sim_grade_pct": session.sim_grade_pct,
        }

        # Remove None values to let database use defaults
        data = {k: v for k, v in data.items() if v is not None}

        self.supabase.table("sessions").upsert(data).execute()

        logger.info(f"Saved session {session.session_id} for user {self.user_id}")
        return session.session_id

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Get a session by ID.

        Args:
            session_id: UUID of the session

        Returns:
            Session data dict or None if not found
        """
        try:
            result = (
                self.supabase.table("sessions")
                .select("*")
                .eq("id", session_id)
                .single()
                .execute()
            )

            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """List user's training sessions.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of session data dicts, ordered by start_time descending
        """
        result = (
            self.supabase.table("sessions")
            .select("*")
            .order("start_time", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return result.data or []

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its samples.

        Args:
            session_id: UUID of the session to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            # Samples are deleted automatically via CASCADE
            self.supabase.table("sessions").delete().eq("id", session_id).execute()

            logger.info(f"Deleted session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    # =========================================================================
    # Sample Operations
    # =========================================================================

    async def save_samples(self, samples: List[SampleModel]) -> int:
        """Bulk save training samples.

        Args:
            samples: List of SampleModel instances

        Returns:
            Number of samples saved
        """
        if not samples:
            return 0

        data = [
            {
                "session_id": s.session_id,
                "timestamp": s.timestamp.isoformat(),
                "elapsed_s": s.elapsed_s,
                "power_w": s.power_w,
                "cadence_rpm": s.cadence_rpm,
                "speed_mps": s.speed_mps,
                "distance_m": s.distance_m,
                "hr_bpm": s.hr_bpm,
                "erg_target_power_w": s.erg_target_power_w,
                "sim_grade_pct": s.sim_grade_pct,
            }
            for s in samples
        ]

        # Remove None values from each sample
        data = [{k: v for k, v in sample.items() if v is not None} for sample in data]

        self.supabase.table("samples").insert(data).execute()

        logger.debug(f"Saved {len(samples)} samples")
        return len(samples)

    async def get_session_samples(self, session_id: str) -> List[dict]:
        """Get all samples for a session.

        Args:
            session_id: UUID of the session

        Returns:
            List of sample data dicts, ordered by elapsed_s
        """
        result = (
            self.supabase.table("samples")
            .select("*")
            .eq("session_id", session_id)
            .order("elapsed_s")
            .execute()
        )

        return result.data or []

    # =========================================================================
    # Profile Operations
    # =========================================================================

    async def get_profile(self) -> Optional[dict]:
        """Get user's profile.

        Returns:
            Profile data dict or None if not found
        """
        try:
            result = (
                self.supabase.table("profiles")
                .select("*")
                .eq("id", self.user_id)
                .single()
                .execute()
            )

            return result.data if result.data else None
        except Exception as e:
            logger.error(f"Failed to get profile for {self.user_id}: {e}")
            return None

    async def update_profile(self, **kwargs: Any) -> Optional[dict]:
        """Update user's profile.

        Args:
            **kwargs: Profile fields to update

        Returns:
            Updated profile data or None on failure
        """
        try:
            # Add updated_at timestamp
            kwargs["updated_at"] = datetime.utcnow().isoformat()

            result = (
                self.supabase.table("profiles")
                .update(kwargs)
                .eq("id", self.user_id)
                .execute()
            )

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")
            return None

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_session_count(self) -> int:
        """Get total number of sessions for user."""
        result = self.supabase.table("sessions").select("id", count="exact").execute()

        return result.count or 0

    async def get_total_distance_m(self) -> float:
        """Get total distance ridden across all sessions."""
        result = self.supabase.table("sessions").select("total_distance_m").execute()

        if not result.data:
            return 0.0

        return sum(s.get("total_distance_m", 0) or 0 for s in result.data)

    async def get_total_duration_s(self) -> float:
        """Get total training time across all sessions."""
        result = self.supabase.table("sessions").select("duration_s").execute()

        if not result.data:
            return 0.0

        return sum(s.get("duration_s", 0) or 0 for s in result.data)


def get_repository_for_user(user_id: str) -> SupabaseRepository:
    """Factory function to create a repository for a user.

    Args:
        user_id: UUID of the authenticated user

    Returns:
        SupabaseRepository instance
    """
    return SupabaseRepository(user_id)
