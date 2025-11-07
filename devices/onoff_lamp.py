import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.device_base import BaseDevice





class OnOffLamp(BaseDevice):
    def __init__(self, name="OnOffLamp"):
        super().__init__(name, device_type="lamp")
        self.state = {"power": False}

    def read_state(self):
        return self.state

    def write_state(self, attribute, value):
        if attribute == "power" and isinstance(value, bool):
            self.state["power"] = value
            print(f"[Device] {self.name}: Power {'ON' if value else 'OFF'}")
            return True
        return False
