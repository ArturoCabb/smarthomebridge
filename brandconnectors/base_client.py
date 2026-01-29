from abc import abstractmethod
from typing import Any, Dict, List

class BaseClient:
    """Cliente base para APIs de marcas"""
    
    def __init__(self):
        pass

    @abstractmethod
    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_device_profile(self, device_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def send_command(self, device_id: str, command_data: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def get_devices_list(self) -> List[Dict[str, Any]]:
        pass