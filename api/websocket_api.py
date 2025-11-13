# api/websocket_api.py
import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import os
from core.larnitech_ws_listener import larnitech_ws_listener

import qrcode
import io
import base64
import secrets
from io import BytesIO

# Authentication import
from api import auth

# Core gateway
from core.gateway import MatterGateway
from core.token_utils import verify_token


# Device imports
from devices.onoff_lamp import OnOffLamp
from devices.dimmer import Dimmer
from devices.thermostat import Thermostat
from devices.temperature_sensor import TemperatureSensor
from devices.humidity_sensor import HumiditySensor
from devices.light_sensor import LightSensor
from devices.leak_sensor import LeakSensor

# Temporary static PINs – replace with live values if needed
MATTER_PIN = "20202021"
HOMEKIT_PIN = "031-45-154"

# -------------------------------
# FastAPI App Initialization
# -------------------------------
app = FastAPI(title="Matter Gateway WebSocket API")

# Session middleware for login sessions
app.add_middleware(SessionMiddleware, secret_key="supersecret-session-key")

# Include authentication routes
app.include_router(auth.router)

# -------------------------------
# Serve static files (assets) — keep mounted as /assets as well
# -------------------------------
WEB_UI_DIR = Path(__file__).resolve().parents[0] / "web_ui"  # api/web_ui
if not WEB_UI_DIR.exists():
    WEB_UI_DIR = Path("api/web_ui")

# mount under /assets for explicit asset path if needed
app.mount("/assets", StaticFiles(directory=str(WEB_UI_DIR), html=True), name="webui_assets")

# also mount under /static (optional)
app.mount("/static", StaticFiles(directory=str(WEB_UI_DIR)), name="static_assets")


# Provide explicit routes for root-level asset requests so existing index.html works
@ app.get("/style.css")
async def style_css():
    f = WEB_UI_DIR / "style.css"
    if f.exists():
        return FileResponse(str(f), media_type="text/css")
    return Response(status_code=404)


@ app.get("/dashboard.js")
async def dashboard_js():
    f = WEB_UI_DIR / "dashboard.js"
    if f.exists():
        return FileResponse(str(f), media_type="application/javascript")
    return Response(status_code=404)


@ app.get("/favicon.ico")
async def favicon():
    f = WEB_UI_DIR / "favicon.ico"
    if f.exists():
        return FileResponse(str(f), media_type="image/x-icon")
    # no favicon file — return 204 No Content to avoid 404 spam
    return Response(status_code=204)


# -------------------------------
# Connection Manager
# -------------------------------
class ConnectionManager:
    """Manages active WebSocket connections and broadcasting"""
    def __init__(self):
        self.active: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active:
                self.active.remove(websocket)

    async def send_personal(self, websocket: WebSocket, message: dict):
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        """Send message to all connected WebSocket clients"""
        data = json.dumps(message)
        async with self.lock:
            to_remove = []
            for ws in list(self.active):
                try:
                    await ws.send_text(data)
                except Exception:
                    to_remove.append(ws)
            for r in to_remove:
                self.active.remove(r)


manager = ConnectionManager()

# -------------------------------
# Gateway Initialization
# -------------------------------
def broadcaster_wrapper(msg):
    """Wrapper to broadcast messages asynchronously"""
    asyncio.create_task(manager.broadcast(msg))

gateway = MatterGateway(broadcaster=broadcaster_wrapper)

# -------------------------------
# Device Factory & Loader
# -------------------------------
DEVICE_MAP = {
    "OnOffLamp": OnOffLamp,
    "Dimmer": Dimmer,
    "Thermostat": Thermostat,
    "TemperatureSensor": TemperatureSensor,
    "HumiditySensor": HumiditySensor,
    "LightSensor": LightSensor,
    "LeakSensor": LeakSensor,
}

def load_devices_from_config(gateway: MatterGateway):
    """Dynamically load devices from config/devices_config.json"""
    config_path = Path("config/devices_config.json")
    devices = []
    if not config_path.exists():
        print("[Gateway] Config file not found — using default devices.")
        devices = [
            OnOffLamp("LivingRoomLamp"),
            Dimmer("BedroomDimmer"),
            Thermostat("MainThermostat"),
            TemperatureSensor("RoomTempSensor", gateway=gateway),
            HumiditySensor("HomeHumidity", gateway=gateway),
            LightSensor("WindowLight", gateway=gateway),
            LeakSensor("PipeLeak", gateway=gateway)
        ]
    else:
        try:
            cfg = json.loads(config_path.read_text())
        except Exception as e:
            print(f"[Gateway] Failed to parse config/devices_config.json: {e}")
            cfg = []
        for item in cfg:
            dev_type, name = item.get("type"), item.get("name")
            cls = DEVICE_MAP.get(dev_type)
            if cls:
                try:
                    device = cls(name, gateway=gateway)
                except TypeError:
                    device = cls(name)
                    device.gateway = gateway
                devices.append(device)
    for dev in devices:
        gateway.register_device(dev)
    return devices

