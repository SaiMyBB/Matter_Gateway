# devices/light_sensor.py
import asyncio
import random
from core.device_base import BaseDevice

class LightSensor(BaseDevice):
    """
    Light Sensor Device
    -------------------
    Simulates an ambient light sensor reporting illumination in lux (0–1000).
    Automatically updates its reading at a configurable interval and broadcasts
    updates to all connected WebSocket clients.
    """

    def __init__(self, name="LightSensor", gateway=None, update_interval=12):
        """
        :param name: Display name of the sensor
        :param gateway: Reference to MatterGateway (for persistence & broadcasting)
        :param update_interval: Time interval between sensor updates (seconds)
        """
        super().__init__(name, device_type="light_sensor")
        self.state = {"lux": 300.0}  # Default light level (lux)
        self.gateway = gateway
        self.interval = update_interval

    # -------------------------------
    # State Management
    # -------------------------------
    def read_state(self):
        """Return current light level."""
        return dict(self.state)

    def write_state(self, attr, value):
        """Optional manual override (not typically used for sensors)."""
        if attr == "lux":
            try:
                val = float(value)
                if 0 <= val <= 10000:
                    self.state["lux"] = val
                    return True
            except Exception:
                return False
        return False

    # -------------------------------
    # Auto Update Logic
    # -------------------------------
    async def auto_update(self):
        """Simulate periodic changes in ambient light level and broadcast."""
        while True:
            await asyncio.sleep(self.interval)

            # Randomly vary light levels between 0–1000 lux
            new_lux = round(random.uniform(0.0, 1000.0), 1)
            self.state["lux"] = new_lux
            print(f"[Sensor] {self.name}: light level updated to {new_lux} lux")

            # Persist state and broadcast update
            if self.gateway:
                try:
                    self.gateway._persist_device_state(self.name)
                    if self.gateway.broadcaster:
                        self.gateway.broadcaster({
                            "event": "update",
                            "dev": self.name,
                            "attr": "lux",
                            "val": new_lux
                        })
                except Exception as e:
                    print(f"[Warning] Broadcast/persistence failed for {self.name}: {e}")
