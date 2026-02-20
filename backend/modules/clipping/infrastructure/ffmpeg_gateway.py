"""FFmpeg gateway wrapper for clipping operations."""

from pathlib import Path
from typing import Dict, List

from backend.utils.video_processor import VideoProcessor


class FfmpegGateway:
    """Adapter over VideoProcessor to isolate ffmpeg usage."""

    def __init__(self, clips_dir: str, collections_dir: str):
        self._processor = VideoProcessor(clips_dir=clips_dir, collections_dir=collections_dir)

    def extract_batch(self, input_video: Path, clips_data: List[Dict]) -> List[Path]:
        return self._processor.batch_extract_clips(input_video, clips_data)

    def build_collection(self, clip_paths: List[Path], output_path: Path) -> bool:
        return self._processor.create_collection(clip_paths, output_path)
