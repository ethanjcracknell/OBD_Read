"""
config.py
---------
Loads and validates config.toml at startup.
All other modules import from here — never read the file directly.
 
Supports Python 3.10 (tomllib backport) and 3.11+ (stdlib tomllib).
"""
 
from __future__ import annotations
 
import sys
from dataclasses import dataclass
from pathlib import Path
 
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib          # type: ignore[no-redef]
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]  # pip install tomli
 
 
_CONFIG_PATH = Path(__file__).parent.parent / "config.toml"
 
 
@dataclass
class AppConfig:
    mode: str           # "sim" | "live"
    port: int
 
 
@dataclass
class OBDConfig:
    serial_port: str
    baudrate: int
    poll_interval: float
    reconnect_interval: float = 5.0
 
 
@dataclass
class LoggingConfig:
    granularity: str    # "every_poll" | "fixed" | "summary"
    interval_seconds: float
    output_dir: str
 
 
@dataclass
class Config:
    app: AppConfig
    obd: OBDConfig
    logging: LoggingConfig
 
 
def load_config(path: Path = _CONFIG_PATH) -> Config:
    """
    Parse config.toml and return a validated Config object.
    Raises FileNotFoundError if the file is missing.
    Raises ValueError for unrecognised mode or granularity values.
    """
    with open(path, "rb") as f:
        raw = tomllib.load(f)
 
    app_cfg = AppConfig(
        mode=raw["app"]["mode"],
        port=raw["app"]["port"],
    )
 
    if app_cfg.mode not in ("sim", "live"):
        raise ValueError(f"config [app] mode must be 'sim' or 'live', got: {app_cfg.mode!r}")
 
    obd_cfg = OBDConfig(
        serial_port=raw["obd"]["serial_port"],
        baudrate=raw["obd"]["baudrate"],
        poll_interval=raw["obd"]["poll_interval"],
        reconnect_interval=raw["obd"].get("reconnect_interval", 5.0),
    )
 
    log_cfg = LoggingConfig(
        granularity=raw["logging"]["granularity"],
        interval_seconds=raw["logging"]["interval_seconds"],
        output_dir=raw["logging"]["output_dir"],
    )
 
    valid_granularities = ("every_poll", "fixed", "summary")
    if log_cfg.granularity not in valid_granularities:
        raise ValueError(
            f"config [logging] granularity must be one of {valid_granularities}, "
            f"got: {log_cfg.granularity!r}"
        )
 
    return Config(app=app_cfg, obd=obd_cfg, logging=log_cfg)
 