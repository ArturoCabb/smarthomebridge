from abc import abstractmethod
from typing import Any, Dict, List


class BasePlugin:
    """Plugin base para cada marca"""
    
    brand: str = None  # "lg", "samsung", etc.
    
    @abstractmethod
    def get_supported_devices(self) -> List[str]:
        """Retorna tipos de dispositivos soportados: ['washer', 'tv', ...]"""
        pass
    
    @abstractmethod
    def get_api_client(self) -> object:
        """Retorna cliente API para esta marca"""
        pass
    
    @abstractmethod
    def create_device(self, device_type: str, device_data: dict)-> object:
        """Factory method para crear dispositivo específico"""
        pass
    
    @abstractmethod
    def discover_devices(self) -> List[dict]:
        """Descubrir dispositivos de esta marca"""
        pass

    @abstractmethod
    def get_device_state(self, device_id: str, device_type: str) -> Dict:
        pass

    @abstractmethod
    def send_command(self, device_id: str, command_data: Dict[str, Any], credentials: Dict[str, Any] | None = None) -> bool:
        pass