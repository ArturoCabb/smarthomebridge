# plugins/lg_plugin.py

from asyncio.log import logger
from pathlib import Path
from typing import Any, Dict, List
from brandconnectors.lg_client import LGThinQClient
from models.LG.washer import LGwasher, WasherState
from plugins.base_plugin import BasePlugin
from configparser import ConfigParser


class LGPlugin(BasePlugin):
    brand = "lg"

    def __init__(self) -> None:
        super().__init__()
        self.client: LGThinQClient
    
    def get_supported_devices(self):
        return ['washer', 'refrigerator', 'air_conditioner', 'tv']
    
    def get_api_client(self) -> LGThinQClient:
        CONFIG_DIR = './.smarthome/'
        CONFIG_FILE = CONFIG_DIR + 'config.conf'
        config_parser = ConfigParser()
        config_parser.read(CONFIG_FILE, encoding='utf-8')
        self.client = LGThinQClient(config_parser.get('LG','base_url'), config_parser.get('LG','access_token'), config_parser.get('LG','message_id'), config_parser.get('LG','client_id'))
        return self.client
    
    def create_device(self, device_type: str, device_data: dict):
        """Factory para crear dispositivo LG según tipo"""
        
        device_map = {
            'DEVICE_WASHER': LGwasher,
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
            devices.append({
                'device_id': item['deviceId'],
                'device_type': item['deviceInfo']['deviceType'].upper(),
                'model': item['deviceInfo']['modelName'],
                'alias': item['deviceInfo']['alias'],
                'brand': self.brand
            })
        
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
            #print(snapshot)
            # Parsear según tipo
            if 'DEVICE_WASHER' == device_type:
                return WasherState.from_json(snapshot)
            else:
                logger.warning(f"Estado no parseado para tipo: {device_type}")
                return snapshot
                
        except Exception as e:
            logger.error(f"Error al obtener estado de {device_id}: {e}")
            return None
        
    def send_command(self, device_id: str, command_data: Dict[str, Any], credentials: Dict[str, Any] | None = None) -> bool:
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
            logger.error(f"Error al enviar comando a {device_id}: {e}")
            return False