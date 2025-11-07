class MatterGateway:
    def __init__(self):
        self.devices = {}

    def register_device(self, device):
        self.devices[device.name] = device

    def get_device(self, name):
        return self.devices.get(name)

    def get_all_devices(self):
        return {name: dev.read_state() for name, dev in self.devices.items()}
