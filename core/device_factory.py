from core.plugin_manager import PluginManager
from models.base import BaseDevice


class DeviceFactory:
    """Fábrica para crear dispositivos de cualquier marca"""
    
    def __init__(self, plugin_manager: PluginManager):
        self.plugin_manager = plugin_manager
    
    #def create_from_db(self, db_record) -> BaseDevice:
    #    """
    #    Crear dispositivo desde registro de base de datos.
    #    
    #    El registro debe tener:
    #    - brand: "lg", "samsung", etc.
    #    - device_type: "washer", "tv", etc.
    #    - device_id: ID único
    #    - configuracion: JSON con datos específicos
    #    """
    #    
    #    brand = db_record.configuracion.get('brand', '').lower()
    #    device_type = db_record.tipo.lower()
    #    
    #    # Obtener plugin apropiado
    #    plugin = self.plugin_manager.get_plugin(brand)
    #    if not plugin:
    #        raise ValueError(f"No hay plugin para marca: {brand}")
    #    
    #    # Preparar datos del dispositivo
    #    device_data = {
    #        'uuid': db_record.uuid,
    #        'device_id': db_record.configuracion.get('device_id'),
    #        'name': db_record.nombre,
    #        'model': db_record.modelo,
    #        'brand': brand,
    #        'device_type': device_type
    #    }
    #    
    #    # Crear dispositivo usando el plugin
    #    return plugin.create_device(device_type, device_data)
    
    def create_from_discovery(self, brand: str, device_info: dict) -> BaseDevice:
        """Crear dispositivo desde descubrimiento"""
        
        plugin = self.plugin_manager.get_plugin(brand)
        if not plugin:
            raise ValueError(f"No hay plugin para marca: {brand}")
        
        return plugin.create_device(device_info['device_type'], device_info)