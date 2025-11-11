# devices/humidity_sensor.py
import asyncio
import random
from core.device_base import BaseDevice

class HumiditySensor(BaseDevice):
    """
    Humidity Sensor Device
    ----------------------
    Simulates a humidity sensor that reports relative humidity (%) between 20% and 90%.
    Automatically updates readings at a configurable interval and broadcasts changes
    to connected WebSocket clients.
    """

    def __init__(self, name="HumiditySensor", gateway=None, update_interval=15):
        """
        :param name: Display name of the sensor
        :param gateway: Reference to MatterGateway (for persistence & broadcasting)
        :param update_interval: Time interval between updates in seconds
        """
        super().__init__(name, device_type="humidity_sensor")
        self.state = {"humidity": 50.0}  # default humidity value (%)
        self.gateway = gateway
        self.interval = update_interval

    # -------------------------------
    # State Management
    # -------------------------------
    def read_state(self):
        """Return current humidity reading."""
        return dict(self.state)

    def write_state(self, attr, value):
        """This sensor is read-only by design."""
        if attr == "humidity":
            try:
                val = float(value)
                if 0.0 <= val <= 100.0:
                    self.state["humidity"] = val
                    return True
            except Exception:
                return False
        return False

    # -------------------------------
    # Auto Update Logic
    # -------------------------------
    async def auto_update(self):
        """Simulate periodic humidity changes and broadcast them."""
        while True:
            await asyncio.sleep(self.interval)

            # Randomly adjust humidity between 20–90%
            new_humidity = round(random.uniform(20.0, 90.0), 1)
            self.state["humidity"] = new_humidity
            print(f"[Sensor] {self.name}: humidity updated to {new_humidity}%")

            # Persist and broadcast update
            if self.gateway:
                try:
                    self.gateway._persist_device_state(self.name)
                    if self.gateway.broadcaster:
                        self.gateway.broadcaster({
                            "event": "update",
                            "dev": self.name,
                            "attr": "humidity",
                            "val": new_humidity
                        })
                except Exception as e:
                    print(f"[Warning] Broadcast/persistence failed for {self.name}: {e}")
