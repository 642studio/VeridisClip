"""Application orchestrator for clipping export."""

from pathlib import Path
from typing import Any, Dict

from backend.pipeline.step6_video import run_step6_video


class ClippingOrchestrator:
    """Orchestrates export stage for clip and collection videos."""

    def export_project(
        self,
        clips_with_titles_path: Path,
        collections_path: Path,
        input_video_path: str,
        output_dir: Path,
        clips_dir: str,
        collections_dir: str,
        metadata_dir: str,
    ) -> Dict[str, Any]:
        return run_step6_video(
            clips_with_titles_path,
            collections_path,
            input_video_path,
            output_dir=output_dir,
            clips_dir=clips_dir,
            collections_dir=collections_dir,
            metadata_dir=metadata_dir,
        )
