"""
models.py
---------
Shared data structures used across the entire application.
Every component that produces or consumes vehicle metrics
uses MetricPayload as the canonical contract.
"""
 
from __future__ import annotations
 
import time
from dataclasses import dataclass, asdict
 
 
@dataclass
class MetricPayload:
    """
    A single snapshot of vehicle telemetry.
 
    All fields are Optional so a live source can return partial
    data when a PID is unsupported or temporarily unavailable.
    None values are serialised as null in the JSON sent to the
    browser, and the frontend renders them as "—".
 
    Units
    -----
    rpm                 : revolutions per minute   (int)
    speed_kmh           : kilometres per hour      (float)
    coolant_temp_c      : degrees Celsius          (float)
    throttle_pos        : 0.0–100.0 percent        (float)
    fuel_level          : 0.0–100.0 percent        (float)
    intake_temp_c       : degrees Celsius          (float)
    engine_load         : 0.0–100.0 percent        (float)
    fuel_pressure       : kilopascals              (float)
    barometric_pressure : kilopascals              (float)
    timing_advance      : degrees                  (float)
    maf                 : grams per second         (float)
    o2_voltage          : volts                    (float)
    battery_voltage     : volts                    (float)
    timestamp           : Unix epoch seconds       (float)
    source              : "sim" | "live"
    """

    rpm: int | None = None
    speed_kmh: float | None = None
    coolant_temp_c: float | None = None
    throttle_pos: float | None = None
    fuel_level: float | None = None
    intake_temp_c: float | None = None
    engine_load: float | None = None
    fuel_pressure: float | None = None
    barometric_pressure: float | None = None
    timing_advance: float | None = None
    maf: float | None = None
    o2_voltage: float | None = None
    battery_voltage: float | None = None
    timestamp: float | None = None
    source: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization and CSV writing."""
        return asdict(self)
 