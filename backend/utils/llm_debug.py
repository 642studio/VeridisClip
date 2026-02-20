"""
LLM debug helpers.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ..core.path_utils import get_data_directory, get_settings_file_path

logger = logging.getLogger(__name__)

_TRUE_VALUES = {"1", "true", "yes", "on"}


def is_llm_debug_enabled() -> bool:
    """
    Enable order:
    1) AUTOCLIP_LLM_DEBUG env var
    2) data/settings.json key llm_debug
    """
    env_value = os.getenv("AUTOCLIP_LLM_DEBUG", "").strip().lower()
    if env_value:
        return env_value in _TRUE_VALUES

    try:
        settings_file = get_settings_file_path()
        if settings_file.exists():
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return bool(settings.get("llm_debug", False))
    except Exception as exc:
        logger.warning(f"No se pudo leer llm_debug desde settings: {exc}")

    return False


def _get_llm_debug_dir() -> Path:
    debug_dir = get_data_directory() / "logs" / "llm_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def summarize_text(value: Any, limit: int = 600) -> str:
    text = str(value)
    return text if len(text) <= limit else f"{text[:limit]}...(truncated, len={len(text)})"


def write_llm_debug_event(event_type: str, payload: Dict[str, Any]) -> None:
    if not is_llm_debug_enabled():
        return

    try:
        debug_dir = _get_llm_debug_dir()
        line = {
            "ts": datetime.utcnow().isoformat(),
            "event": event_type,
            **payload,
        }
        log_file = debug_dir / "events.jsonl"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False))
            f.write("\n")
    except Exception as exc:
        logger.warning(f"No se pudo escribir evento LLM debug: {exc}")


def write_llm_debug_blob(prefix: str, content: str) -> Optional[Path]:
    if not is_llm_debug_enabled():
        return None
    try:
        debug_dir = _get_llm_debug_dir()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        blob_path = debug_dir / f"{prefix}_{timestamp}.txt"
        with open(blob_path, "w", encoding="utf-8") as f:
            f.write(content)
        return blob_path
    except Exception as exc:
        logger.warning(f"No se pudo escribir blob LLM debug: {exc}")
        return None
