"""Clipping policy constraints."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ClipPolicy:
    """Execution limits for clipping export."""

    min_clips_per_collection: int = 2
    max_clips_per_collection: int = 5

    def validate(self) -> None:
        if self.min_clips_per_collection < 1:
            raise ValueError("min_clips_per_collection must be >= 1")
        if self.max_clips_per_collection < self.min_clips_per_collection:
            raise ValueError("max_clips_per_collection must be >= min_clips_per_collection")
