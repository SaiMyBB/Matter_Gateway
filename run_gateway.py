# run_gateway.py
import uvicorn
import sys
import os
from api.websocket_api import app
from dotenv import load_dotenv
load_dotenv()


# --- Ensure project root is in sys.path ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

if __name__ == "__main__":
    try:
        print("🚀 Starting Matter Gateway (WebSocket API) on http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except OSError:
        print("⚠️ Port 8000 busy, switching to 8080...")
        uvicorn.run(app, host="0.0.0.0", port=8080)
