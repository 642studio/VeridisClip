"""Metadata IO for clipping artifacts."""

import json
from pathlib import Path
from typing import Any, Dict, List


class ClippingMetadataRepository:
    """Repository for clipping metadata files under project metadata dir."""

    def __init__(self, metadata_dir: Path):
        self.metadata_dir = metadata_dir
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def read_clips(self) -> List[Dict[str, Any]]:
        return self._read_json(self.metadata_dir / "clips_metadata.json")

    def read_collections(self) -> List[Dict[str, Any]]:
        return self._read_json(self.metadata_dir / "collections_metadata.json")

    def write_clips(self, payload: List[Dict[str, Any]]) -> Path:
        return self._write_json(self.metadata_dir / "clips_metadata.json", payload)

    def write_collections(self, payload: List[Dict[str, Any]]) -> Path:
        return self._write_json(self.metadata_dir / "collections_metadata.json", payload)

    def _read_json(self, path: Path):
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []

    def _write_json(self, path: Path, payload: List[Dict[str, Any]]) -> Path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path