# -------------------------------
# FastAPI Startup / Shutdown
# -------------------------------
@app.on_event("startup")
async def startup_event():
    """Initialize devices, start background tasks, and begin Larnitech sync."""
    print("[Startup] Loading devices from configuration...")
    gateway.devices_list = load_devices_from_config(gateway)
    print(f"[Startup] Devices loaded: {[d.name for d in gateway.devices_list]}")

    # ---------------------------------------------
    # 1️⃣ Start local sensor auto-update tasks
    # ---------------------------------------------
    gateway._tasks = []
    for dev in gateway.devices_list:
        if hasattr(dev, "auto_update") and asyncio.iscoroutinefunction(dev.auto_update):
            print(f"[Startup] Starting auto-update task for {dev.name}")
            task = asyncio.create_task(dev.auto_update())
            gateway._tasks.append(task)

    # ---------------------------------------------
    # 2️⃣ Start Larnitech WebSocket listener
    # ---------------------------------------------
    try:
        print("[Startup] Starting Larnitech WebSocket listener...")
        ws_task = asyncio.create_task(larnitech_ws_listener(gateway))
        gateway._tasks.append(ws_task)
    except Exception as e:
        print(f"[Startup] ⚠️ Failed to start Larnitech WS listener: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cancel background tasks cleanly"""
    print("[Shutdown] Stopping background tasks...")
    tasks = getattr(gateway, "_tasks", [])
    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

# ===========================================================
#               PAIRING INFO (Matter + HomeKit)
# ===========================================================

def _qr_to_data_uri(text: str) -> str:
    """Generate a QR PNG and return as base64 data URI."""
    try:
        qr = qrcode.QRCode(
            version=2,
            box_size=6,
            border=2,
            error_correction=qrcode.constants.ERROR_CORRECT_M
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[PAIRING] QR generation failed: {e}")
        return None


@app.get("/pairing-info")
async def pairing_info():
    """
    Returns both Matter and HomeKit pairing QR codes + PIN data.
    Used by frontend to show the 'Add Device' modal.
    """

    # -----------------------------
    #  HOMEKIT SETUP
    # -----------------------------
    hk_pin = os.getenv("HAP_PIN", "031-45-154")
    hk_manual_str = f"PIN:{hk_pin}"

    # NOTE: HomeKit official QR requires special payload, but PIN-only works.
    hk_qr_data = _qr_to_data_uri(hk_manual_str)

    # -----------------------------
    #  MATTER SETUP
    # -----------------------------
    matter_pin = os.getenv("MATTER_PIN", os.getenv("MATTER_SETUP_PIN", "20202021"))
    bridge_id = os.getenv("MATTER_BRIDGE_ID", "matter-gateway-001")

    # Simple mock Matter payload (works for QR display)
    matter_payload = f"MTR-{bridge_id}-PIN:{matter_pin}"

    matter_qr_data = _qr_to_data_uri(matter_payload)

    # -----------------------------
    #  RESPONSE
    # -----------------------------
    return {
        "homekit": {
            "pin": hk_pin,
            "manual": hk_manual_str,
            "qr": hk_qr_data
        },
        "matter": {
            "setup_pin": matter_pin,
            "payload": matter_payload,
            "qr": matter_qr_data
        },
        "status": "ok"
    }


# -------------------------------
# Protected Web Dashboard Route
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the dashboard only if logged in"""
    if not auth.is_authenticated(request):
        return RedirectResponse("/login")
    # serve index.html from api/web_ui
    index_path = WEB_UI_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return HTMLResponse("<h3>Dashboard not found</h3>", status_code=404)

# -------------------------------
# WebSocket Endpoint
# -------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles WebSocket API2-style commands with JWT authentication."""
    DEV_MODE = True     # temporary override

    # ✅ Step 1: Extract token from cookies or query
    token = websocket.cookies.get("access_token") or websocket.query_params.get("token")
    if not token:
        # also allow ?token=... for testing
        token = websocket.query_params.get("token")

    # ✅ Step 2: Validate token
    username = verify_token(token) if token else None
    if not username:
        await websocket.close(code=1008)  # policy violation (unauthorized)
        print("[Security] Unauthorized WebSocket connection rejected.")
        return

    # ✅ Step 3: Accept connection
    await manager.connect(websocket)
    print(f"[Security] WebSocket connection accepted for user '{username}'")

    try:
        await manager.send_personal(websocket, {"status": "ok", "msg": "connected"})

        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {"status": "error", "error": "invalid_json"})
                continue

            cmd = msg.get("cmd")
            if cmd == "set":
                dev = msg.get("dev")
                attr = msg.get("attr")
                val = msg.get("val")
                ok, err = gateway.set_device_attribute(dev, attr, val)
                resp = {"status": "ok", "dev": dev, "attr": attr, "val": val} if ok else {"status": "error", "error": err}
                await manager.send_personal(websocket, resp)

            elif cmd == "get":
                dev = msg.get("dev")
                device = gateway.get_device(dev)
                if not device:
                    await manager.send_personal(websocket, {"status": "error", "error": "device_not_found"})
                else:
                    await manager.send_personal(websocket, {"status": "ok", "dev": dev, "state": device.read_state()})

            elif cmd == "list":
                devices = gateway.get_all_devices()
                print("📦 Sending devices to dashboard:", devices)
                await manager.send_personal(websocket, {"status": "ok", "devices": devices})


            else:
                await manager.send_personal(websocket, {"status": "error", "error": "unknown_cmd"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)


def generate_qr_base64(text: str) -> str:
    """Generate QR PNG and return base64 string."""
    qr = qrcode.QRCode(version=2, box_size=6, border=2)
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


@app.get("/qr/matter")
async def qr_matter():
    """Matter (Google Home) pairing QR."""
    qr_text = f"MTR-matter-gateway-001-PIN:{MATTER_PIN}"
    qr_b64 = generate_qr_base64(qr_text)
    return JSONResponse({"qr": qr_b64, "pin": MATTER_PIN})


@app.get("/qr/homekit")
async def qr_homekit():
    """HomeKit pairing QR."""
    # HomeKit QR format (HAP):
    qr_text = f"X-HM://0023IS{HOMEKIT_PIN.replace('-', '')}"
    qr_b64 = generate_qr_base64(qr_text)
    return JSONResponse({"qr": qr_b64, "pin": HOMEKIT_PIN})