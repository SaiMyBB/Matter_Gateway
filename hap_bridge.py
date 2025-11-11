# hap_bridge.py
"""
HomeKit bridge for Matter Gateway -> Larnitech devices.

- Exposes devices as HomeKit accessories (Lightbulb).
- Uses core.larnitech_client to list/get/set device state.
- Polls regularly and updates HomeKit characteristics.
- Shows pairing PIN/QR in console so you can add to Apple Home.
"""

import time
import threading
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# HAP-python imports
from pyhap.accessory import Accessory
from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver
from pyhap.const import CATEGORY_LIGHTBULB

# Your Larnitech client (make sure it's configured via .env)
from core.larnitech_client import list_devices, get_device_state, set_device_state

# config
POLL_INTERVAL = int(os.getenv("HAP_POLL_INTERVAL", 5))  # seconds
DEVICE_CONFIG = Path("config/larnitech_devices.json")


class LarnitechLightAccessory(Accessory):
    category = CATEGORY_LIGHTBULB

    def __init__(self, driver, name: str, device_id: str, supports_brightness: bool = False):
        super().__init__(driver, name)
        self.device_id = device_id
        self.supports_brightness = supports_brightness

        serv_light = self.add_preload_service("Lightbulb")
        self.char_on = serv_light.configure_char("On", setter_callback=self.set_on)
        if supports_brightness:
            self.char_bri = serv_light.configure_char("Brightness", setter_callback=self.set_brightness)
        else:
            self.char_bri = None

    # HomeKit -> Larnitech: set ON/OFF
    def set_on(self, value):
        try:
            # value is True/False
            ok = set_device_state(self.device_id, bool(value))
            if not ok:
                self.logger.warning(f"Failed to set device {self.device_id} to {value}")
        except Exception as e:
            self.logger.error(f"Error setting {self.device_id} on: {e}")

    # HomeKit -> Larnitech: set brightness (0-100)
    def set_brightness(self, value):
        if not self.supports_brightness:
            return
        try:
            ok = set_device_state(self.device_id, int(value))
            if not ok:
                self.logger.warning(f"Failed to set brightness for {self.device_id} to {value}")
        except Exception as e:
            self.logger.error(f"Error setting brightness: {e}")

    def update_from_backend(self, state: Dict[str, Any]):
        """
        Called by polling thread to update characteristic values from Larnitech state.
        state: device JSON from get_device_state
        """
        # common pattern: backend may return {"id":"lamp1","value":False} or {"power":True} etc.
        # check multiple keys
        val = None
        if "value" in state:
            val = state["value"]
        elif "power" in state:
            val = state["power"]
        elif "on" in state:
            val = state["on"]

        if isinstance(val, bool):
            try:
                self.char_on.set_value(bool(val))
            except Exception:
                pass

        # brightness
        bri = None
        if "brightness" in state:
            bri = state["brightness"]
        elif "value" in state and isinstance(state["value"], (int, float)) and self.supports_brightness:
            bri = int(state["value"])

        if bri is not None and self.char_bri:
            try:
                self.char_bri.set_value(int(bri))
            except Exception:
                pass


def build_device_list() -> Dict[str, Dict[str, Any]]:
    """
    Return dict mapping device_id -> {name, supports_brightness}
    Source: try Larnitech API list first; fallback to config file.
    """
    devices = {}
    api_list = list_devices()
    if api_list:
        # api_list expected to be list of {id, name, value, maybe type}
        for item in api_list:
            dev_id = item.get("id") or item.get("device_id")
            if not dev_id:
                continue
            name = item.get("name") or item.get("label") or dev_id
            # heuristic for brightness support
            supports_brightness = False
            if isinstance(item.get("value"), (int, float)):
                supports_brightness = True
            devices[dev_id] = {"name": name, "supports_brightness": supports_brightness}
        return devices

    # fallback to config file mapping (expects type and id)
    if DEVICE_CONFIG.exists():
        cfg = json.loads(DEVICE_CONFIG.read_text())
        for item in cfg:
            dev_id = item.get("id")
            name = item.get("name") or dev_id
            dtype = item.get("type", "").lower()
            supports_brightness = dtype in ("dimmer",)
            devices[dev_id] = {"name": name, "supports_brightness": supports_brightness}
    return devices


def poll_loop(driver: AccessoryDriver, accessories_map: Dict[str, LarnitechLightAccessory]):
    """Background thread: poll device states and update HomeKit characteristics."""
    while True:
        try:
            for dev_id, acc in accessories_map.items():
                state = get_device_state(dev_id)
                if state:
                    # normalized to dict
                    if isinstance(state, dict):
                        acc.update_from_backend(state)
                # small sleep per device (avoid hammering)
                time.sleep(0.1)
        except Exception as e:
            print(f"[HAP] Poll error: {e}")
        time.sleep(POLL_INTERVAL)


def run_bridge(pin: str = "031-45-154"):
    """
    Start HomeKit bridge. Default pairing PIN is the standard HAP example.
    Run this alongside your existing gateway.
    """
    driver = AccessoryDriver(port=51826, persist_file='hap_state.json')

    bridge = Bridge(driver, "Matter Gateway Bridge")
    driver.add_accessory(bridge)

    devices = build_device_list()
    acc_map: Dict[str, LarnitechLightAccessory] = {}

    # create and add accessories for each device
    for dev_id, meta in devices.items():
        name = meta["name"]
        supports_brightness = meta.get("supports_brightness", False)
        acc = LarnitechLightAccessory(driver, name, device_id=dev_id, supports_brightness=supports_brightness)
        bridge.add_accessory(acc)
        acc_map[dev_id] = acc

    # start polling thread after driver starts
    t = threading.Thread(target=poll_loop, args=(driver, acc_map), daemon=True)
    t.start()

    print("HomeKit bridge starting. Pair using the Home app with PIN:", pin)
    print("If you need a QR code (iOS 16+), use the PIN or generate QR externally.")
    driver.start()  # blocking


if __name__ == "__main__":
    # optional PIN from env
    pin_env = os.getenv("HAP_PIN")
    run_bridge(pin=pin_env or "031-45-154")
