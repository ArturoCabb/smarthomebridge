"""
Device Manager - Núcleo central del sistema.
Mantiene el estado de todos los dispositivos y coordina entre plugins y servicios.
"""
import logging
import threading
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DeviceState:
    """Estado de un dispositivo (agnóstico de marca/protocolo)"""
    device_id: str
    brand: str
    device_type: str
    name: str
    model: str
    
    # Estado actual (parsado del plugin)
    state: Dict = field(default_factory=dict)
    
    # Metadata
    online: bool = True
    last_update: datetime = field(default_factory=datetime.now)
    
    # Callbacks cuando cambia el estado
    callbacks: List[Callable] = field(default_factory=list)

class DeviceManager:
    """
    Gestor central de dispositivos.
    Mantiene el estado de todos los dispositivos y coordina comunicación.
    """
    
    def __init__(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.devices: Dict[str, DeviceState] = {}  # device_id -> DeviceState
        
        self._sync_thread = None
        self._running = False
        self._sync_interval = 30  # segundos
        
        self._lock = threading.Lock()
    
    def add_device(self, device_info: Dict) -> DeviceState:
        """
        Agregar un dispositivo al manager.
        
        Args:
            device_info: Información del dispositivo desde plugin
            
        Returns:
            DeviceState creado
        """
        device_id = device_info['device_id']
        
        with self._lock:
            if device_id in self.devices:
                logger.warning(f"Dispositivo {device_id} ya existe")
                return self.devices[device_id]
            
            device_state = DeviceState(
                device_id=device_id,
                brand=device_info['brand'],
                device_type=device_info['device_type'],
                name=device_info.get('alias', 'Device'),
                model=device_info.get('model', 'Unknown'),
            )
            
            self.devices[device_id] = device_state
            
            logger.info(f"Dispositivo agregado: {device_state.name}")
            
            return device_state
    
    def get_device(self, device_id: str) -> Optional[DeviceState]:
        """Obtener un dispositivo por ID"""
        return self.devices.get(device_id)
    
    def get_all_devices(self) -> List[DeviceState]:
        """Obtener todos los dispositivos"""
        return list(self.devices.values())
    
    def subscribe_to_device(self, device_id: str, callback: Callable):
        """
        Suscribirse a cambios de estado de un dispositivo.
        
        Args:
            device_id: ID del dispositivo
            callback: Función a llamar cuando cambie el estado
                      Firma: callback(device_state: DeviceState)
        """
        device = self.get_device(device_id)
        if device:
            device.callbacks.append(callback)
    
    def update_device_state(self, device_id: str, new_state: Dict):
        """
        Actualizar el estado de un dispositivo.
        Notifica a todos los callbacks suscritos.
        
        Args:
            device_id: ID del dispositivo
            new_state: Nuevo estado (dict parseado del plugin)
        """
        with self._lock:
            device = self.get_device(device_id)
            if not device:
                logger.warning(f"Dispositivo {device_id} no encontrado")
                return
            
            # Actualizar estado
            device.state = new_state
            #print(device.state)
            device.last_update = datetime.now()
            
            # Notificar a callbacks
            for callback in device.callbacks:
                try:
                    callback(device)
                except Exception as e:
                    logger.error(f"Error en callback: {e}")
    
    def send_command(self, device_id: str, command_data: Dict) -> bool:
        """
        Enviar comando a un dispositivo.
        
        Args:
            device_id: ID del dispositivo
            command_data: Datos del comando (formato genérico)
            
        Returns:
            True si se envió correctamente
        """
        device = self.get_device(device_id)
        if not device:
            logger.error(f"Dispositivo {device_id} no encontrado")
            return False
        
        # Obtener plugin correspondiente
        plugin = self.plugin_manager.get_plugin(device.brand)
        if not plugin:
            logger.error(f"Plugin no encontrado para {device.brand}")
            return False
        
        # Enviar comando a través del plugin
        try:
            success = plugin.send_command(
                device_id=device_id,
                command_data=command_data
            )
            
            if success:
                logger.info(f"Comando enviado a {device.name}")
                # Sincronizar estado inmediatamente
                self._sync_device(device_id)
            else:
                logger.error(f"Error enviando comando a {device.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error enviando comando: {e}")
            return False
    
    def start_sync(self, interval: int = 30):
        """
        Iniciar sincronización automática de estados.
        
        Args:
            interval: Intervalo en segundos
        """
        if self._running:
            logger.warning("Sync ya está ejecutándose")
            return
        
        self._sync_interval = interval
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
        
        logger.info(f"Sincronización iniciada (cada {interval}s)")
    
    def stop_sync(self):
        """Detener sincronización"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        logger.info("Sincronización detenida")
    
    def _sync_loop(self):
        """Loop de sincronización"""
        while self._running:
            try:
                self._sync_all_devices()
            except Exception as e:
                logger.error(f"Error en sync loop: {e}")
            
            time.sleep(self._sync_interval)
    
    def _sync_all_devices(self):
        """Sincronizar todos los dispositivos"""
        for device_id in list(self.devices.keys()):
            self._sync_device(device_id)
    
    def _sync_device(self, device_id: str):
        """Sincronizar un dispositivo específico"""
        device = self.get_device(device_id)
        if not device:
            return
        
        plugin = self.plugin_manager.get_plugin(device.brand)
        if not plugin:
            return
        
        try:
            # Obtener estado actual de la API
            state = plugin.get_device_state(
                device_id=device_id,
                device_type=device.device_type
            )
            #rint(state)
            if state:
                # Convertir estado a dict
                if hasattr(state, 'to_dict'):
                    state_dict = state.to_dict()
                elif hasattr(state, '__dict__'):
                    state_dict = state.__dict__
                else:
                    state_dict = state
                
                # Actualizar estado (esto notificará a los callbacks)
                self.update_device_state(device_id, state_dict)
                
        except Exception as e:
            logger.error(f"Error sincronizando {device.name}: {e}")