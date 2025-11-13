.

🏠 Matter Gateway – Larnitech Smart Home Bridge

A Python-based Matter Gateway connecting Larnitech Smart Home controllers to both Apple HomeKit and Google Home (Matter) ecosystems.

This gateway allows real-time monitoring and control of Larnitech devices using standardized Matter protocols — with a WebSocket core, persistent storage, dashboard UI, and dual-bridge support (HAP + Matter).

🌍 Project Overview
Module	Description
api/websocket_api.py	FastAPI WebSocket gateway handling live updates and commands
core/larnitech_client.py	Secure connection to Larnitech API2 over LAN or Cloud
core/larnitech_ws_listener.py	Persistent WebSocket listener for live state updates
hap_bridge.py	Exposes devices to Apple HomeKit (HAP protocol)
matter_bridge.py	Exposes devices to Android/Google Home (Matter QR pairing)
core/persistence.py	JSON-based device state persistence
config/devices_config.json	Device configuration and defaults
README.md	Setup and usage guide
CHANGELOG.txt	Version and milestone documentation
🧩 Architecture Diagram
graph TD
    A[Larnitech Controller] -->|API2 HTTPS/WS| B[core/larnitech_client.py]
    B --> C[Matter Gateway Core]
    C --> D[api/websocket_api.py]
    C --> E[core/persistence.py]
    D --> F[Dashboard Web UI]
    C --> G[hap_bridge.py]
    C --> H[matter_bridge.py]
    G -->|Apple Home| I[iOS Home App]
    H -->|Matter| J[Google Home App]

⚙️ Installation & Setup
🧱 1. Prerequisites

Ensure you have the following installed:

macOS (M1/M2/M3) / Linux / Windows 10+

Python 3.10 – 3.12 (⚠️ 3.13 not supported by HAP/Matter)

Homebrew (macOS only)

Install dependencies:

pip install -r requirements.txt


On macOS:

brew install websocat openssl

⚙️ 2. Environment Configuration

Copy the sample environment file:

cp config/.env.example .env


Edit .env and fill in your details:

# 🔌 Larnitech API Connection
LARNITECH_URL=https://1876d100.in.larnitech.com:8443/api2
LARNITECH_SERIAL=1876d100
LARNITECH_PASSWORD=11111111
LARNITECH_TOKEN=
LARNITECH_TIMEOUT=5
LARNITECH_RETRIES=3

# Optional Local LAN URL (when connected directly to controller)
# LARNITECH_LOCAL_IP=http://192.168.1.50:1111/api2

# 🍎 HomeKit Configuration
HAP_PIN=031-45-154

# 🤖 Matter Configuration
MATTER_PORT=5580
MATTER_PIN=20202021

🧠 3. Verify Larnitech API Connectivity
✅ Step 1: Remote (Cloud)

Run:

curl -v "https://1876d100.in.larnitech.com:8443/api2/device/list" \
  -H "srv-serial: 1876d100" \
  -H "e-passw: 11111111"


If you see:

502 Bad Gateway


then the controller’s cloud API2 is unreachable externally.

➡️ Proceed to local connection setup below.

🌐 Step 2: Local (LAN)

Ask the client for the controller’s local IP (example 192.168.1.45),
then test locally:

curl "http://192.168.1.45:1111/api2/device/list" \
  -H "srv-serial: 1876d100" \
  -H "e-passw: 11111111"


If this returns JSON (device list) → perfect ✅
Then, update .env:

LARNITECH_URL=http://192.168.1.45:1111/api2

🚀 4. Run the Matter Gateway (Core API)

Start the WebSocket gateway:

python3 run_gateway.py


Expected output:

🚀 Starting Matter Gateway (WebSocket API) on http://localhost:8000
[Startup] Devices loaded: ['LivingRoomLamp', 'BedroomDimmer', 'RoomTempSensor']


Your dashboard will be available at:

http://localhost:8000

🍎 5. Run the HomeKit Bridge (iOS)

Start the bridge:

python3 hap_bridge.py


You’ll see:

HomeKit bridge starting. Pair using Home app with PIN: 031-45-154


Then on your iPhone:

Open Apple Home

Tap ➕ → “Add Accessory”

Enter the PIN or scan the QR code

You’ll see devices appear (Lamp, Dimmer, Thermostat)

🤖 6. Run the Matter Bridge (Android / Google Home)

For Android pairing:

python3 matter_bridge.py


You’ll see:

🔑 Setup PIN: 20202021
📦 QR Payload: MTR-matter-gateway-001-PIN:20202021


And a QR code displayed in terminal (matter_qr.png saved locally).

Then:

Open Google Home

Tap ➕ → Device → New Device → Matter

Scan the displayed QR

This mock Matter bridge will expose your devices to Android/Google Home UI.

🧩 Troubleshooting
❌ 502 Bad Gateway (API2)

Check that API2 is enabled on Larnitech Controller.

Ask client to enable:

Configurator → Network → "Enable API2 over server"


If not visible, use local LAN connection via port 1111.

⚠️ Port already in use (51826)

When running HAP bridge:

OSError: [Errno 48] address already in use


Fix:

sudo lsof -i :51826
kill -9 <PID>


Then rerun the bridge.

🔒 HomeKit Not Discoverable

If pairing fails, try:

rm -rf ~/.pyhap


Then restart hap_bridge.py to generate a new pairing identity.

🌐 “No route to host” or LAN connection refused

Ensure:

Your Mac and Larnitech Controller are on the same network.

VPNs or Firewalls are disabled temporarily.

🧪 Testing & Diagnostics

To test API endpoints:

python3 core/test_larnitech_endpoints.py
python3 core/test_larnitech_endpoints_extended.py


To manually test WebSocket:

websocat "wss://1876d100.in.larnitech.com:8443/api2" \
  -H "srv-serial: 1876d100" \
  -H "e-passw: 11111111"

📂 Directory Layout
Matter_Gateway/
├── api/
│   ├── websocket_api.py
│   └── web_ui/
│       ├── index.html
│       └── dashboard.js
├── core/
│   ├── gateway.py
│   ├── larnitech_client.py
│   ├── larnitech_ws_listener.py
│   ├── persistence.py
│   ├── test_larnitech_endpoints.py
│   └── test_larnitech_endpoints_extended.py
├── devices/
│   ├── onoff_lamp.py
│   ├── thermostat.py
│   └── temperature_sensor.py
├── config/
│   ├── devices_config.json
│   └── .env.example
├── hap_bridge.py
├── matter_bridge.py
├── run_gateway.py
├── README.md
└── CHANGELOG.txt
