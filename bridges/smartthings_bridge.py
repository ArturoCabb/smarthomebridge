"""
SMARTTHINGS Bridge - Traduce entre DeviceManager y SMARTTHINGS Service
"""

import logging
import json
from typing import Dict, Optional
from pathlib import Path
from bridges.smartthings.LGWasherAccessory import LGWasherAccessory
from core.device_manager import DeviceManager, DeviceState
from requests import post as send_req
from uuid import uuid4

logger = logging.getLogger(__name__)

class SmartThingsBridge:
    """
    Bridge que conecta DeviceManager con SMARTTHINGS Service.
    Traduce estados de dispositivos a accesorios SMARTTHINGS.
    """

    CONFIG_FILE = ".smarthome/smartthings_device_conf.json"

    def __init__(self, device_manager: DeviceManager, smartthings_service):
        self.device_manager = device_manager
        self.smartthings_service = smartthings_service

        # Mapeo: device_id -> accessory SmartThings
        self.accessories: Dict[str, object] = {}

        # Cargar configuración de dispositivos
        self.config = self._load_config()

        # Configurar callback en el webhook
        if smartthings_service and smartthings_service.webhook:
            smartthings_service.webhook.on_device_event = self._on_device_event

    def _load_config(self) -> Dict:
        """
        Cargar configuración de dispositivos desde archivo JSON.

        Returns:
            Dict con configuración de dispositivos
        """
        try:
            config_path = Path(self.CONFIG_FILE)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo cargar configuración: {e}")

        return {"devices": []}

    def add_device(self, device_state: DeviceState):
        """
        Agregar un dispositivo al bridge SmartThings.

        Args:
            device_state: Estado del dispositivo
        """
        device_id = device_state.device_id

        if device_id in self.accessories:
            logger.warning(f"Accesorio ya existe para {device_id}")
            return

        # Crear accesorio SmartThings según el tipo de dispositivo
        accessory = self._create_accessory_from_config(device_state)

        if accessory:
            # Guardar accesorio
            self.accessories[device_id] = accessory

            # Suscribirse a cambios del DeviceManager
            self.device_manager.subscribe_to_device(
                device_id,
                lambda ds: self._on_device_state_changed(ds)
            )

            logger.info(f"Dispositivo {device_state.name} agregado a SmartThings bridge")

    def _create_accessory_from_config(self, device_state: DeviceState) -> Optional[object]:
        """
        Factory para crear accesorio SmartThings según tipo de dispositivo.
        Combina información de configuración + información del dispositivo.

        Args:
            device_state: Estado del dispositivo

        Returns:
            Accesorio SmartThings o None
        """
        # Buscar configuración del dispositivo en el archivo
        # Con pattern matching: Brand_DeviceType_device_ID
        device_config = self._find_device_config(device_state.device_id, device_state.brand)
        if not device_config:
            logger.warning(f"No hay configuración para {device_state.device_id}")
            return None

        device_type = device_config.get('deviceType', '').lower()
        brand = device_state.brand.lower()

        # Factory para crear accesorios según brand + device_type
        if brand == 'lg':
            if 'washer' in device_type:
                try:
                    accessory = LGWasherAccessory(
                        external_device_id=device_config.get('externalDeviceId', device_state.device_id),
                        friendly_name=device_config.get('friendlyName', device_state.name),
                        device_handler_type=device_config.get('deviceHandlerType', ''),
                        manufacturer_name=device_config.get('manufacturerName', device_state.brand),
                        model_name=device_config.get('modelName', device_state.model),
                        hw_version=device_config.get('hwVersion', 'v1'),
                        sw_version=device_config.get('swVersion', '0.0.1'),
                        room_name=device_config.get('roomName', 'cuarto de lavado'),
                        groups=device_config.get('groups', ['washer']),
                        categories=device_config.get('categories', ['washer']),
                        device_cookie=device_config.get('deviceCookie', {})
                    )

                    # Actualizar estado inicial del accesorio
                    if device_state.state:
                        accessory.update_from_device_state(device_state)
                    if accessory:
                        accessory.set_device_manager(self.device_manager)
                    return accessory

                except Exception as e:
                    logger.error(f"Error creando LGWasher accesorio: {e}")
        
        logger.warning(f"No hay accesorio SmartThings para {brand} {device_type}")
        return None

    def _find_device_config(self, device_id: str, brand: str = None) -> Optional[Dict]:
        """
        Buscar configuración de un dispositivo en el archivo de configuración.
        Soporta búsqueda por:
        1. Pattern-based: Brand_DeviceType_device_ID (ej: LG_Washer_device_abc123)
        2. Fallback: externalDeviceId exacto

        Args:
            device_id: ID del dispositivo
            brand: Marca del dispositivo (opcional, para pattern matching)

        Returns:
            Dict con configuración o None
        """
        devices = self.config.get('devices', [])

        # Buscar por pattern matching si brand está disponible
        if brand:
            brand_upper = brand.upper()
            for device_config in devices:
                external_id = device_config.get('externalDeviceId', '')
                # Patrón: Brand_DeviceType_device_ID
                if external_id.startswith(f'{brand_upper}_'):
                    if device_id in external_id:
                        logger.info(f"Config encontrada por pattern: {external_id}")
                        return device_config

        # Fallback: búsqueda exacta por externalDeviceId
        for device_config in devices:
            if device_config.get('externalDeviceId') == device_id:
                logger.info(f"Config encontrada por ID exacto: {device_id}")
                return device_config

        logger.warning(f"No hay configuración para {brand}_{device_id} o {device_id}")
        return None

    def _on_device_state_changed(self, device_state: DeviceState):
        """
        Callback cuando cambia el estado de un dispositivo en el DeviceManager.
        Actualiza el accesorio SmartThings correspondiente.

        Args:
            device_state: Nuevo estado del dispositivo
        """
        device_id = device_state.device_id
        accessory = self.accessories.get(device_id)

        if accessory and hasattr(accessory, 'update_from_device_state'):
            try:
                accessory.update_from_device_state(device_state)

                # Notificar a SmartThings API sobre el cambio
                self._notify_smartthings(accessory)

            except Exception as e:
                logger.error(f"Error actualizando accesorio {device_id}: {e}")

    def _on_device_event(self, device_id: str, state):
        """
        Callback cuando SmartThings notifica un cambio via webhook.

        Args:
            device_id: ID del dispositivo
            state: Nuevo estado recibido de SmartThings
        """
        logger.info(f"Evento de SmartThings para {device_id}")

        # Convertir a dict y actualizar en DeviceManager
        if hasattr(state, 'to_dict'):
            state_dict = state.to_dict()
        else:
            state_dict = state

        self.device_manager.update_device_state(device_id, state_dict)

    def _notify_smartthings(self, accessory: object, retry: bool = True):
        """
        Notificar a SmartThings cuando cambia un dispositivo localmente.
        Con soporte para token refresh automático en caso de expiración.

        Args:
            accessory: Accesorio que cambió
            retry: Si es True, reintentar después de refresh de token en caso de 401/403
        """
        if not self.smartthings_service or not hasattr(accessory, 'send_device_status'):
            return

        try:
            # Obtener token de configuración
            token_from_smartthings = self.smartthings_service.get_access_token()
            callback_url = self.smartthings_service.get_callback_url()

            if not token_from_smartthings or not callback_url:
                logger.warning("Token o callback URL no disponible para SmartThings")
                return

            message = {
                "headers": {
                    "schema": "st-schema",
                    "version": "1.0",
                    "interactionType": "stateCallback",
                    "requestId": str(uuid4())
                },
                "authentication": {
                    "tokenType": "Bearer",
                    "token": token_from_smartthings
                },
                "deviceState": [
                    accessory.send_device_status()
                ]
            }

            result = send_req(callback_url, json=message)

            # Manejo de token expirado
            if result.status_code in [401, 403] and retry:
                logger.warning(f"Token expirado (HTTP {result.status_code}), intentando renovar...")

                if self.smartthings_service._refresh_access_token():
                    logger.info("Token renovado exitosamente, reintentando notificación...")
                    # Reintentar sin volver a intentar para evitar loop infinito
                    self._notify_smartthings(accessory, retry=False)
                else:
                    logger.error("No se pudo renovar token de SmartThings")
            else:
                logger.info(f"Notificación enviada a SmartThings: {result.status_code}")

        except Exception as e:
            logger.error(f"Error notificando a SmartThings: {e}")