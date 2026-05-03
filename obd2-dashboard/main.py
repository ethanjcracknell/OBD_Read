"""
main.py
-------
Entry point. Run with:
 
    python main.py
 
This creates the FastAPI application and starts uvicorn programmatically
so port, log level, and reload settings live here rather than in a CLI call.
 
For development with auto-reload:
    uvicorn app.api:create_app --factory --reload --port 8080
"""
 
import logging
import uvicorn
 
from app.config import load_config
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
 
if __name__ == "__main__":
    cfg = load_config()
    uvicorn.run(
        "app.api:create_app",
        factory=True,
        host="127.0.0.1",
        port=cfg.app.port,
        log_level="info",
        reload=False,      # flip to True during active frontend development
    )