# =============================================================================
#  OPS PLATFORM — SHARED ACTIVITY LOGGER
#  common/logger.py
#
#  DO NOT MODIFY — this is a shared file used by all modules.
#
#  Provides a consistent rotating file logger for all platform modules.
#  Log files are written to:  <project_root>/logs/<module_name>.log
#
#  The project root is auto-detected as the parent of the "common" folder,
#  so logs always land inside the running ops-platform directory regardless
#  of where the app is installed or which user runs it.
#
#  Usage (matches DCN Analytics pattern):
#      from common.logger import setup_logger
#      logger = setup_logger("operations_center")
#      logger.info("Dashboard loaded")
#      logger.warning("File not found")
#      logger.error("Failed", exc_info=True)
#
#  Log file: <project_root>/logs/<module_name>.log
#  Rotation: 5 MB × 7 backups
# =============================================================================

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Resolve project-relative logs directory ───────────────────────────────────
# __file__ = <project_root>/common/logger.py
# .parent   = <project_root>/common/
# .parent.parent = <project_root>/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR     = _PROJECT_ROOT / "logs"

# Rotation settings
_MAX_BYTES    = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 7                  # keep 7 rotated backups

# Internal cache: one logger instance per module name
_loggers: dict = {}


def setup_logger(module_name: str) -> logging.Logger:
    """
    Return a named logger for the given module (DCN Analytics compatible API).

    Creates and configures on first call; returns cached instance on repeat
    calls — safe to call multiple times from different files.

    Log file location: <project_root>/logs/<module_name>.log

    Args:
        module_name: Short identifier e.g. "operations_center",
                     "windchill_monitoring", "dcn_analytics".

    Returns:
        Configured logging.Logger writing to file + console.
    """
    if module_name in _loggers:
        return _loggers[module_name]

    # ── Ensure log directory exists ───────────────────────────────────────────
    try:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # Cannot create directory — fall back to console-only logger
        fallback = logging.getLogger(module_name)
        fallback.setLevel(logging.DEBUG)
        if not fallback.handlers:
            fallback.addHandler(logging.StreamHandler())
        fallback.warning(f"[Logger] Cannot create log directory {_LOGS_DIR}: {e}")
        _loggers[module_name] = fallback
        return fallback

    log_file = _LOGS_DIR / f"{module_name}.log"

    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers on Flask hot-reload
    if logger.handlers:
        _loggers[module_name] = logger
        return logger

    # Shared format: timestamp [LEVEL] module_name — message
    fmt = logging.Formatter(
        fmt     = "%(asctime)s [%(levelname)-5s] %(name)s — %(message)s",
        datefmt = "%Y-%m-%d %H:%M:%S"
    )

    # ── Rotating file handler ─────────────────────────────────────────────────
    try:
        fh = RotatingFileHandler(
            filename    = str(log_file),
            maxBytes    = _MAX_BYTES,
            backupCount = _BACKUP_COUNT,
            encoding    = "utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as e:
        logger.warning(f"[Logger] Cannot open log file {log_file}: {e}")

    # ── Console handler (INFO+) ───────────────────────────────────────────────
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Prevent propagation to root logger (avoids duplicate console output)
    logger.propagate = False

    _loggers[module_name] = logger
    logger.info(f"Logger started → {log_file}")
    return logger
