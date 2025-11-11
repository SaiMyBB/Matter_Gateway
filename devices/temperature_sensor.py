# devices/temperature_sensor.py
import asyncio
import random
from core.device_base import BaseDevice

class TemperatureSensor(BaseDevice):
    """
    Temperature Sensor:
      - Reports temperature in °C.
      - Periodically updates the value within 20–30°C.
      - Uses asyncio background task for simulation.
    """
    def __init__(self, name="TemperatureSensor", gateway=None, update_interval=10):
        super().__init__(name, device_type="temperature_sensor")
        self.state = {"temperature": 25.0}
        self.update_interval = update_interval
        self.gateway = gateway  # reference to gateway for persistence/broadcast

    def read_state(self):
        return dict(self.state)

    def write_state(self, attribute, value):
        # Sensors typically don't accept writes, but allow manual override if needed.
        if attribute == "temperature":
            try:
                val = float(value)
                self.state["temperature"] = val
                return True
            except Exception:
                return False
        return False

    async def auto_update(self):
        """Simulate periodic temperature updates"""
        while True:
            await asyncio.sleep(self.update_interval)
            # fluctuate ±0.5°C randomly within 20–30°C
            new_temp = self.state["temperature"] + random.uniform(-0.5, 0.5)
            new_temp = max(20.0, min(30.0, round(new_temp, 1)))
            self.state["temperature"] = new_temp
            print(f"[Sensor] {self.name}: temperature updated to {new_temp}°C")

            # persist and broadcast the update
            if self.gateway:
                self.gateway._persist_device_state(self.name)
                if self.gateway.broadcaster:
                    try:
                        self.gateway.broadcaster({
                            "event": "update",
                            "dev": self.name,
                            "attr": "temperature",
                            "val": new_temp
                        })
                    except Exception:
                        pass
