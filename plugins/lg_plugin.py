from asyncio.log import logger
from typing import Any, Dict, List
from brandconnectors.lg_client import LGThinQClient
from models.LG.washer import LGwasher, WasherState
from plugins.base_plugin import BasePlugin
from config import LGClientConfig


class LGPlugin(BasePlugin):
    brand = "lg"

    def __init__(self) -> None:
        super().__init__()
        self.client: LGThinQClient

    def get_supported_devices(self):
        return ["washer", "refrigerator", "air_conditioner", "tv"]

    def get_api_client(self) -> LGThinQClient:
        self.client = LGThinQClient(
            LGClientConfig.base_url,
            LGClientConfig.access_token,
            LGClientConfig.message_id,
            LGClientConfig.client_id,
        )
        return self.client

    def create_device(self, device_type: str, device_data: dict):
        """Factory para crear dispositivo LG según tipo"""

        device_map = {
            "DEVICE_WASHER": LGwasher,
        }

        device_class = device_map.get(device_type.lower())
        if not device_class:
            raise ValueError(f"Tipo de dispositivo no soportado: {device_type}")

        return device_class(device_data)

    def discover_devices(self) -> List[dict]:
        """Obtener lista de dispositivos LG"""
        client = self.client
        response = client.get_devices_list()  # Llama a la API

        # Transformar respuesta API a formato estándar
        devices = []
        for item in response:
            devices.append(
                {
                    "device_id": item["deviceId"],
                    "device_type": item["deviceInfo"]["deviceType"].upper(),
                    "model": item["deviceInfo"]["modelName"],
                    "alias": item["deviceInfo"]["alias"],
                    "brand": self.brand,
                }
            )

        return devices

    def get_device_state(self, device_id: str, device_type: str) -> Dict:
        """
        Obtener estado actual de un dispositivo.

        Args:
            device_id: ID del dispositivo
            device_type: Tipo de dispositivo

        Returns:
            Estado parseado según el tipo
        """
        try:
            client = self.client
            snapshot = client.get_device_state(device_id)
            if "DEVICE_WASHER" == device_type:
                return WasherState.from_json(snapshot)
            else:
                logger.warning("Estado no parseado para tipo: %s", device_type)
                return snapshot

        except Exception as e:
            pass

    def send_command(
        self,
        device_id: str,
        command_data: Dict[str, Any],
        credentials: Dict[str, Any] | None = None,
    ) -> bool:
        """
        Enviar comando a un dispositivo.

        Args:
            device_id: ID del dispositivo
            device_type: Tipo de dispositivo
            command_data: Datos del comando
            credentials: Credenciales

        Returns:
            True si se envió correctamente
        """
        try:
            client = self.client
            print(device_id)
            print(command_data)
            return client.send_command(device_id, command_data)

        except Exception as e:
            logger.error("Error al enviar comando a %s: %s", device_id, e, exc_info=True)
            return False
