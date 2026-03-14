from abc import abstractmethod, ABC

class BaseService(ABC):
    @abstractmethod
    def initialize(self):
        pass

    def add_accessory(self, device_id: str, accessory):
        pass

    def start(self):
        pass

    def stop(self):
        pass