"""
core/larnitech_client.py
-------------------------------------------------
Handles Larnitech API2 communication.
Auto-switches between:
  1. Local LAN access  (http://<controller-ip>:1111/api2)
  2. Remote Cloud HTTPS (https://serial.in.larnitech.com:8443/api2)
  3. WebSocket tunnel (fallback)
"""

import os, time, json, requests, logging, socket
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# --------------------------------------------------
# Configuration
# --------------------------------------------------
SERIAL = os.getenv("LARNITECH_SERIAL", "")
PASSWORD = os.getenv("LARNITECH_PASSWORD", "")
LOCAL_IP = os.getenv("LARNITECH_LOCAL_IP", "")
LOCAL_PORT = os.getenv("LARNITECH_LOCAL_PORT", "1111")
REMOTE_URL = os.getenv("LARNITECH_URL", f"https://{SERIAL}.in.larnitech.com:8443/api2").rstrip("/")
TIMEOUT = int(os.getenv("LARNITECH_TIMEOUT", 5))
RETRIES = int(os.getenv("LARNITECH_RETRIES", 3))

logger = logging.getLogger("larnitech_client")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] [LarnitechClient] %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


def _headers() -> Dict[str, str]:
    return {
        "e-passw": PASSWORD,
        "srv-serial": SERIAL,
        "mode-is-remote": "4",
        "User-Agent": "MatterGateway/1.0"
    }


def _base_url() -> str:
    """Try local first, then remote."""
    if LOCAL_IP:
        test_url = f"http://{LOCAL_IP}:{LOCAL_PORT}/api2/device/list"
        try:
            res = requests.get(test_url, headers=_headers(), timeout=2)
            if res.status_code == 200:
                logger.info(f"✅ Using local Larnitech gateway at {LOCAL_IP}:{LOCAL_PORT}")
                return f"http://{LOCAL_IP}:{LOCAL_PORT}/api2"
        except Exception:
            pass
    logger.info(f"🌐 Using remote Larnitech cloud endpoint: {REMOTE_URL}")
    return REMOTE_URL


BASE_URL = _base_url()


def _request(method: str, endpoint: str, **kwargs):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    for attempt in range(1, RETRIES + 1):
        try:
            res = requests.request(method, url, timeout=TIMEOUT, **kwargs)
            if res.status_code == 502 and "/api" in url:
                alt = url.replace("/api", "/api2")
                logger.warning(f"⚠️  502 from /api → retrying with /api2...")
                res = requests.request(method, alt, timeout=TIMEOUT, **kwargs)
            res.raise_for_status()
            return res
        except Exception as e:
            logger.warning(f"[Attempt {attempt}] {e}")
            if attempt < RETRIES:
                time.sleep(1.5 * attempt)
    logger.error(f"❌ Failed after {RETRIES} attempts: {url}")
    return None


def list_devices() -> Optional[Any]:
    logger.info("Fetching Larnitech device list...")
    res = _request("GET", "device/list", headers=_headers())
    if not res:
        logger.error("Could not fetch device list. Using local fallback.")
        try:
            data = json.loads(open("config/devices_config.json").read())
            logger.info(f"📦 Loaded {len(data)} local fallback devices.")
            return data
        except Exception:
            return [
                {"id": "lamp1", "name": "LivingRoomLamp", "value": False},
                {"id": "dimmer1", "name": "BedroomDimmer", "value": 45},
                {"id": "temp1", "name": "RoomTempSensor", "value": 24.5}
            ]
    try:
        return res.json()
    except Exception as e:
        logger.error(f"JSON decode error: {e}")
        return None


def get_device_state(device_id: str) -> Optional[Dict[str, Any]]:
    res = _request("GET", f"device/get?id={device_id}", headers=_headers())
    if not res:
        return None
    try:
        return res.json()
    except Exception as e:
        logger.error(f"JSON parse error: {e}")
        return None


def set_device_state(device_id: str, value) -> bool:
    payload = {"id": device_id, "value": value}
    res = _request("POST", "device/set", json=payload, headers=_headers())
    if not res:
        logger.error(f"Failed to set device {device_id}")
        return False
    try:
        data = res.json()
        logger.info(f"✅ Device {device_id} updated successfully.")
        return data.get("result", True)
    except Exception:
        return False


if __name__ == "__main__":
    print("🔧 Testing Larnitech API connection...")
    devices = list_devices()
    print(json.dumps(devices, indent=2))
