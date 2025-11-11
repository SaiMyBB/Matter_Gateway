"""
core/larnitech_client.py
-------------------------------------------------
Handles Larnitech API2 communication.
Supports both:
  - Remote (Bearer token over HTTPS)
  - Local LAN (password + serial)
"""

import os, time, json, requests, logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# --------------------------------------------------
# Load environment variables automatically
# --------------------------------------------------
load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------
LARNITECH_URL = os.getenv("LARNITECH_URL", "https://1876d100.in.larnitech.com:8443/api").rstrip("/")
LARNITECH_WS_URL = os.getenv("LARNITECH_WS_URL", "wss://1876d100.in.larnitech.com:8443/api")
LARNITECH_TOKEN = os.getenv("LARNITECH_TOKEN", None)
LARNITECH_PASSWORD = os.getenv("LARNITECH_PASSWORD", None)
LARNITECH_SERIAL = os.getenv("LARNITECH_SERIAL", None)
REQUEST_TIMEOUT = int(os.getenv("LARNITECH_TIMEOUT", 5))
MAX_RETRIES = int(os.getenv("LARNITECH_RETRIES", 3))

# --------------------------------------------------
# Logging Setup
# --------------------------------------------------
logger = logging.getLogger("larnitech_client")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [LarnitechClient] %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
def _headers() -> Dict[str, str]:
    """Return correct authentication headers for API2."""
    headers = {"Content-Type": "application/json"}
    if LARNITECH_TOKEN:
        # Token mode (remote HTTPS)
        headers["Authorization"] = f"{LARNITECH_TOKEN}"
    elif LARNITECH_PASSWORD:
        # Local LAN mode
        headers["e-passw"] = LARNITECH_PASSWORD
        if LARNITECH_SERIAL:
            headers["srv-serial"] = LARNITECH_SERIAL
    return headers


def _request(method: str, endpoint: str, **kwargs):
    """Perform request with retry and error handling."""
    url = f"{LARNITECH_URL}/{endpoint.lstrip('/')}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(f"{method.upper()} {url} (try {attempt})")
            res = requests.request(method, url, timeout=REQUEST_TIMEOUT, **kwargs)
            res.raise_for_status()
            return res
        except requests.RequestException as e:
            logger.warning(f"[Larnitech] Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(1.5 * attempt)
    logger.error(f"❌ Failed after {MAX_RETRIES} attempts: {url}")
    return None


# --------------------------------------------------
# API Functions
# --------------------------------------------------
def list_devices() -> Optional[Any]:
    """Fetch list of devices from Larnitech controller."""
    logger.info("Fetching Larnitech device list...")
    res = _request("GET", "device/list", headers=_headers())
    if not res:
        logger.error("Could not fetch device list.")
        return None
    try:
        data = res.json()
        logger.info(f"Fetched {len(data) if isinstance(data, list) else 'unknown'} devices.")
        return data
    except Exception as e:
        logger.error(f"JSON decode error: {e}")
        return None


def get_device_state(device_id: str) -> Optional[Dict[str, Any]]:
    """Get state of a specific device by ID."""
    res = _request("GET", f"device/get?id={device_id}", headers=_headers())
    if not res:
        return None
    try:
        return res.json()
    except Exception as e:
        logger.error(f"JSON parse error: {e}")
        return None


def set_device_state(device_id: str, value) -> bool:
    """Set a device state or value."""
    payload = {"id": device_id, "value": value}
    res = _request("POST", "device/set", json=payload, headers=_headers())
    if not res:
        logger.error(f"Failed to set device {device_id}")
        return False
    try:
        data = res.json()
        logger.info(f"✅ Device {device_id} updated successfully.")
        return data.get("result", True)
    except Exception as e:
        logger.error(f"Response parse error: {e}")
        return False


# --------------------------------------------------
# CLI Test Helper
# --------------------------------------------------
if __name__ == "__main__":
    print("🔧 Testing Larnitech API connection...")
    devices = list_devices()
    if devices:
        print(json.dumps(devices, indent=2))
    else:
        print("❌ No devices fetched. Check URL or token.")
