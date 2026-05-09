from abc import abstractmethod
from typing import Any, Dict, List

class BaseClient:
    """Cliente base para APIs de marcas"""

    @abstractmethod
    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """Obtener el estado de un dispositivo."""
        pass

    @abstractmethod
    def get_device_profile(self, device_id: str) -> Dict[str, Any]:
        """Obtener el perfil de un dispositivo."""
        pass

    @abstractmethod
    def send_command(self, device_id: str, command_data: Dict[str, Any]) -> bool:
        """Enviar un comando a un dispositivo."""
        pass

    @abstractmethod
    def get_devices_list(self) -> List[Dict[str, Any]]:
        """Obtener la lista de dispositivos."""
        pass