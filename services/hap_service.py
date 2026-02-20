"""
Servicio HAP/HomeKit que maneja el Bridge y accesorios
"""
import logging
from typing import Dict
from pyhap.accessory import Bridge
from pyhap.accessory_driver import AccessoryDriver
from config import config
import configparser

# opcional: limitar Zeroconf a una interfaz específica para evitar errores
try:
    from zeroconf import Zeroconf as _Zeroconf
    import pyhap.accessory_driver as _pyhap_ad
except Exception:
    _Zeroconf = None
    _pyhap_ad = None

logger = logging.getLogger(__name__)

class HAPService:
    """Servicio HAP/HomeKit"""
    conf_parser = configparser.ConfigParser()
    conf_parser.read(config.CONFIG_FILE)
    
    def __init__(self):
        self.accessories: Dict[str, object] = {}  # device_id -> accessory
    
    def initialize(self):
        """Inicializar el servicio HAP"""
        logger.info("Inicializando servicio HAP...")
        
        # Crear driver
        # Si en la configuración existe `listen_address`, forzamos a Zeroconf
        # a usar esa interfaz para evitar intentos por otras (ej. wg0)
        listen_addr = self.conf_parser.get('HAPCONFIG', 'listen_address', fallback=None)
        if listen_addr and _Zeroconf and _pyhap_ad:
            try:
                def _zc_factory(*args, **kwargs):
                    if 'interfaces' not in kwargs:
                        kwargs['interfaces'] = [listen_addr]
                    return _Zeroconf(*args, **kwargs)

                _pyhap_ad.Zeroconf = _zc_factory
                logger.info(f"Zeroconf limitado a la interfaz: {listen_addr}")
            except Exception as e:
                logger.warning(f"No se pudo limitar Zeroconf: {e}")

        self.driver = AccessoryDriver(
            address=self.conf_parser.get('HAPCONFIG', 'address', fallback=None),
            port=self.conf_parser.getint('HAPCONFIG', 'port', fallback=51827),
            pincode=self.conf_parser.get('HAPCONFIG', 'pincode', fallback="031-45-154").encode(),
            persist_file=self.conf_parser.get('HAPCONFIG', 'persist_file_name', fallback="homekit.json"),
            listen_address=listen_addr
        )
        
        # Crear bridge usando el nombre definido en la configuración
        bridge_name = self.conf_parser.get('HAPCONFIG', 'bridge_name', fallback="Mi Raspberry Hub")
        self.bridge = Bridge(self.driver, bridge_name)
        
        logger.info(f"HAP Bridge creado: Mi Raspberry Hub")
        logger.info(f"  Puerto: {self.conf_parser.getint('HAPCONFIG', 'port', fallback=51827)}")
        logger.info(f"  PIN Code: {self.conf_parser.get('HAPCONFIG', 'pincode', fallback='031-45-154')}")
    
    def add_accessory(self, device_id: str, accessory):
        """
        Agregar un accesorio al bridge.
        
        Args:
            device_id: ID único del dispositivo
            accessory: Objeto accesorio HAP
        """
        if device_id in self.accessories:
            logger.warning(f"Accesorio ya existe: {device_id}")
            return False
        
        self.bridge.add_accessory(accessory)
        self.accessories[device_id] = accessory
        
        logger.info(f"Accesorio agregado: {accessory.display_name}")
        return True
    
    def remove_accessory(self, device_id: str):
        """Remover un accesorio del bridge"""
        if device_id not in self.accessories:
            logger.warning(f"Accesorio no encontrado: {device_id}")
            return False
        
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
        logger.info(f"Accesorios registrados: {len(self.accessories)}")
        logger.info("=" * 60)
        
        # Agregar bridge al driver
        self.driver.add_accessory(accessory=self.bridge)
        
        # Configurar signal handler
        #signal.signal(signal.SIGTERM, self.driver.signal_handler)
        
        # Iniciar servidor (bloqueante)
        logger.info("Servidor HAP en ejecución...")
        logger.info(f"Escanea el código QR en la app Home con PIN: {self.conf_parser.get('HAPCONFIG', 'pincode', fallback='031-45-154')}")
        
        self.driver.start()
    
    def stop(self):
        """Detener el servidor HAP"""
        if self.driver:
            logger.info("Deteniendo servidor HAP...")
            self.driver.stop()
            logger.info("Servidor HAP detenido")