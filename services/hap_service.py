"""
Servicio HAP/HomeKit que maneja el Bridge y accesorios
"""
import logging
from typing import Dict
from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver
from zeroconf import InterfaceChoice
from config import HAPConfig

logger = logging.getLogger(__name__)

class HAPService:
    """Servicio HAP/HomeKit"""
    
    def __init__(self):
        self.accessories: Dict[str, object] = {}  # device_id -> accessory
        self.driver: AccessoryDriver
        self.bridge: Bridge


    def initialize(self):
        """Inicializar el servicio HAP"""
        logger.info("Inicializando servicio HAP...")
        
        # Crear driver
        
        self.driver = AccessoryDriver(
            address = HAPConfig().address,
            port= HAPConfig().port,
            pincode = HAPConfig().pincode,
            persist_file = HAPConfig().persist_file_name,
            listen_address = HAPConfig().listen_address,
            interface_choice=InterfaceChoice.Default,
        )
        
        # Crear bridge
        self.bridge = Bridge(self.driver, HAPConfig().bridge_name)
        
        logger.info("HAP Bridge creado: %s", HAPConfig().bridge_name)
        logger.info("  Puerto: %d", HAPConfig().port)
        logger.info("  PIN Code: %s", HAPConfig().pincode)
    def add_accessory(self, device_id: str, accessory):
        """
        Agregar un accesorio al bridge.
        
        Args:
            device_id: ID único del dispositivo
            accessory: Objeto accesorio HAP
        """
        if device_id in self.accessories:
            logger.warning("Accesorio ya existe en hap service: %s", device_id)
            return False
        
        self.bridge.add_accessory(accessory)
        self.accessories[device_id] = accessory
        
        logger.info("Accesorio agregado a hap service: %s", accessory.display_name)
        return True
    
    def remove_accessory(self, device_id: str):
        """Remover un accesorio del bridge"""
        if device_id not in self.accessories:
            logger.warning("Accesorio no encontrado: %s", device_id)
        
        # HAP no soporta remover accesorios dinámicamente
        # Necesitarías reiniciar el servicio
        logger.warning("Remover accesorios requiere reiniciar el servicio")
        return False
    
    def start(self):
        """Iniciar el servidor HAP"""
        if not self.driver or not self.bridge:
            raise RuntimeError("Servicio HAP no inicializado. Llama a initialize() primero")        
        logger.info("=" * 60)
        logger.info("Iniciando servidor HAP...")
        logger.info("Accesorios registrados: %d", len(self.accessories))
        logger.info("=" * 60)
        
        # Agregar bridge al driver
        self.driver.add_accessory(accessory=self.bridge)
        
        # Configurar signal handler
        #signal.signal(signal.SIGTERM, self.driver.signal_handler)
        
        # Iniciar servidor (bloqueante)
        logger.info("Servidor HAP en ejecución...")
        logger.info("Escanea el código QR en la app Home con PIN: %s", HAPConfig().pincode.decode())
        
        self.driver.start()
    
    def stop(self):
        """Detener el servidor HAP"""
        if self.driver:
            logger.info("Deteniendo servidor HAP...")
            self.driver.stop()
            logger.info("Servidor HAP detenido")