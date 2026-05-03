"""
logger.py
---------
Writes vehicle metrics to a session-scoped CSV file.
 
A new file is created each time the application starts,
named with an ISO-8601 timestamp so sessions are easy to find.
 
Granularity is controlled by config.toml [logging] granularity:
  "every_poll"  — write on every call to log()
  "fixed"       — write at most once per interval_seconds
  "summary"     — buffer all readings; write min/max/avg on close()
 
The poller calls log() after each successful read().
"""
 
from __future__ import annotations
 
import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
 
from app.config import LoggingConfig
from app.models import MetricPayload
 
logger = logging.getLogger(__name__)
 
_CSV_FIELDS = [
    "timestamp", "source", "rpm", "speed_kmh", "coolant_temp_c", "throttle_pos",
    "fuel_level", "intake_temp_c", "engine_load", "fuel_pressure", 
    "barometric_pressure", "timing_advance", "maf", "o2_voltage", "battery_voltage"
]
 
 
class SessionLogger:
    """
    Manages one CSV file per application session.
    Thread-safe for single-threaded asyncio use (no locks needed).
    """
 
    def __init__(self, cfg: LoggingConfig) -> None:
        self._cfg = cfg
        self._file = None
        self._writer: Optional[csv.DictWriter] = None
        self._last_write: float = 0.0
        self._buffer: list[MetricPayload] = []
        self._path: Optional[Path] = None
        self._row_count: int = 0
 
    def open(self) -> None:
        """Create the output directory and open a new CSV file for this session."""
        out_dir = Path(self._cfg.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
 
        session_ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        self._path = out_dir / f"session_{session_ts}.csv"
 
        self._file = open(self._path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=_CSV_FIELDS)
        self._writer.writeheader()
        logger.info("SessionLogger: writing to %s", self._path)
 
    def log(self, payload: MetricPayload) -> None:
        """
        Conditionally write payload to CSV based on configured granularity.
        Call this from the polling loop after every successful read().
        """
        if self._writer is None:
            return
 
        granularity = self._cfg.granularity
 
        if granularity == "every_poll":
            self._write_row(payload)
 
        elif granularity == "fixed":
            now = time.monotonic()
            if now - self._last_write >= self._cfg.interval_seconds:
                self._write_row(payload)
                self._last_write = now
 
        elif granularity == "summary":
            self._buffer.append(payload)
 
    def close(self) -> None:
        """Flush any buffered data and close the CSV file."""
        if self._cfg.granularity == "summary" and self._buffer:
            self._write_summary()
 
        if self._file:
            self._file.flush()
            self._file.close()
            logger.info("SessionLogger: closed %s (%d rows)", self._path, self._row_count)
 
    def _write_row(self, payload: MetricPayload) -> None:
        assert self._writer is not None
        self._writer.writerow(payload.to_dict())
        self._row_count += 1
 
    def _write_summary(self) -> None:
        """Write one summary row per metric: min, max, avg across the session buffer."""
        if not self._buffer:
            return
 
        assert self._writer is not None
 
        def _stats(values: list[Optional[float]]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
            clean = [v for v in values if v is not None]
            if not clean:
                return None, None, None
            return min(clean), max(clean), round(sum(clean) / len(clean), 2)
 
        rows = []
        rows.append({
            "timestamp": "summary_min",
            "source": "summary",
            "rpm": _stats([p.rpm for p in self._buffer])[0],
            "speed_kmh": _stats([p.speed_kmh for p in self._buffer])[0],
            "coolant_temp_c": _stats([p.coolant_temp_c for p in self._buffer])[0],
            "throttle_pos": _stats([p.throttle_pos for p in self._buffer])[0],
        })
        rows.append({
            "timestamp": "summary_max",
            "source": "summary",
            "rpm": _stats([p.rpm for p in self._buffer])[1],
            "speed_kmh": _stats([p.speed_kmh for p in self._buffer])[1],
            "coolant_temp_c": _stats([p.coolant_temp_c for p in self._buffer])[1],
            "throttle_pos": _stats([p.throttle_pos for p in self._buffer])[1],
        })
        rows.append({
            "timestamp": "summary_avg",
            "source": "summary",
            "rpm": _stats([p.rpm for p in self._buffer])[2],
            "speed_kmh": _stats([p.speed_kmh for p in self._buffer])[2],
            "coolant_temp_c": _stats([p.coolant_temp_c for p in self._buffer])[2],
            "throttle_pos": _stats([p.throttle_pos for p in self._buffer])[2],
        })
 
        for row in rows:
            self._writer.writerow(row)
            self._row_count += 1
