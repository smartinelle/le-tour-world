"""Session persistence service to decouple UI from storage details."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

from ..store.models import SessionModel, SampleModel, SessionSummary
from ..store.repository import TrainingRepository

logger = logging.getLogger(__name__)


class SessionService:
    """Thin service layer around TrainingRepository."""

    def __init__(self, repository: Optional[TrainingRepository] = None) -> None:
        self._repository = repository or TrainingRepository()

    # Write operations
    def save_session(self, session: SessionModel) -> None:
        self._repository.save_session(session)

    def save_sample(self, sample: SampleModel) -> None:
        self._repository.save_sample(sample)

    def delete_session(self, session_id: str) -> bool:
        deleted = self._repository.delete_session(session_id)
        if deleted:
            self._prune_jsonl(self._repository.sessions_file, session_id)
            self._prune_jsonl(self._repository.samples_file, session_id)
        return deleted

    # Read operations
    def get_session(self, session_id: str) -> Optional[SessionModel]:
        return self._repository.get_session(session_id)

    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[SessionModel]:
        return self._repository.list_sessions(limit=limit, offset=offset)

    def get_session_samples(self, session_id: str) -> List[SampleModel]:
        return self._repository.get_session_samples(session_id)

    def get_session_summary(self, session_id: str) -> Optional[SessionSummary]:
        return self._repository.get_session_summary(session_id)

    # Internal helpers
    def _prune_jsonl(self, file_path: Path, session_id: str) -> None:
        """Rewrite JSONL file without entries for the given session_id."""
        if not file_path.exists():
            return

        tmp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        removed = 0
        try:
            with (
                open(file_path, "r", encoding="utf-8") as src,
                open(tmp_path, "w", encoding="utf-8") as dst,
            ):
                for line in src:
                    try:
                        data = json.loads(line)
                    except Exception:
                        # Keep malformed lines; don't risk losing unrelated data
                        dst.write(line)
                        continue

                    if data.get("session_id") == session_id:
                        removed += 1
                        continue

                    dst.write(line)

            tmp_path.replace(file_path)
            if removed:
                logger.info(
                    "Pruned %s entries for session %s from %s",
                    removed,
                    session_id,
                    file_path.name,
                )
        except Exception as e:
            logger.warning(
                "Failed to prune %s for session %s: %s",
                file_path,
                session_id,
                e,
            )
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass


_session_service: Optional[SessionService] = None


def get_session_service() -> SessionService:
    """Get (or create) the shared session service instance."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
