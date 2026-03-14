from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseDeviceProfile(ABC):
    """Perfil base de cualquier dispositivo"""
    @abstractmethod
    def from_json(cls, json_data: Dict[str, Any]) -> Any:
        pass

class BaseDeviceState(ABC):
    """Estado base de cualquier dispositivo"""
    @abstractmethod
    def from_json(cls, json_data: Dict[str, Any]) -> Any:
        pass
    
    @abstractmethod
    def is_online(self) -> bool:
        pass

class BaseDevice(ABC):
    """Dispositivo base abstracto"""
    
    def __init__(self, device_data: Dict[str, Any]):
        self.device_id = device_data.get('device_id')
        self.name = device_data.get('alias', 'Device')
        self.model = device_data.get('model', 'Unknown')
        self.brand = device_data.get('brand', 'unknown')
        self.device_type = device_data.get('device_type', 'unknown')
        self.raw_data = device_data

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', type='{self.device_type}')>"
    
    @abstractmethod
    def get_profile(self) -> BaseDeviceProfile:
        pass
    
    @abstractmethod
    def get_state(self) -> BaseDeviceState:
        pass
    
    @abstractmethod
    def send_command(self, command: dict) -> bool:
        pass