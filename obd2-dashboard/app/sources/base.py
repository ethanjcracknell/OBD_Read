"""
sources/base.py
---------------
Abstract base class that every data source must implement.
 
poller.py depends only on this interface, so swapping SimSource for 
LiveOBD2Source requires zero changes to any other module.
"""
 
from __future__ import annotations
 
from abc import ABC, abstractmethod
from app.models import MetricPayload
 
 
class DataSource(ABC):
    """
    Contract for all vehicle data providers.
 
    Concrete implementations: SimSource, LiveOBD2Source.
    """
 
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish data source connection.
        Called once at application startup, before polling loop begins.
        Raises an exception on failure so app can exit cleanly.
        """
        ...
 
    @abstractmethod
    async def read(self) -> MetricPayload:
        """
        Read one snapshot of vehicle metrics.
        Called repeatedly by the polling loop at the configured interval.
        Must return a MetricPayload; use None fields for unavailable PIDs.
        Should not raise — catch internal errors and return partial data.
        """
        ...
 
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Tear down the connection gracefully.
        Called on application shutdown (FastAPI lifespan cleanup).
        """
        ...
 
    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True if the source currently has an active connection."""
        ...