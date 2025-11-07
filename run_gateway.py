import sys
import os

# --- Ensure project root is in sys.path ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from api.rest_api import app
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Matter Gateway on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
