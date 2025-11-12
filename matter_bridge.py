#!/usr/bin/env python3
"""
matter_bridge.py (fallback/testing mode)

- Lightweight, dependency-light bridge for demo/testing.
- Generates a QR (PNG + ASCII) that contains a short payload (bridge-id + pin).
- Exposes a small HTTP API for Google Home / bridge-like testing:
    GET  /devices
    GET  /device/{id}
    POST /device/{id}/set   -> {"value": ...}
- Broadcasts updates to the MatterGateway.broadcaster if available.

NOT a full Matter implementation. Use for demos and app testing while
you install / configure the full Matter stack (python-matter-server).
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from aiohttp import web
import qrcode
import qrcode.image.pil
import base64
from core.gateway import MatterGateway
from core.larnitech_client import set_device_state, get_device_state, list_devices

# ----- Config -----
BRIDGE_ID = os.getenv("MATTER_BRIDGE_ID", "matter-gateway-001")
SETUP_PIN = os.getenv("MATTER_PIN", "20202021")   # 8-digit PIN for easier testing
PORT = int(os.getenv("MATTER_PORT", 5580))
DEVICE_CONFIG = Path("config/devices_config.json")
QR_PNG_PATH = Path("matter_qr.png")

# ----- Logging -----
logger = logging.getLogger("matter_bridge")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] [MatterMock] %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

# ----- Gateway (shared broadcaster) -----
gateway = MatterGateway()  # uses existing project gateway; will be no-op if not fully initialized

# ----- Device loader (tries Larnitech API, falls back to config or built-ins) -----
def load_devices():
    api = list_devices()
    if api:
        logger.info(f"Loaded {len(api)} devices from Larnitech API.")
        # Expect list of {id, name, value}
        return api
    if DEVICE_CONFIG.exists():
        try:
            cfg = json.loads(DEVICE_CONFIG.read_text())
            logger.info(f"Loaded {len(cfg)} devices from config file.")
            return cfg
        except Exception as e:
            logger.warning(f"Failed to read config: {e}")
    # fallback
    fallback = [
        {"id": "lamp1", "name": "LivingRoomLamp", "value": False},
        {"id": "dimmer1", "name": "BedroomDimmer", "value": 45},
        {"id": "temp1", "name": "RoomTempSensor", "value": 24.5},
    ]
    logger.info("Using fallback device list.")
    return fallback

DEVICES = {d["id"]: d for d in load_devices()}

# ----- HTTP API -----
routes = web.RouteTableDef()

@routes.get("/devices")
async def http_list_devices(request):
    return web.json_response(list(DEVICES.values()))

@routes.get("/device/{dev_id}")
async def http_get_device(request):
    dev_id = request.match_info["dev_id"]
    dev = DEVICES.get(dev_id)
    if not dev:
        return web.json_response({"error":"not_found"}, status=404)
    # Try Larnitech for freshest value
    try:
        state = get_device_state(dev_id)
        if isinstance(state, dict):
            # normalize to "value" key if present
            if "value" in state:
                dev["value"] = state["value"]
            else:
                dev.update(state)
    except Exception:
        pass
    return web.json_response(dev)

@routes.post("/device/{dev_id}/set")
async def http_set_device(request):
    dev_id = request.match_info["dev_id"]
    payload = await request.json()
    val = payload.get("value")
    if dev_id not in DEVICES:
        return web.json_response({"status":"error","error":"not_found"}, status=404)

    ok = False
    try:
        ok = set_device_state(dev_id, val)
    except Exception:
        ok = False

    # local update and broadcast if success (or best-effort)
    if ok:
        DEVICES[dev_id]["value"] = val
        # broadcast to gateway/dashboard
        if gateway and getattr(gateway, "broadcaster", None):
            gateway.broadcaster({"event":"update","dev":dev_id,"attr":"value","val":val})
        return web.json_response({"status":"ok"})
    else:
        # still update locally for demo
        DEVICES[dev_id]["value"] = val
        if gateway and getattr(gateway, "broadcaster", None):
            gateway.broadcaster({"event":"update","dev":dev_id,"attr":"value","val":val})
        return web.json_response({"status":"ok","note":"local-only (backend failed)"}, status=200)

# ----- QR generation (simple and robust) -----
def make_qr_payload(bridge_id: str, pin: str):
    """
    Create a minimal payload text to encode in QR for demo:
    MTR-<bridge-id>-PIN:<pin>
    This is NOT the Matter Setup Payload; it's a lightweight fallback used
    for Google Home / demo scanning if the client app accepts a custom format.
    """
    return f"MTR-{bridge_id}-PIN:{pin}"

def generate_qr_image(payload_text: str, save_path: Path = QR_PNG_PATH):
    qr = qrcode.QRCode(version=3, box_size=6, border=2)
    qr.add_data(payload_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(save_path))
    logger.info(f"QR saved to {save_path}")

def print_ascii_qr(payload_text: str):
    # Use small ascii fallback (if terminal supports)
    try:
        import sys
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(payload_text)
        qr.make()
        print("\nASCII QR (scan with phone if your terminal supports it):\n")
        qr.print_ascii(invert=True)
    except Exception as e:
        logger.debug("ASCII QR not available: " + str(e))

# ----- Main runner -----
async def start_app():
    payload_text = make_qr_payload(BRIDGE_ID, SETUP_PIN)
    logger.info("🔑 Setup PIN: %s", SETUP_PIN)
    logger.info("📦 QR Payload: %s", payload_text)
    generate_qr_image(payload_text, QR_PNG_PATH)
    print_ascii_qr(payload_text)

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    logger.info("Matter Bridge (mock) running on http://0.0.0.0:%s", PORT)
    logger.info("Scan 'matter_qr.png' or use payload data to pair in your app (demo mode).")
    await site.start()
    # keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(start_app())
    except KeyboardInterrupt:
        logger.info("Stopped.")
