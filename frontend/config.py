"""Frontend configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "30"))
APP_TITLE = "Brand Intel Monitor"
