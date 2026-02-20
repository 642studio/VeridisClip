"""Clipping service entrypoints."""

from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.services.data_sync_service import DataSyncService

from .clipping_orchestrator import ClippingOrchestrator


class ClippingService:
    """Public service used by pipeline and API for clipping operations."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._orchestrator = ClippingOrchestrator()

    def export_project_clips(
        self,
        project_id: str,
        clips_with_titles_path: Path,
        collections_path: Path,
        input_video_path: str,
        output_dir: Path,
        clips_dir: str,
        collections_dir: str,
        metadata_dir: str,
    ) -> Dict[str, Any]:
        return self._orchestrator.export_project(
            clips_with_titles_path=clips_with_titles_path,
            collections_path=collections_path,
            input_video_path=input_video_path,
            output_dir=output_dir,
            clips_dir=clips_dir,
            collections_dir=collections_dir,
            metadata_dir=metadata_dir,
        )

    def sync_project(self, project_id: str, project_dir: Path) -> Dict[str, Any]:
        if self.db is None:
            raise ValueError("db session is required for sync_project")
        sync_service = DataSyncService(self.db)
        return sync_service.sync_project_from_filesystem(project_id, project_dir)
