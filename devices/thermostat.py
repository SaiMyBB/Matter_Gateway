# devices/thermostat.py
from core.device_base import BaseDevice

class Thermostat(BaseDevice):
    """
    Thermostat Device:
      - Attributes:
          mode: str -> "heat", "cool", or "auto"
          setpoint: int -> desired temperature in °C (10–30)
      - Behavior:
          validates all writes, keeps state in persistence
    """

    def __init__(self, name="Thermostat"):
        super().__init__(name, device_type="thermostat")
        self.state = {"mode": "auto", "setpoint": 24}

    def read_state(self):
        return dict(self.state)

    def write_state(self, attribute, value):
        # ---- mode attribute ----
        if attribute == "mode":
            if isinstance(value, str) and value.lower() in ["heat", "cool", "auto"]:
                self.state["mode"] = value.lower()
                return True
            return False

        # ---- setpoint attribute ----
        if attribute == "setpoint":
            try:
                # ensure numeric (allow strings convertible to int)
                set_temp = int(value)
            except Exception:
                return False
            if 10 <= set_temp <= 30:
                self.state["setpoint"] = set_temp
                return True
            return False

        # unknown attribute
        return False
