"""
Utility functions and helpers
"""
import json
import logging
from typing import Any, Dict
from datetime import datetime
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup structured JSON logging"""
    class JSONFormatter(logging.Formatter):
        """Custom JSON formatter for structured logging"""
        
        def format(self, record: logging.LogRecord) -> str:
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_data)
    
    json_formatter = JSONFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def validate_environment() -> Dict[str, Any]:
    """Validate environment variables and configuration"""
    from config.settings import settings
    
    issues = []
    warnings = []
    
    if not settings.BINANCE_API_KEY:
        issues.append("BINANCE_API_KEY not set")
    
    if not settings.BINANCE_SECRET:
        issues.append("BINANCE_SECRET not set")
    
    if not settings.TELEGRAM_BOT_TOKEN:
        issues.append("TELEGRAM_BOT_TOKEN not set")
    
    if not settings.TELEGRAM_CHAT_ID:
        issues.append("TELEGRAM_CHAT_ID not set")
    
    if not settings.DATABASE_URL:
        issues.append("DATABASE_URL not set")
    
    if settings.BINANCE_TESTNET:
        warnings.append("Running in TESTNET mode")
    
    if settings.RISK_PER_TRADE > 0.05:
        warnings.append(f"High risk per trade: {settings.RISK_PER_TRADE*100}%")
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings
    }
