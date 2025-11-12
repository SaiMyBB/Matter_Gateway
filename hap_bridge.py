"""
hap_bridge.py — Production Ready (Milestone 6)

HomeKit bridge for Matter Gateway ↔ Larnitech ↔ Dashboard

Features:
- Exposes all discovered Larnitech or virtual devices as HomeKit accessories.
- Syncs HomeKit actions → Larnitech API (via REST) + Gateway Dashboard broadcast.
- Polls backend to refresh HomeKit states (for remote changes).
- Runs safely with FastAPI Matter Gateway on macOS/iOS.
"""

import os
import time
import json
import threading
import logging
from pathlib import Path
from typing import Dict, Any

# HAP-Python
from pyhap.accessory import Accessory, Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_LIGHTBULB

# Core modules
from core.larnitech_client import list_devices, get_device_state, set_device_state
from core.gateway import MatterGateway

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
POLL_INTERVAL = int(os.getenv("HAP_POLL_INTERVAL", 5))
DEVICE_CONFIG = Path("config/larnitech_devices.json")

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logger = logging.getLogger("hap_bridge")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[%(asctime)s] [HAP] %(message)s", "%H:%M:%S"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

# Global gateway instance for broadcasting
gateway = MatterGateway()  # reuse existing persistence/broadcast logic

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _call_set_device_state_async(device_id: str, value):
    """Send command to Larnitech cloud in background thread."""
    def worker():
        try:
            ok = set_device_state(device_id, value)
            logger.info(f"[Larnitech] set_device_state({device_id}, {value}) -> {ok}")
        except Exception as e:
            logger.exception(f"[Larnitech] Failed to set {device_id}: {e}")
    threading.Thread(target=worker, daemon=True).start()


def _broadcast_update(dev_name: str, attr: str, val):
    """Broadcast change to WebSocket dashboard."""
    try:
        if gateway and getattr(gateway, "broadcaster", None):
            gateway.broadcaster({"event": "update", "dev": dev_name, "attr": attr, "val": val})
            logger.info(f"[Broadcast] {dev_name} {attr} -> {val}")
    except Exception:
        logger.exception("[Broadcast] Broadcast failed.")


# ---------------------------------------------------------------------
# Accessory Class
# ---------------------------------------------------------------------
class LarnitechLightAccessory(Accessory):
    category = CATEGORY_LIGHTBULB

    def __init__(self, driver, name: str, device_id: str, supports_brightness: bool = False):
        super().__init__(driver, name)
        self.device_id = device_id
        self.supports_brightness = supports_brightness

        # HAP service & characteristics
        chars = ["On"]
        if supports_brightness:
            chars.append("Brightness")
        serv_light = self.add_preload_service("Lightbulb", chars=chars)

        self.char_on = serv_light.configure_char("On", setter_callback=self.set_on)
        self.char_bri = None
        if supports_brightness:
            self.char_bri = serv_light.configure_char("Brightness", setter_callback=self.set_brightness)

    # -------------------------
    # HomeKit → Larnitech
    # -------------------------
    def set_on(self, value):
        """Toggle ON/OFF from Home app."""
        val = bool(value)
        logger.info(f"[HomeKit] {self.display_name} → {'ON' if val else 'OFF'}")
        _call_set_device_state_async(self.device_id, val)
        _broadcast_update(self.display_name, "power", val)
        # Update local persistence
        dev = gateway.get_device(self.display_name)
        if dev:
            dev.write_state("power", val)
            gateway._persist_device_state(dev.name)

    def set_brightness(self, value):
        """Set brightness from Home app."""
        if not self.supports_brightness:
            return
        bri = int(value)
        logger.info(f"[HomeKit] {self.display_name} Brightness → {bri}")
        _call_set_device_state_async(self.device_id, bri)
        _broadcast_update(self.display_name, "brightness", bri)
        dev = gateway.get_device(self.display_name)
        if dev:
            dev.write_state("brightness", bri)
            gateway._persist_device_state(dev.name)

    # -------------------------
    # Larnitech → HomeKit
    # -------------------------
    def update_from_backend(self, state: Dict[str, Any]):
        """Update HomeKit characteristic values from Larnitech state."""
        try:
            # On/Off
            val = None
            for k in ("value", "power", "on"):
                if k in state:
                    val = state[k]
                    break
            if isinstance(val, bool):
                self.char_on.set_value(val)
            # Brightness
            bri = None
            if "brightness" in state:
                bri = state["brightness"]
            elif isinstance(state.get("value"), (int, float)) and self.supports_brightness:
                bri = int(state["value"])
            if bri is not None and self.char_bri:
                self.char_bri.set_value(int(bri))
        except Exception as e:
            logger.warning(f"[Update] Failed to update {self.display_name}: {e}")


