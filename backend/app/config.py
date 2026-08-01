import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root or current directory
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
