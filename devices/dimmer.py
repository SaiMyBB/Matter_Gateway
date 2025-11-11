# devices/dimmer.py
from core.device_base import BaseDevice

class Dimmer(BaseDevice):
    """
    Dimmer device:
      - state: {"power": bool, "brightness": int (0-100)}
      - write_state validates types and ranges
    """
    def __init__(self, name="Dimmer"):
        super().__init__(name, device_type="dimmer")
        # default: off, brightness 0
        self.state = {"power": False, "brightness": 0}

    def read_state(self):
        # return a copy to avoid accidental mutation by callers
        return dict(self.state)

    def write_state(self, attribute, value):
        # power: boolean
        if attribute == "power":
            if not isinstance(value, bool):
                return False
            # if turning off, keep brightness but device is off
            self.state["power"] = value
            return True

        # brightness: integer 0..100
        if attribute == "brightness":
            # allow ints and numeric strings that represent integers
            try:
                # if value is bool, reject (bool is subclass of int)
                if isinstance(value, bool):
                    return False
                brightness = int(value)
            except Exception:
                return False
            if 0 <= brightness <= 100:
                self.state["brightness"] = brightness
                # auto-turn-on when brightness > 0 (common behavior)
                if brightness > 0:
                    self.state["power"] = True
                return True
            else:
                return False

        # unknown attribute
        return False
