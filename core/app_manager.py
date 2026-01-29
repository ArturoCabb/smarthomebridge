from asyncio.log import logger
import threading
from core.plugin_manager import PluginManager
from core.device_manager import DeviceManager
from services.hap_service import HAPService
from bridges.hap_bridge import HAPBridge

class AppManager:
    """Gestor principal de la aplicación"""
    
    def __init__(self):
        self.plugin_manager = PluginManager()
        self.device_manager = DeviceManager(self.plugin_manager)
        
        # Servicios
        self.hap_service = HAPService()
        
        # Bridges
        self.hap_bridge = None

    def _homekit(self):
        """Ejecutar HomeKit en un hilo separado con manejo de errores"""
        try:
            # 3. Inicializar HAP Service
            logger.info("\n3. Inicializando HAP Service...")
            self.hap_service.initialize()
            
            # 4. Crear HAP Bridge
            logger.info("\n4. Conectando dispositivos a HomeKit...")
            self.hap_bridge = HAPBridge(self.device_manager, self.hap_service)
            
            # Agregar cada dispositivo al bridge
            for device_state in self.device_manager.get_all_devices():
                self.hap_bridge.add_device(device_state)
            
            logger.info("Iniciando HAP Service...")
            self.hap_service.start()
            
        except Exception as e:
            logger.error(f"Error crítico en HomeKit: {e}", exc_info=True)
            raise
    
    def initialize(self):
        """Inicializar aplicación"""
        logger.info("=" * 60)
        logger.info("INICIALIZANDO HOMEBRIDGE HAP")
        logger.info("=" * 60)
        
        # 1. Descubrir dispositivos
        logger.info("\n1. Descubriendo dispositivos...")
        discovered = self._discover_all_devices()
        
        if not discovered:
            logger.warning(" No se encontraron dispositivos")
            return False
        
        logger.info(f"Encontrados {len(discovered)} dispositivos")
        
        # 2. Agregar dispositivos al Device Manager
        logger.info("\n2. Agregando dispositivos al Device Manager...")
        for device_info in discovered:
            self.device_manager.add_device(device_info)
        
        logger.info("\nINICIALIZACIÓN COMPLETADA")
        return True
    
    def _discover_all_devices(self):
        """Descubrir dispositivos de todos los plugins"""
        all_discovered = []
        
        for plugin in self.plugin_manager.get_all_plugins():
            try:
                plugin.get_api_client()
                discovered = plugin.discover_devices()
                logger.info(f"  {plugin.brand.upper()}: {len(discovered)} dispositivos")
                all_discovered.extend(discovered)
            except Exception as e:
                logger.error(f"Error con {plugin.brand}: {e}")
        
        return all_discovered
    
    def start(self):
        """Iniciar aplicación"""
        if not self.initialize():
            return False
        thread = threading.Thread(target=self._homekit, daemon=False, name="HomeKit")
        
        # Iniciar sincronización
        logger.info("\n5. Iniciando sincronización...")
        self.device_manager.start_sync(interval=30)
        
        # Iniciar HAP en el hilo
        logger.info("\n6. Iniciando HomeKit en hilo separado...")
        thread.start()
        
        # Mantener vivo el programa principal
        try:
            while True:
                thread.join(timeout=1)
                if not thread.is_alive():
                    logger.error("HomeKit thread se detiene inesperadamente")
                    break
        except KeyboardInterrupt:
            logger.info("Interrupción del usuario")
    
    def stop(self):
        """Detener aplicación"""
        self.device_manager.stop_sync()
        self.hap_service.stop()