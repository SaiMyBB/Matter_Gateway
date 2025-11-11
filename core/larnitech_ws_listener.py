"""
core/larnitech_ws_listener.py
-------------------------------------------------
Listens for live device updates from the Larnitech
controller over a secure WebSocket (wss://...).

Uses Bearer token authentication if provided.
Automatically reconnects if connection is lost.
Broadcasts incoming updates to connected dashboard
and HomeKit bridge clients via MatterGateway.broadcaster.
"""

import asyncio
import json
import os
import ssl
import websockets
import logging

# ------------------------------------------------------------------
# Configuration from environment (.env)
# ------------------------------------------------------------------
LARNITECH_WS_URL = os.getenv("LARNITECH_WS_URL", "wss://1876d100.in.larnitech.com:8443/api")
LARNITECH_TOKEN = os.getenv("LARNITECH_TOKEN", None)
RECONNECT_DELAY = int(os.getenv("LARNITECH_WS_RECONNECT", 10))

# ------------------------------------------------------------------
# Logger setup
# ------------------------------------------------------------------
logger = logging.getLogger("larnitech_ws_listener")
if not logger.handlers:
    h = logging.StreamHandler()
    f = logging.Formatter("[%(asctime)s] [%(levelname)s] [LarnitechWS] %(message)s", "%H:%M:%S")
    h.setFormatter(f)
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


# ------------------------------------------------------------------
# Main listener
# ------------------------------------------------------------------
async def larnitech_ws_listener(gateway):
    """
    Connect to Larnitech secure WebSocket stream and listen for device updates.
    Expected message format:
        {"id": "lamp1", "value": true}
    """
    ssl_context = ssl.create_default_context()
    headers = [("Authorization", LARNITECH_TOKEN)] if LARNITECH_TOKEN else []

    while True:
        try:
            logger.info(f"🔌 Connecting securely to Larnitech WS at {LARNITECH_WS_URL} ...")
            async with websockets.connect(
                LARNITECH_WS_URL,
                extra_headers=headers,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=20,
            ) as ws:
                logger.info("✅ Connected to Larnitech WebSocket stream (secure).")

                async for message in ws:
                    try:
                        data = json.loads(message)
                    except json.JSONDecodeError:
                        logger.warning(f"⚠️ Invalid JSON received: {message}")
                        continue

                    dev_id = data.get("id")
                    val = data.get("value")

                    if not dev_id:
                        logger.debug("Received message without device ID, skipping.")
                        continue

                    # Find the matching registered device
                    matched_device = None
                    for dev in gateway.devices.values():
                        if getattr(dev, "larnitech_id", None) == dev_id:
                            matched_device = dev
                            break

                    if matched_device:
                        # Update local device state
                        matched_device.state["value"] = val
                        logger.info(f"🔁 {matched_device.name} updated via Larnitech WS → {val}")

                        # Persist to JSON file
                        gateway._persist_device_state(matched_device.name)

                        # Broadcast to dashboard / HomeKit
                        if gateway.broadcaster:
                            gateway.broadcaster({
                                "event": "update",
                                "dev": matched_device.name,
                                "attr": "value",
                                "val": val
                            })
                    else:
                        logger.debug(f"⚠️ Unknown device id {dev_id} from WS.")

        except (ConnectionRefusedError, OSError, websockets.exceptions.ConnectionClosedError) as e:
            logger.warning(f"⚠️ WebSocket connection lost: {e}")
            logger.info(f"🔄 Reconnecting in {RECONNECT_DELAY} seconds...")
            await asyncio.sleep(RECONNECT_DELAY)
        except Exception as e:
            logger.error(f"❌ Unexpected WS error: {e}")
            await asyncio.sleep(RECONNECT_DELAY)
