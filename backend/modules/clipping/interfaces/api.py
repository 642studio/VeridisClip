"""Clipping module HTTP endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.path_utils import get_project_directory
from backend.modules.clipping.application.clipping_service import ClippingService
from backend.modules.clipping.infrastructure.metadata_repository import ClippingMetadataRepository

router = APIRouter(prefix="/clipping", tags=["clipping"])


@router.get("/projects/{project_id}/summary")
def get_clipping_summary(project_id: str):
    project_dir = get_project_directory(project_id)
    metadata_repo = ClippingMetadataRepository(project_dir / "metadata")

    clips = metadata_repo.read_clips()
    collections = metadata_repo.read_collections()

    return {
        "project_id": project_id,
        "clips_count": len(clips),
        "collections_count": len(collections),
        "clips_metadata_path": str(project_dir / "metadata" / "clips_metadata.json"),
        "collections_metadata_path": str(project_dir / "metadata" / "collections_metadata.json"),
    }


@router.post("/projects/{project_id}/sync")
def sync_clipping_to_database(project_id: str, db: Session = Depends(get_db)):
    project_dir = get_project_directory(project_id)
    if not Path(project_dir).exists():
        raise HTTPException(status_code=404, detail="project directory not found")

    service = ClippingService(db=db)
    result = service.sync_project(project_id, project_dir)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "sync failed"))

    return result
