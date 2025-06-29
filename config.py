import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    STEAM_API_KEY = os.getenv("STEAM_API_KEY")
    PROXY = os.getenv("PROXY")  # "http://user:pass@ip:port"
    LOGS_BACKUP_DIR = "backups/logs"