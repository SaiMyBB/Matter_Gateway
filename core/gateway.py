# core/gateway.py
from typing import Dict
from core.persistence import Persistence

class MatterGateway:
    def __init__(self, broadcaster=None):
        # devices: name -> device instance
        self.devices: Dict[str, object] = {}
        self.persistence = Persistence()
        self.broadcaster = broadcaster  # callback to broadcast update events
        self._restore_states()

    def register_device(self, device):
        self.devices[device.name] = device
        # If we have persisted state for this device, restore attrs
        persisted = self.persistence.load_all()
        dev_state = persisted.get(device.name)
        if dev_state:
            for k, v in dev_state.items():
                # attempt to write state on device
                try:
                    device.write_state(k, v)
                except Exception:
                    pass

    def get_device(self, name):
        return self.devices.get(name)

    def get_all_devices(self):
        return {name: dev.read_state() for name, dev in self.devices.items()}

    def set_device_attribute(self, name, attribute, value):
        device = self.get_device(name)
        if not device:
            return False, "device_not_found"
        ok = device.write_state(attribute, value)
        if not ok:
            return False, "invalid_attribute_or_value"
        # persist whole state
        self._persist_device_state(name)
        # broadcast update if broadcaster provided
        if self.broadcaster:
            try:
                self.broadcaster({
                    "event": "update",
                    "dev": name,
                    "attr": attribute,
                    "val": value
                })
            except Exception:
                pass
        return True, None

    def _persist_device_state(self, name):
        all_data = self.persistence.load_all()
        device = self.get_device(name)
        if device:
            all_data[name] = device.read_state()
            self.persistence.save_all(all_data)

    def _restore_states(self):
        # no devices yet at init; this will be applied at register_device time
        pass
