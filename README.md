# Matter Gateway — Full Delivery (Milestone 7)

## Overview
This repository contains the Matter Gateway (WebSocket API), Web Dashboard, Larnitech integration helpers, HomeKit bridge, and a Matter bridge prototype. The aim is to provide:
- Local WebSocket gateway + dashboard for virtual devices
- Persistent device state (JSON)
- Larnitech API client and optional live listener
- HomeKit & Matter bridge prototypes for mobile integration (iOS / Android)
- Full instructions to build and run in macOS / Linux environments

> NOTE: For a fully production-capable Matter bridge, the CHIP SDK Python bindings from `connectedhomeip` must be built and installed. This README covers both quick-demo (shims) and correct production paths.

---

## Quick status (what’s done)
- WebSocket Gateway & Dashboard — ✅
- Devices: OnOff Lamp, Dimmer, Thermostat, Temperature/Humidity/Light/Leak sensors — ✅
- Persistence scaffold (JSON) — ✅
- Larnitech client and WS listener (prototype) — ✅
- Web Dashboard (login + WS auth + live UI) — ✅
- HomeKit bridge prototype (`hap_bridge.py`) — ✅ (works with HAP Python)
- Matter bridge prototype (`matter_bridge.py`) — ✅ (works in demo mode with shims). Full Matter control requires CHIP Python bindings.

---

## Prerequisites
- macOS / Linux
- Python 3.12 (recommended for CHIP builds) — your project venv can be Python 3.13 for gateway, but CHIP build requires ≤ 3.12.
- Git, curl, build tools (cmake, ninja) if you plan to build connectedhomeip
- Optional: Home app (iOS) or Google Home (Android) to test HomeKit/Matter pairing.

---

## Files delivered
- `run_gateway.py` — starts WebSocket gateway (FastAPI / Uvicorn)
- `api/websocket_api.py` — WebSocket API and dashboard static mounts
- `api/web_ui/` — index.html, dashboard.js, style.css, login/register UI
- `core/` — gateway, persistence, larnitech_client, larnitech_ws_listener
- `devices/` — virtual device classes + sensors
- `hap_bridge.py` — HomeKit bridge (HAP-python)
- `matter_bridge.py` — Matter bridge prototype (uses python-matter-server / shims)
- `config/devices_config.json` — sample device list
- `data/devices_state.json` — runtime device state (auto created)
- `requirements.txt`, `setup.sh`, `run_matter_gateway.sh`, `.env.example`
- `verify_matter_env.py` (checks environment readiness)

---

## Quick demo (fast path, uses shims if full CHIP not available)
1. Create venv and install Python deps
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
