"""
HAP Bridge - Traduce entre DeviceManager y HAP Service
"""
import logging
from typing import Dict
from bridges.homekit.LGWasherAccessory import LGWasherAccessory
from core.device_manager import DeviceManager, DeviceState

logger = logging.getLogger(__name__)

class HAPBridge:
    """
    Bridge que conecta DeviceManager con HAP Service.
    Traduce estados de dispositivos a accesorios HAP.
    """
    
    def __init__(self, device_manager: DeviceManager, hap_service):
        self.device_manager = device_manager
        self.hap_service = hap_service
        
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
            self.hap_service.add_accessory(device_id, accessory)
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
            
            return LGWasherAccessory(
                driver=self.hap_service.driver,
                display_name=device_state.name,
                device_id=device_state.device_id,
                device_manager=self.device_manager  # ✅ Pasa el manager
            )
        
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
                accessory.update_from_device_state(device_state)
                logger.debug(f"Accessory HAP actualizado: {device_state.name}")
            except Exception as e:
                logger.error(f"Error actualizando accessory: {e}")