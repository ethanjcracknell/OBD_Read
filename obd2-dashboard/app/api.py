"""
api.py
------
FastAPI application definition.
 
Provides:
  GET  /status        — JSON health check (source mode, connection state)
  WS   /ws            — WebSocket endpoint; pushes MetricPayload JSON to clients
  GET  /              — serves frontend/index.html (via StaticFiles mount)
 
The polling loop (Poller) is started inside the lifespan context manager
so it runs for the lifetime of the server and shuts down cleanly on SIGINT.
 
StaticFiles is mounted AFTER route definitions to avoid it intercepting /ws.
"""
 
from __future__ import annotations
 
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Set
 
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
 
from app.config import load_config
from app.models import MetricPayload
from app.sources.sim import SimSource
from app.sources.live import LiveOBD2Source
from app.sources.base import DataSource
from app.logger import SessionLogger
from app.poller import Poller
 
logger = logging.getLogger(__name__)
 
# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
 
class ConnectionManager:
    """Tracks all active WebSocket connections and broadcasts to all of them."""
 
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
 
    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        logger.info("WebSocket client connected (total: %d)", len(self._clients))
 
    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)
        logger.info("WebSocket client disconnected (total: %d)", len(self._clients))
 
    async def broadcast(self, payload: MetricPayload) -> None:
        """Send payload as JSON to all connected clients. Drop dead connections."""
        if not self._clients:
            return
        message = json.dumps(payload.to_dict())
        dead: Set[WebSocket] = set()
        for client in self._clients:
            try:
                await client.send_text(message)
            except Exception:
                dead.add(client)
        for client in dead:
            self._clients.discard(client)
 
    @property
    def client_count(self) -> int:
        return len(self._clients)
 
 
# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
 
def create_app() -> FastAPI:
    cfg = load_config()
 
    # Select data source based on config
    source: DataSource
    if cfg.app.mode == "sim":
        source = SimSource()
    else:
        source = LiveOBD2Source(
            serial_port=cfg.obd.serial_port,
            baudrate=cfg.obd.baudrate,
            reconnect_interval=cfg.obd.reconnect_interval,
        )
 
    session_logger = SessionLogger(cfg.logging)
    manager = ConnectionManager()
    poller: Poller | None = None
    poller_task: asyncio.Task | None = None
    recording_active = False

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal poller, poller_task
        # --- startup ---
        await source.connect()
        # Don't start recording automatically - wait for manual start
        logger.info("Application started in %r mode on port %d", cfg.app.mode, cfg.app.port)
        yield
        # --- shutdown ---
        if poller:
            poller.stop()
        if poller_task:
            await poller_task
        await source.disconnect()
        session_logger.close()
        logger.info("Application shut down cleanly")
 
    app = FastAPI(title="OBD2 Dashboard", lifespan=lifespan)
 
    # --- Routes ---
 
    @app.get("/status")
    async def status():
        status_payload = {
            "mode": cfg.app.mode,
            "source_connected": source.is_connected,
            "adapter_connected": source.is_connected,
            "recording_active": recording_active,
            "ws_clients": manager.client_count,
        }
        if cfg.app.mode == "live":
            status_payload["car_connected"] = source.car_connected
        return status_payload

    @app.post("/recording/start")
    async def start_recording():
        nonlocal poller, poller_task, recording_active
        if recording_active:
            return {"message": "Recording already active"}
        
        try:
            session_logger.open()
            poller = Poller(source, manager, session_logger, cfg.obd)
            poller_task = asyncio.create_task(poller.run())
            recording_active = True
            logger.info("Recording started")
            return {"message": "Recording started"}
        except Exception as e:
            logger.error("Failed to start recording: %s", e)
            return {"message": "Failed to start recording", "error": str(e)}

    @app.post("/recording/stop")
    async def stop_recording():
        nonlocal poller, poller_task, recording_active
        if not recording_active:
            return {"message": "Recording not active"}
        
        try:
            if poller:
                poller.stop()
            if poller_task:
                await poller_task
            session_logger.close()
            poller = None
            poller_task = None
            recording_active = False
            logger.info("Recording stopped")
            return {"message": "Recording stopped"}
        except Exception as e:
            logger.error("Failed to stop recording: %s", e)
            return {"message": "Failed to stop recording", "error": str(e)}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                # Keep connection alive, data is pushed via broadcast()
                await websocket.receive_text()
        except WebSocketDisconnect:
            manager.disconnect(websocket)

    @app.get("/history")
    async def history(limit: int = 1000):
        """Return recent historical data from CSV logs."""
        import csv
        from pathlib import Path
        from datetime import datetime
        
        logs_dir = Path(cfg.logging.output_dir)
        if not logs_dir.exists():
            return {"sessions": []}
        
        sessions = []
        csv_files = sorted(logs_dir.glob("session_*.csv"), reverse=True)
        
        for csv_file in csv_files[:10]:  # Last 10 sessions
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    data = list(reader)
                    
                    # Skip empty sessions
                    if not data:
                        continue
                    
                    # Convert string values to appropriate types
                    for row in data:
                        for key, value in row.items():
                            if key == 'timestamp':
                                row[key] = float(value) if value else None
                            elif key in ['rpm']:
                                row[key] = int(float(value)) if value else None
                            elif key in ['speed_kmh', 'coolant_temp_c', 'throttle_pos', 
                                       'fuel_level', 'intake_temp_c', 'engine_load', 
                                       'fuel_pressure', 'barometric_pressure', 'timing_advance', 
                                       'maf', 'o2_voltage', 'battery_voltage']:
                                row[key] = float(value) if value else None
                    
                    # Create readable title from timestamp
                    session_timestamp = csv_file.stat().st_mtime
                    dt = datetime.fromtimestamp(session_timestamp)
                    readable_title = dt.strftime("%B %d, %Y at %I:%M %p")
                    
                    sessions.append({
                        "title": readable_title,
                        "filename": csv_file.name,
                        "timestamp": session_timestamp,
                        "data": data[-limit:] if len(data) > limit else data
                    })
            except Exception as e:
                logger.warning("Failed to read %s: %s", csv_file, e)
                continue
        
        # Sort by timestamp (most recent first)
        sessions.sort(key=lambda s: s["timestamp"], reverse=True)
        
        return {"sessions": sessions}

    # --- Static files (must be mounted AFTER routes) ---
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if frontend_dir.exists():
        app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
    else:
        @app.get("/")
        async def root():
            return {
                "message": "Frontend not built. Run npm install && npm run build in frontend/.",
                "help": "Build the React app before running main.py.",
            }
 
    return app
