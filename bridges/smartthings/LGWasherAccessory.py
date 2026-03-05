from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MachineState(str, Enum):
    PAUSE = "pause"
    RUN = "run"
    STOP = "stop"

class WasherJobState(str, Enum):
    AIR_WASH = "airWash"
    AI_RINSE = "aIRinse"
    AI_SPIN = "aISpin"
    AI_WASH = "aIWash"
    COOLING = "cooling"
    DELAY_WASH = "delayWash"
    DRYING = "drying"
    FINISH = "finish"
    NONE = "none"
    PRE_WASH = "preWash"
    RINSE = "rinse"
    SPIN = "spin"
    WASH = "wash"
    WEIGHT_SENSING = "weightSensing"
    WRINKLE_PREVENT = "wrinklePrevent"
    FREEZE_PROTECTION = "freezeProtection"

class HealthStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"

@dataclass
class LGWasherAccessory:
    # Device identity
    external_device_id: str
    friendly_name: str
    device_handler_type: str

    # Manufacturer info
    manufacturer_name: str
    model_name: str
    hw_version: str
    sw_version: str = "0.0.1"

    # Device context
    room_name: str = "cuarto de lavado"
    groups: List[str] = field(default_factory=lambda: ["washer"])
    categories: List[str] = field(default_factory=lambda: ["washer"])

    # Device cookie (opaque para SmartThings)
    device_cookie: Dict = field(default_factory=dict)

    # State
    health_status: HealthStatus = HealthStatus.ONLINE
    completion_time: str = "2022-09-27 18:00:00.000"
    machine_state: MachineState = MachineState.STOP
    washer_job_state: WasherJobState = WasherJobState.NONE

    # Device manager (inyectado desde el bridge)
    device_manager: Optional[object] = field(default=None, repr=False, init=False)


    def to_discovery_dict(self) -> Dict:
        """
        Send device info formated to function handle_device_discovered()
        """
        return {
            "externalDeviceId": self.external_device_id,
            "deviceCookie": self.device_cookie,
            "friendlyName": self.friendly_name,
            "manufacturerInfo": {
                "manufacturerName": self.manufacturer_name,
                "modelName": self.model_name,
                "hwVersion": self.hw_version,
                "swVersion": self.sw_version
            },
            "deviceContext" : {
                "roomName": self.room_name,
                "groups": self.groups,
                "categories": self.categories
            },
            "deviceHandlerType": self.device_handler_type,
            "deviceUniqueId": self.external_device_id
        }
    
    def state_refresh_request(self) -> Dict:
        """
        Send device info formated to function state_refresh_request()
        """
        return {
            "externalDeviceId": self.external_device_id,
            "deviceCookie": self.device_cookie,
            "states": [
                {
                    "component": "main",
                    "capability": "st.healthCheck",
                    "attribute": "healthStatus",
                    "value": self.health_status.value
                },
                {
                    "component": "main",
                    "capability": "st.washerOperatingState",
                    "attribute": "completionTime",
                    "value": self.completion_time
                },
                {
                    "component": "main",
                    "capability": "st.washerOperatingState",
                    "attribute": "machineState",
                    "value": self.machine_state.value,
                },
                {
                    "component": "main",
                    "capability": "st.washerOperatingState",
                    "attribute": "washerJobState",
                    "value": self.washer_job_state.value,
                },
            ]
        }
    
    def to_command_request(self) -> Dict:
        """
        Send device info formated to function command_request()
        """
        return {
            "externalDeviceId": self.external_device_id,
            "deviceCookie": self.device_cookie,
            "states": [
                {
                    "component": "main",
                    "capability": "st.washerOperatingState",
                    "attribute": "state",
                    "value": self.machine_state.value,
                }
            ],
        }
    
    def send_device_status(self):
        """
        Send device info formated to function handle_device_discovered()
        """
        return {
            "externalDeviceId": self.external_device_id,
            "states": [
                {
                    "component": "main",
                    "capability": "st.healthCheck",
                    "attribute": "healthStatus",
                    "value": self.health_status.value,
                    "stateChange": "Y",
                },
                {
                    "component": "main",
                    "capability": "st.washerOperatingState",
                    "attribute": "completionTime",
                    "value": self.completion_time,
                    "stateChange": "Y",
                },
                {
                    "component": "main",
                    "capability": "st.washerOperatingState",
                    "attribute": "machineState",
                    "value": self.machine_state.value,
                    "stateChange": "Y",
                },
                {
                    "component": "main",
                    "capability": "st.washerOperatingState",
                    "attribute": "washerJobState",
                    "value": self.washer_job_state.value,
                    "stateChange": "Y",
                },
            ]
        }

    def update_from_device_state(self, device_state):
        """
        Actualizar el estado del accesorio desde un DeviceState del DeviceManager.

        Args:
            device_state: DeviceState obtenido del plugin
        """
        if not device_state or not hasattr(device_state, 'state'):
            logger.warning(f"DeviceState inválido para {self.external_device_id}")
            return

        state = device_state.state

        # Actualizar health_status según conectividad del dispositivo
        if device_state.online:
            self.health_status = HealthStatus.ONLINE
        else:
            self.health_status = HealthStatus.OFFLINE

        # Mapear estado del dispositivo a machine_state
        device_operation_state = state.get('state', '').upper()
        if device_operation_state in ('RUN', 'WASH', 'RINSING', 'SPINNING'):
            self.machine_state = MachineState.RUN
        elif device_operation_state == 'PAUSE':
            self.machine_state = MachineState.PAUSE
        else:  # POWER_OFF, STOP, etc.
            self.machine_state = MachineState.STOP

        # Mapear estado específico del lavado a washer_job_state
        # Esta lógica depende de cómo el plugin retorna el estado
        job_state_str = state.get('washer_job_state', 'none').lower()
        try:
            self.washer_job_state = WasherJobState(job_state_str)
        except ValueError:
            self.washer_job_state = WasherJobState.NONE
            logger.debug(f"Estado de trabajo desconocido: {job_state_str}")

        # Actualizar tiempo de completación (si está disponible)
        if 'remain_time_m' in state:
            remain_minutes = state.get('remain_time_m', 0)
            # Convertir minutos a formato HH:MM:SS (aproximado)
            hours = remain_minutes // 60
            minutes = remain_minutes % 60
            self.completion_time = f"{hours:02d}:{minutes:02d}:00"

        logger.info(f"Estado actualizado para {self.external_device_id}: "
                   f"machine_state={self.machine_state.value}, "
                   f"health_status={self.health_status.value}")

    def set_device_manager(self, device_manager):
        """
        Establecer el device_manager (inyección de dependencia postinit).

        Args:
            device_manager: Instancia de DeviceManager para enviar comandos
        """
        self.device_manager = device_manager

    def translate_smartthings_command(self, st_command: Dict) -> Optional[Dict]:
        """
        Traducir comando de SmartThings a formato API LG.

        Args:
            st_command: Comando desde SmartThings con estructura:
            {
                "component": "main",
                "capability": "st.washerOperatingState",
                "attribute": "machineState",
                "value": "run" | "pause" | "stop"
            }

        Returns:
            Dict con comando en formato LG API o None si no se puede traducir

        Ejemplos de traducción:
        - ST: {attribute: "machineState", value: "run"} → LG: {operation: {washerOperationMode: "START"}}
        - ST: {attribute: "machineState", value: "pause"} → LG: {operation: {washerOperationMode: "STOP"}}
        - ST: {attribute: "machineState", value: "stop"} → LG: {operation: {washerOperationMode: "POWER_OFF"}}
        """
        if not st_command:
            return None

        attribute = st_command.get('attribute', '').lower()
        value = st_command.get('value', '').lower()

        # Mapeo: machineState → operation/washerOperationMode
        if attribute == 'machinestate':
            if value == 'run':
                return {'operation': {'washerOperationMode': 'START'}}
            elif value == 'pause':
                return {'operation': {'washerOperationMode': 'STOP'}}
            elif value == 'stop':
                return {'operation': {'washerOperationMode': 'POWER_OFF'}}

        # Mapeo: completionTime → délai de inicio
        elif attribute == 'completiontime' and value.isdigit():
            try:
                hours = int(value) // 60
                if 0 <= hours <= 19:
                    return {'reserveTime_H': hours}
            except (ValueError, ZeroDivisionError):
                pass

        logger.warning(f"No se puede traducir comando SmartThings: {st_command}")
        return None

    def handle_smartthings_command(self, st_command: Dict) -> bool:
        """
        Manejar comando recibido desde SmartThings.
        Traduce el comando a formato LG y lo envía al dispositivo.

        Args:
            st_command: Comando desde SmartThings

        Returns:
            True si se envió exitosamente, False si falló

        Flujo:
        1. Traducir comando ST → LG
        2. Enviar comando via device_manager
        3. Retornar resultado
        """
        if not self.device_manager:
            logger.error(f"device_manager no disponible para {self.external_device_id}")
            return False

        try:
            lg_command = self.translate_smartthings_command(st_command)
            if not lg_command:
                logger.warning(f"No se pudo traducir comando para {self.external_device_id}")
                return False

            logger.info(f"Comando traducido: {lg_command}")

            # Enviar comando al dispositivo via device_manager
            result = self.device_manager.send_command(
                self.external_device_id,
                lg_command
            )

            if result:
                logger.info(f"Comando enviado exitosamente a {self.external_device_id}")
            else:
                logger.error(f"Error enviando comando a {self.external_device_id}")

            return result

        except Exception as e:
            logger.error(f"Error en handle_smartthings_command: {e}")
            return False

