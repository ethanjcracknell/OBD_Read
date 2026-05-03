"""
poller.py
---------
The asyncio background task that drives the entire data pipeline.
 
Responsibilities
----------------
1. Call source.read() at the configured poll_interval.
2. Broadcast the MetricPayload to all connected WebSocket clients
   via the ConnectionManager in api.py.
3. Hand the payload to the SessionLogger.
4. Handle per-cycle errors without crashing the loop.
 
The loop runs as a FastAPI background task (asyncio.Task) created
inside the lifespan context manager in api.py.
"""
 
from __future__ import annotations
 
import asyncio
import logging
 
from app.models import MetricPayload
from app.sources.base import DataSource
from app.config import OBDConfig
 
logger = logging.getLogger(__name__)
 
 
class Poller:
    """
    Wraps the polling loop and holds references to the source,
    connection manager, and session logger.
 
    Usage (inside FastAPI lifespan):
        poller = Poller(source, manager, session_logger, cfg.obd)
        task = asyncio.create_task(poller.run())
        ...
        poller.stop()
        await task
    """
 
    def __init__(self, source: DataSource, manager, session_logger, obd_cfg: OBDConfig) -> None:
        # 'manager' typed as Any here to avoid circular import with api.py.
        # At runtime it is a ConnectionManager instance.
        self._source = source
        self._manager = manager
        self._logger = session_logger
        self._interval = obd_cfg.poll_interval
        self._running = False
 
    async def run(self) -> None:
        """
        Main polling loop. Runs until stop() is called.
 
        Error strategy
        --------------
        - Errors from source.read() are caught and logged; the loop continues.
        - Three consecutive failures trigger a warning; ten trigger an error.
        - The loop never raises — it exits cleanly when self._running is False.
        """
        self._running = True
        consecutive_failures = 0
        logger.info("Poller: starting (interval=%.2fs)", self._interval)
 
        while self._running:
            loop_start = asyncio.get_event_loop().time()
 
            try:
                payload: MetricPayload = await self._source.read()
                consecutive_failures = 0
 
                # Broadcast to all WebSocket clients
                await self._manager.broadcast(payload)
 
                # Write to CSV
                self._logger.log(payload)
 
            except Exception as exc:
                consecutive_failures += 1
                if consecutive_failures == 3:
                    logger.warning("Poller: 3 consecutive read failures: %s", exc)
                elif consecutive_failures == 10:
                    logger.error("Poller: 10 consecutive read failures — check adapter connection")
                else:
                    logger.debug("Poller: read error: %s", exc)
 
            # Drift-compensated sleep: subtract how long the read took
            elapsed = asyncio.get_event_loop().time() - loop_start
            sleep_time = max(0.0, self._interval - elapsed)
            await asyncio.sleep(sleep_time)
 
        logger.info("Poller: stopped")
 
    def stop(self) -> None:
        """Signal the loop to exit after the current iteration."""
        self._running = False
 