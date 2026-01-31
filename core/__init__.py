"""Core module initialization"""
# Don't import signal_engine here to avoid circular dependency
from .binance_client import binance_client
from .websocket_handler import ws_handler
from .indicators import indicators

__all__ = [
    "binance_client",
    "ws_handler", 
    "indicators"
]