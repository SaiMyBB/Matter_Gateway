# devices/leak_sensor.py
import asyncio
import random
from core.device_base import BaseDevice

class LeakSensor(BaseDevice):
    """
    Leak Sensor Device
    ------------------
    Simulates a water leak sensor that toggles between detected (True)
    and not detected (False) states. Updates periodically and broadcasts
    events to all connected WebSocket clients.
    """

    def __init__(self, name="LeakSensor", gateway=None, update_interval=20):
        """
        :param name: Display name of the sensor
        :param gateway: Reference to MatterGateway for persistence/broadcast
        :param update_interval: Time interval between auto updates (in seconds)
        """
        super().__init__(name, device_type="leak_sensor")
        self.state = {"leak": False}  # Default: no leak detected
        self.gateway = gateway
        self.interval = update_interval

    # -------------------------------
    # State Management
    # -------------------------------
    def read_state(self):
        """Return the current leak detection state."""
        return dict(self.state)

    def write_state(self, attr, value):
        """
        Allow manual override of the leak state (boolean only).
        Typically used for testing or forced simulation.
        """
        if attr == "leak" and isinstance(value, bool):
            self.state["leak"] = value
            return True
        return False

    # -------------------------------
    # Auto Update Logic
    # -------------------------------
    async def auto_update(self):
        """
        Periodically toggles leak detection state to simulate random events.
        Broadcasts changes and persists state to JSON storage.
        """
        while True:
            await asyncio.sleep(self.interval)

            # Randomly toggle between True (leak detected) and False
            new_state = random.choice([True, False])
            self.state["leak"] = new_state
            status = "DETECTED" if new_state else "CLEAR"
            print(f"[Sensor] {self.name}: leak status {status}")

            # Persist and broadcast
            if self.gateway:
                try:
                    self.gateway._persist_device_state(self.name)
                    if self.gateway.broadcaster:
                        self.gateway.broadcaster({
                            "event": "update",
                            "dev": self.name,
                            "attr": "leak",
                            "val": self.state["leak"]
                        })
                except Exception as e:
                    print(f"[Warning] Broadcast/persistence failed for {self.name}: {e}")
