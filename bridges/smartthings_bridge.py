"""
SMARTTHINGS Bridge - Traduce entre DeviceManager y SMARTTHINGS Service
"""
import logging
from typing import Dict
from core.device_manager import DeviceManager, DeviceState
from services.smartthings_service import SmartThingsService
from bridges.smartthings.LGWasherAccessory import LGWasherAccessory
from json import loads

logger = logging.getLogger(__name__)

class SmartThingsBridge:
    """
    Bridge que conecta DeviceManager con SMARTTHINGS Service.
    Traduce estados de dispositivos a accesorios SMARTTHINGS.
    """
     
    def __init__(self, device_manager: DeviceManager, smartthings_service: SmartThingsService):
        self.device_manager = device_manager
        self.smartthings_service = smartthings_service

        # Mapeo: device_id -> accessory HAP
        self.accessories: Dict[str, object] = {}
    
    def add_device(self, device_state: DeviceState):
        """
        Agregar un dispositivo al bridge HAP.
        
        Args:
            device_state: Estado del dispositivo
        """
        device_id = device_state.device_id
        
        if device_id in self.accessories:
            logger.warning(f"Accessory ya existe para {device_id}")
            return
        
        # Crear accessory HAP según el tipo de dispositivo
        accessory = self._create_accessory(device_state)
        
        if accessory:
            # Agregar al servicio HAP
            self.smartthings_service.add_accessory(device_id, accessory)
            self.accessories[device_id] = accessory
            
            # Suscribirse a cambios de estado
            self.device_manager.subscribe_to_device(
                device_id,
                lambda ds: self._on_device_state_changed(ds)
            )
            
            logger.info(f"Dispositivo {device_state.name} agregado a HAP")

    def _create_accessory(self, device_state: DeviceState):
        """
        Factory para crear accessory HAP según tipo de dispositivo.
        
        Args:
            device_state: Estado del dispositivo
            
        Returns:
            Accessory HAP o None
        """
        brand = device_state.brand.lower()
        device_type = device_state.device_type.lower()
        
        # Importar el accessory correspondiente
        if brand == 'lg' and 'washer' in device_type:
            print("Device id de LG para coincidir con del del accesorio para smartthings " + device_state.device_id)
            smartthings_device_conf = open(self.smartthings_service.devies_config_file, "r")
            dat_file = smartthings_device_conf.read()
            smartthings_device_conf.close()
            dat_file = loads(dat_file)
            for device in dat_file["devices"]:
                if device["externalDeviceId"] == device_state.device_id:
                    print("Device id de LG coincide con el del accesorio para smartthings " + device_state.device_id)
                    access = LGWasherAccessory(
                        external_device_id=device["externalDeviceId"],
                        friendly_name=device["friendlyName"],
                        device_handler_type=device["deviceHandlerType"],
                        manufacturer_name=device["manufacturerName"],
                        model_name=device["modelName"],
                        hw_version=device["hwVersion"],
                        sw_version=device["swVersion"],
                        room_name=device["roomName"],
                        groups=device["groups"],
                        categories=device["categories"]
                    )
                    access.set_device_manager(self.device_manager)  # ✅ Inyectar el manager
                    access.set_smartthings_service(self.smartthings_service)  # ✅ Inyectar el servicio
                    return access
        
        # Agregar más tipos de dispositivos aquí
        
        logger.warning(f"No hay accessory HAP para {brand} {device_type}")
        return None
    
    def _on_device_state_changed(self, device_state: DeviceState):
        """
        Callback cuando cambia el estado de un dispositivo.
        Actualiza el accessory HAP correspondiente.
        
        Args:
            device_state: Nuevo estado del dispositivo
        """
        device_id = device_state.device_id
        accessory = self.accessories.get(device_id)
        
        if accessory and hasattr(accessory, 'update_from_device_state'):
            try:
                accessory.update_from_device_state(device_state) # Esta es la funcion que se llmam a que le dice al servicio hap que en telefono pinte el estado del dispositivo
            except Exception as e:
                pass