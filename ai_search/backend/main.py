"""
Main Backend Entry Point
Run this to start the AI Search Engine backend server
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os
import uvicorn

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables from .env
load_dotenv()

# Get values from .env with defaults
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 8000))
BACKEND_LOG_LEVEL = os.getenv("BACKEND_LOG_LEVEL", "info")

# Import the FastAPI app
from backend.api.server import app

if __name__ == "__main__":
    print("🚀 Starting AI Search Engine Backend Server...")
    print(f"📍 Server URL: http://{BACKEND_HOST}:{BACKEND_PORT}")
    print(f"📖 API Docs: http://{BACKEND_HOST}:{BACKEND_PORT}/api/docs")
    print(f"🌐 Frontend: http://localhost:3000")
    print("=" * 60)
    
    uvicorn.run(
        app,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level=BACKEND_LOG_LEVEL.lower(),
        access_log=True
    )
