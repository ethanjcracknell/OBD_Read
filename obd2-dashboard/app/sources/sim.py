"""
sources/sim.py
--------------
Simulated data source — no hardware required.
 
Phase 1: returns plausible static values so the rest of the
stack (WebSocket broadcast, CSV logger, frontend rendering)
can be developed and tested end-to-end before the ELM327
adapter is available.
 
Phase 2 (TODO): replace static values with a realistic driving
pattern — sine wave for RPM, correlated speed, temp warm-up
curve, etc. The interface stays identical.
"""
 
from __future__ import annotations
 
import logging
import math
import time
 
from app.models import MetricPayload
from app.sources.base import DataSource
 
logger = logging.getLogger(__name__)
 
 
class SimSource(DataSource):
    """
    Simulated vehicle data source.
    """
 
    def __init__(self) -> None:
        self._connected = False
        self._start = time.time()
 
    async def connect(self) -> None:
        """No real connection needed; just flip the flag."""
        logger.info("SimSource: connected (dynamic simulated data)")
        self._connected = True
 
    async def read(self) -> MetricPayload:
        """Return a dynamic MetricPayload that oscillates like a warm engine."""
        elapsed = time.time() - self._start
        rpm = int(850 + 420 * math.sin(elapsed / 4.0) + 120 * math.sin(elapsed / 1.7))
        rpm = max(700, min(2600, rpm))
 
        speed_kmh = float(max(0.0, min(120.0, 0.08 * (rpm - 700) + 4.0 * math.sin(elapsed / 3.5))))
        coolant_temp_c = float(85.0 + min(15.0, elapsed / 40.0) + 2.0 * math.sin(elapsed / 25.0))
        throttle_pos = float(max(1.0, min(25.0, 1.5 + 0.01 * (rpm - 700) + 4.0 * math.sin(elapsed / 2.0))))
        
        # Simulate additional metrics
        fuel_level = float(max(10.0, min(95.0, 75.0 - 0.1 * elapsed + 5.0 * math.sin(elapsed / 60.0))))
        intake_temp_c = float(coolant_temp_c + 15.0 + 5.0 * math.sin(elapsed / 8.0))
        engine_load = float(max(10.0, min(90.0, 25.0 + 0.02 * (rpm - 700) + 15.0 * math.sin(elapsed / 5.0))))
        fuel_pressure = float(max(250.0, min(450.0, 350.0 + 20.0 * math.sin(elapsed / 12.0))))
        barometric_pressure = float(101.3 + 2.0 * math.sin(elapsed / 30.0))  # kPa
        timing_advance = float(max(-5.0, min(45.0, 15.0 + 10.0 * math.sin(elapsed / 6.0))))
        maf = float(max(2.0, min(50.0, 8.0 + 0.05 * (rpm - 700) + 5.0 * math.sin(elapsed / 4.0))))
        o2_voltage = float(max(0.1, min(0.9, 0.45 + 0.2 * math.sin(elapsed / 3.0))))
        battery_voltage = float(max(12.0, min(14.8, 13.8 + 0.3 * math.sin(elapsed / 20.0))))

        return MetricPayload(
            rpm=rpm,
            speed_kmh=round(speed_kmh, 1),
            coolant_temp_c=round(coolant_temp_c, 1),
            throttle_pos=round(throttle_pos, 1),
            fuel_level=round(fuel_level, 1),
            intake_temp_c=round(intake_temp_c, 1),
            engine_load=round(engine_load, 1),
            fuel_pressure=round(fuel_pressure, 1),
            barometric_pressure=round(barometric_pressure, 1),
            timing_advance=round(timing_advance, 1),
            maf=round(maf, 1),
            o2_voltage=round(o2_voltage, 2),
            battery_voltage=round(battery_voltage, 1),
            source="sim",
        )
