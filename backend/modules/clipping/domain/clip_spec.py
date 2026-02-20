"""Clip domain specification."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClipSpec:
    """Canonical clip shape used by clipping services."""

    clip_id: str
    title: str
    start_time: str
    end_time: str

    def validate(self) -> None:
        if not self.clip_id:
            raise ValueError("clip_id is required")
        if not self.start_time or not self.end_time:
            raise ValueError("start_time and end_time are required")
