import requests
import logging
from typing import List, Optional, Dict, Any

from brandconnectors.base_client import BaseClient

logger = logging.getLogger(__name__)

class LGDeviceOfflineError(Exception):
    """Excepción cuando el dispositivo está offline/apagado"""
    pass

class LGThinQClient(BaseClient):
    """Cliente para la API de LG ThinQ"""
    
    
    def __init__(self, base_url: str, access_token: str, meessage_id: str, client_id: str):
        """
        Inicializar cliente.
        
        Args:
            access_token: Token de autenticación OAuth2
        """
        self.BASE_URL = base_url
        self.access_token = access_token
        self.session = requests.Session()
        
        # Headers requeridos
        self.session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'x-message-id': meessage_id,
            'x-country': 'MX',
            'x-client-id': client_id,
            'x-api-key': 'v6GFvkweNo7DK7yD3ylIZ9w52aKBU0eJ7wLXkSR3'
        })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Realizar petición HTTP.
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Endpoint de la API (ej: '/devices/123/state')
            params: Query parameters
            json_data: Body JSON
            
        Returns:
            Respuesta JSON
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            logger.info(f"{method} {url}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                timeout=30
            )
            
            # Log de respuesta
            logger.debug(f"Status: {response.status_code}")
            logger.debug(f"Response: {response.text[:200]}")
            
            # Verificar errores
            if response.status_code == 416:
                raise LGDeviceOfflineError
            response.raise_for_status()
            
            return response.json()
        except LGDeviceOfflineError:
            logger.warning(f"Recurso no disponible (416) para {url}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición: {e}")
            raise
    
    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        """
        Obtiene el estado de CUALQUIER dispositivo.
        
        Args:
            device_id: ID del dispositivo (puede ser lavadora, TV, etc.)
            
        Returns:
            Diccionario con el snapshot (JSON crudo)
        """
        try:
            response = self._make_request('GET', f'/devices/{device_id}/state')
        
            # Retorna el snapshot crudo, sin parsearlo
            return response.get('response', [])[0]
        except LGDeviceOfflineError:
            return {}
        except Exception as e:
            logger.error(f"Error al obtener estado de {device_id}: {e}")
            return {}
    
    def get_device_profile(self, device_id: str) -> Dict[str, Any]:
        """
        Obtiene el perfil de CUALQUIER dispositivo.
        """
        response = self._make_request('GET', f'/devices/{device_id}/profile')
        return response.get('response', {})
    
    def send_command(self, device_id: str, command_data: Dict[str, Any]) -> bool:
        """
        Envía comando a CUALQUIER dispositivo.
        """
        try:
            response = self._make_request('POST', f'/devices/{device_id}/control', json_data=command_data)
            return response.get("response") == {}
        except LGDeviceOfflineError:
            logger.warning(f"No se pudo enviar el comando {device_id}")
            return False
        except Exception as e:
            logger.error(f"Error al enviar comando a {device_id}: {e}")
            return False
    
    def get_devices_list(self) -> List[Dict[str, Any]]:
        """
        Lista TODOS los dispositivos de la cuenta (lavadoras, TVs, refrigeradores, etc.)
        """
        response = self._make_request('GET', '/devices')
        return response.get('response', [])