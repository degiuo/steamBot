import logging
from datetime import datetime
from pathlib import Path

def setup_logger(bot_name: str) -> logging.Logger:
    log_dir = Path(f"logs/{bot_name}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(bot_name)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = logging.FileHandler(log_dir / f"{datetime.now().date()}.log")
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    return logger