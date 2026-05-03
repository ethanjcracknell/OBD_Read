"""
sources/live.py
---------------
Live OBD2 data source via python-obd + ELM327 USB adapter.

This implementation uses the configured serial port and baudrate to
open the adapter connection, then queries the key PIDs on each poll.
The blocking python-obd operations are executed in a thread so the
FastAPI event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import obd

from app.models import MetricPayload
from app.sources.base import DataSource

logger = logging.getLogger(__name__)


class LiveOBD2Source(DataSource):
    """Reads real PIDs from the vehicle via python-obd."""

    def __init__(self, serial_port: str, baudrate: int, reconnect_interval: float = 5.0) -> None:
        self._serial_port = serial_port
        self._baudrate = baudrate
        self._reconnect_interval = reconnect_interval
        self._connection: Optional[obd.OBD] = None
        self._last_reconnect_attempt = 0.0

    async def connect(self) -> None:
        """Open serial connection to the ELM327 adapter."""
        self._last_reconnect_attempt = asyncio.get_running_loop().time()
        await self._open_connection()

    async def read(self) -> MetricPayload:
        """Query vehicle metrics and return a MetricPayload."""
        if not self.is_connected:
            await self._attempt_reconnect()

        if self._connection is None:
            return MetricPayload(source="live")

        try:
            payload = await asyncio.to_thread(self._read_payload)
            return payload
        except Exception as exc:
            logger.warning("LiveOBD2Source: read failed: %s", exc)
            await self._attempt_reconnect()
            return MetricPayload(source="live")

    async def disconnect(self) -> None:
        """Close the serial connection."""
        if self._connection is None:
            return

        await asyncio.to_thread(self._connection.close)
        self._connection = None
        self._car_connected = False
        logger.info("LiveOBD2Source: disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and self._connection.status() != "Not Connected"

    async def _attempt_reconnect(self) -> None:
        now = asyncio.get_running_loop().time()
        if now - self._last_reconnect_attempt < self._reconnect_interval:
            return

        self._last_reconnect_attempt = now
        if self._connection is not None:
            try:
                await asyncio.to_thread(self._connection.close)
            except Exception:
                logger.debug("LiveOBD2Source: error closing stale connection")
            finally:
                self._connection = None

        await self._open_connection()

    async def _open_connection(self) -> None:
        try:
            self._connection = await asyncio.to_thread(
                obd.OBD,
                self._serial_port,
                baudrate=self._baudrate,
                fast=False,
            )
        except Exception as exc:
            self._connection = None
            logger.warning("LiveOBD2Source: adapter open failed on %s: %s", self._serial_port, exc)
            return

        if self._connection is None:
            logger.warning("LiveOBD2Source: failed to open OBD2 adapter on %s", self._serial_port)
            return

        if self._connection.status() == "Car Connected":
            logger.info("LiveOBD2Source: connected to car via %s", self._serial_port)
        elif self._connection.status() in ["ELM Connected", "OBD Connected"]:
            logger.warning(
                "LiveOBD2Source: adapter is present on %s, but no car connection was detected",
                self._serial_port,
            )
        else:
            logger.warning("LiveOBD2Source: connection status: %s", self._connection.status())

    @property
    def car_connected(self) -> bool:
        return self._connection is not None and self._connection.status() == "Car Connected"

    def _read_payload(self) -> MetricPayload:
        assert self._connection is not None

        # Test connection with a basic PID
        test_response = self._connection.query(obd.commands.PIDS_A)
        if test_response is None or test_response.is_null():
            raise Exception("Connection test failed")

        # Query all PIDs
        rpm = self._query_value(obd.commands.RPM)
        speed_kmh = self._query_value(obd.commands.SPEED, target_unit="km/h")
        coolant_temp_c = self._query_value(obd.commands.COOLANT_TEMP)
        throttle_pos = self._query_value(obd.commands.THROTTLE_POS)
        fuel_level = self._query_value(obd.commands.FUEL_LEVEL)
        intake_temp_c = self._query_value(obd.commands.INTAKE_TEMP)
        engine_load = self._query_value(obd.commands.ENGINE_LOAD)
        fuel_pressure = self._query_value(obd.commands.FUEL_PRESSURE)
        barometric_pressure = self._query_value(obd.commands.BAROMETRIC_PRESSURE)
        timing_advance = self._query_value(obd.commands.TIMING_ADVANCE)
        maf = self._query_value(obd.commands.MAF)
        o2_voltage = self._query_value(obd.commands.O2_S1S1)
        battery_voltage = self._query_value(obd.commands.ELM_VOLTAGE)

        return MetricPayload(
            rpm=int(rpm) if rpm is not None else None,
            speed_kmh=round(float(speed_kmh), 1) if speed_kmh is not None else None,
            coolant_temp_c=round(float(coolant_temp_c), 1) if coolant_temp_c is not None else None,
            throttle_pos=round(float(throttle_pos), 1) if throttle_pos is not None else None,
            fuel_level=round(float(fuel_level), 1) if fuel_level is not None else None,
            intake_temp_c=round(float(intake_temp_c), 1) if intake_temp_c is not None else None,
            engine_load=round(float(engine_load), 1) if engine_load is not None else None,
            fuel_pressure=round(float(fuel_pressure), 1) if fuel_pressure is not None else None,
            barometric_pressure=round(float(barometric_pressure), 1) if barometric_pressure is not None else None,
            timing_advance=round(float(timing_advance), 1) if timing_advance is not None else None,
            maf=round(float(maf), 1) if maf is not None else None,
            o2_voltage=round(float(o2_voltage), 2) if o2_voltage is not None else None,
            battery_voltage=round(float(battery_voltage), 1) if battery_voltage is not None else None,
            source="live",
        )

    def _query_value(self, command: obd.commands.__class__, target_unit: Optional[str] = None) -> Optional[float]:
        response = self._connection.query(command)
        if response is None or response.is_null() or response.value is None:
            return None

        value = response.value
        if target_unit is not None:
            try:
                return float(value.to(target_unit).magnitude)
            except Exception:
                pass

        try:
            return float(value.magnitude)
        except Exception:
            try:
                return float(value)
            except Exception:
                return None
