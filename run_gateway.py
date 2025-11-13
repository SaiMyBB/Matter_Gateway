# run_gateway.py
"""
Main launcher for the Matter Gateway WebSocket API.
Handles:
 - Environment loading
 - Port fallback logic
 - Clean startup output
 - Uvicorn server boot
"""

import uvicorn
import sys
import os
import socket
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Import FastAPI app
from api.websocket_api import app


# ----------------------------------------------------
# Port Selection with Fallback
# ----------------------------------------------------
def find_open_port(preferred_ports=[8000, 8080, 9000]):
    """Return the first available port from list; fallback to random."""
    for port in preferred_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("0.0.0.0", port)) != 0:
                return port
    # fallback to random OS-assigned port
    return 0


# ----------------------------------------------------
# Main Entry
# ----------------------------------------------------
if __name__ == "__main__":
    print("========================================================")
    print(" 🚀 Matter Gateway — Starting WebSocket API Server")
    print("========================================================")

    # Show important environment configuration
    print("📡 Larnitech API URL:", os.getenv("LARNITECH_URL", "NOT SET"))
    print("🔐 Auth Mode:", "TOKEN" if os.getenv("LARNITECH_TOKEN") else 
                         "LAN PASSWORD" if os.getenv("LARNITECH_PASSWORD") else
                         "NONE (using fallback)")
    print("📦 Dashboard:     http://localhost:8000 (or chosen port)")

    # Determine port
    port = find_open_port()
    if port != 8000:
        print(f"⚠️ Port 8000 unavailable. Using port {port} instead.")

    print("--------------------------------------------------------")
    print(f"🌐 Starting server on: http://0.0.0.0:{port}")
    print("--------------------------------------------------------")

    # Launch uvicorn — disable reload to avoid double tasks on macOS
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,   # important: prevents double-spawning sensor tasks
    )
