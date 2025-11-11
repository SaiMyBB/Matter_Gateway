# Matter Gateway — Milestone 1

### 🔹 Overview
This repository contains the **base Matter Gateway implementation** and the **first virtual device (On/Off Lamp)**.  
It establishes the foundational architecture for simulating Matter-compliant smart devices that can be controlled via REST APIs.

---

## Milestone 1 Features

| Component | Description |
|------------|-------------|
| **Base Gateway** | Core framework to register, manage, and interact with virtual devices. |
| **On/Off Lamp** | First functional virtual device supporting power ON/OFF control. |
| **REST API** | FastAPI-powered endpoints for listing, reading, and updating device states. |
| **Commissionable Bridge (Scaffold)** | Gateway acts as a bridge exposing endpoints for future Matter integration. |
| **Persistence Scaffold** | Placeholder for saving/restoring device state (coming in Milestone 3). |

---

## Project Structure
Matter_Gateway/
├── api/
│ ├── init.py
│ └── rest_api.py
├── core/
│ ├── init.py
│ ├── device_base.py
│ ├── gateway.py
│ └── persistence.py
├── devices/
│ ├── init.py
│ └── onoff_lamp.py
├── requirements.txt
└── run_gateway.py



---

## Setup & Run Instructions

### Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# To the run the gateway
python run_gateway.py

--> Server starts at:
 http://localhost:8000

--> REST API Endpoints
Method	Endpoint	Description
GET	/devices	List all registered virtual devices
GET	/devices/{name}	Read device state
POST	/devices/{name}/{attribute}?value={bool}	Update device state


--> Testing the On/Off Lamp
curl http://localhost:8000/devices
curl -X POST "http://localhost:8000/devices/LivingRoomLamp/power?value=true"
curl http://localhost:8000/devices/LivingRoomLamp
curl -X POST "http://localhost:8000/devices/LivingRoomLamp/power?value=false"



# Matter Gateway — Milestone 4  
### 🔹 Secure Authentication + Real-Time WebSocket Dashboard  

---

## 🧠 Overview

This project implements a **Python-based Matter Gateway framework** that simulates smart-home devices, provides a **real-time dashboard**, and integrates **user authentication with email verification**.  

This version (Milestone 4) completes the full authentication system and live WebSocket control of virtual devices.  
It lays the groundwork for **Milestone 5**, which will connect directly to the client’s **Larnitech API2** system.

---

## ⚙️ Features

| Area | Description |
|------|--------------|
| **Authentication** | User registration, login, logout with JWT + session cookies |
| **Email Verification** | Async SMTP verification link using `aiosmtplib` |
| **WebSocket API** | Live device updates using FastAPI’s WebSocket support |
| **Dashboard UI** | Clean HTML + JS interface for real-time control |
| **Virtual Devices** | On/Off Lamp, Dimmer, Thermostat, Temperature, Humidity, Light, Leak Sensors |
| **Auto-Update Sensors** | Periodic updates for environmental devices |
| **Persistence Scaffold** | JSON-based storage and state recovery |
| **Extensible Architecture** | Ready to integrate with real Matter or Larnitech APIs |

---

## 📂 Project Structure

Matter_Gateway/
├── api/
│ ├── auth.py
│ ├── websocket_api.py
│ └── web_ui/
│ ├── index.html
│ ├── login.html
│ ├── register.html
│ ├── dashboard.js
│ └── style.css
│
├── core/
│ ├── gateway.py
│ ├── device_base.py
│ ├── token_utils.py
│ ├── email_utils.py
│ ├── security.py
│ └── persistence.py
│
├── devices/
│ ├── onoff_lamp.py
│ ├── dimmer.py
│ ├── thermostat.py
│ ├── temperature_sensor.py
│ ├── humidity_sensor.py
│ ├── light_sensor.py
│ └── leak_sensor.py
│
├── config/
│ └── devices_config.json
│
├── data/
│ └── users.json
│
├── run_gateway.py
├── requirements.txt
├── README.md
└── CHANGELOG.txt



---

## 🧰 Setup Instructions

### 1️⃣ Create and activate virtual environment
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1       # PowerShell on Windows

2️⃣ Install dependencies
pip install -r requirements.txt

If WebSockets are not detected, install the full set:
pip install "uvicorn[standard]" websockets