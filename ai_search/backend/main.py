"""
Main Backend Entry Point
Run this to start the AI Search Engine backend server
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import and run the server
from backend.api.server import app
import uvicorn
from common.config import BACKEND_HOST, BACKEND_PORT, BACKEND_LOG_LEVEL

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
