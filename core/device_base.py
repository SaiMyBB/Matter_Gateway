from abc import ABC, abstractmethod

class BaseDevice(ABC):
    def __init__(self, name, device_type):
        self.name = name
        self.device_type = device_type
        self.state = {}

    @abstractmethod
    def read_state(self):
        pass

    @abstractmethod
    def write_state(self, attribute, value):
        pass