# ---------------------------------------------------------------------
# Device Discovery
# ---------------------------------------------------------------------
def build_device_list() -> Dict[str, Dict[str, Any]]:
    """Discover Larnitech devices; fallback to config file."""
    devices = {}
    api_list = list_devices()
    if api_list:
        for item in api_list:
            dev_id = item.get("id") or item.get("device_id")
            if not dev_id:
                continue
            name = item.get("name") or item.get("label") or dev_id
            val = item.get("value")
            supports_brightness = isinstance(val, (int, float))
            devices[dev_id] = {"name": name, "supports_brightness": supports_brightness}
        logger.info(f"[Discovery] Found {len(devices)} devices from Larnitech cloud.")
        return devices

    if DEVICE_CONFIG.exists():
        cfg = json.loads(DEVICE_CONFIG.read_text())
        for item in cfg:
            dev_id = item.get("id")
            name = item.get("name") or dev_id
            dtype = item.get("type", "").lower()
            supports_brightness = dtype in ("dimmer",)
            devices[dev_id] = {"name": name, "supports_brightness": supports_brightness}
        logger.info(f"[Discovery] Loaded {len(devices)} devices from local config.")
    else:
        logger.warning("[Discovery] No devices found.")
    return devices


# ---------------------------------------------------------------------
# Polling Loop
# ---------------------------------------------------------------------
def poll_loop(driver: AccessoryDriver, accessories_map: Dict[str, LarnitechLightAccessory]):
    """Background polling of Larnitech device states."""
    while True:
        try:
            for dev_id, acc in accessories_map.items():
                state = get_device_state(dev_id)
                if isinstance(state, dict):
                    acc.update_from_backend(state)
                time.sleep(0.1)
        except Exception as e:
            logger.warning(f"[Poll] {e}")
        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------
# Bridge Runner
# ---------------------------------------------------------------------
def run_bridge(pin: str = "031-45-154"):
    """Start HomeKit bridge; pair via Home app using displayed PIN."""
    driver = AccessoryDriver(port=51826, persist_file='hap_state.json')

    bridge = Bridge(driver, "Matter Gateway Bridge")
    driver.add_accessory(bridge)

    devices = build_device_list()
    acc_map: Dict[str, LarnitechLightAccessory] = {}

    # Create accessories
    for dev_id, meta in devices.items():
        name = meta["name"]
        supports_brightness = meta.get("supports_brightness", False)
        acc = LarnitechLightAccessory(driver, name, device_id=dev_id,
                                      supports_brightness=supports_brightness)
        bridge.add_accessory(acc)
        acc_map[dev_id] = acc

    # Start polling thread
    threading.Thread(target=poll_loop, args=(driver, acc_map), daemon=True).start()

    logger.info("HomeKit bridge starting. Pair using the Home app with PIN: %s", pin)
    logger.info("If using iOS 16+, you can scan a QR generated externally with the same PIN.")
    driver.start()  # blocking


# ---------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------
if __name__ == "__main__":
    pin_env = os.getenv("HAP_PIN", "031-45-154")
    try:
        run_bridge(pin=pin_env)
    except KeyboardInterrupt:
        logger.info("Stopping HomeKit bridge...")
