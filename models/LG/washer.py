from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List

from models.LG.base import LGDevice, LGDeviceProfile, LGDeviceState


# ============================================================================
# DEVICE PROFILE - Basado en el schema de LG
# ============================================================================

@dataclass
class ValueReference:
    """
    Referencia a valores (_comment en el schema).
    """
    comment: Optional[str] = None
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'ValueReference':
        return cls(comment=json_data.get('_comment'))


@dataclass
class EnumValue:
    """
    Valor individual de un enum con sus labels.
    Ejemplo: {"label": ["NORMAL", "COTTON_SOFT"]}
    """
    label: List[str] = field(default_factory=list)
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'EnumValue':
        return cls(label=json_data.get('label', []))


@dataclass
class PropertyValue:
    """
    Valores posibles de una propiedad (r: read, w: write).
    """
    r: Optional[List[EnumValue]] = None  # Valores de lectura
    w: Optional[List[EnumValue]] = None  # Valores de escritura
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'PropertyValue':
        r_values = None
        w_values = None
        
        if 'r' in json_data:
            r_values = [EnumValue.from_json(item) for item in json_data['r']]
        
        if 'w' in json_data:
            w_values = [EnumValue.from_json(item) for item in json_data['w']]
        
        return cls(r=r_values, w=w_values)


@dataclass
class RangeValue:
    """
    Rango de valores numéricos (min, max, step).
    """
    min: int = 0
    max: int = 0
    step: int = 1
    except_: Optional[List[int]] = None  # Valores excluidos del rango
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'RangeValue':
        return cls(
            min=json_data.get('min', 0),
            max=json_data.get('max', 0),
            step=json_data.get('step', 1),
            except_=json_data.get('except')
        )


@dataclass
class Property:
    """
    Propiedad del dispositivo.
    Puede ser tipo: enum, range, number, string, boolean
    """
    type: str  # "enum", "range", "number", "string", "boolean"
    value_reference: Optional[ValueReference] = None
    value: Optional[PropertyValue] = None  # Para type="enum"
    range: Optional[RangeValue] = None     # Para type="range"
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'Property':
        value_ref = None
        if 'valueReference' in json_data:
            value_ref = ValueReference.from_json(json_data['valueReference'])
        
        prop_value = None
        if 'value' in json_data:
            prop_value = PropertyValue.from_json(json_data['value'])
        
        prop_range = None
        if 'range' in json_data:
            prop_range = RangeValue.from_json(json_data['range'])
        
        return cls(
            type=json_data.get('type', 'string'),
            value_reference=value_ref,
            value=prop_value,
            range=prop_range
        )


@dataclass
class Notification:
    """
    Notificaciones push del dispositivo.
    """
    push: Optional[List[str]] = None
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'Notification':
        return cls(push=json_data.get('push'))


class LGwasher(LGDevice):
    device_type = "WASHER"

@dataclass
class WasherProfile(LGDeviceProfile):
    """
    Device Profile completo de la lavadora según schema de LG.
    
    Estructura según documentación:
    {
      "deviceType": "WASHER",
      "property": {
        "state": {...},
        "course": {...},
        "smartCourse": {...},
        ...
      },
      "notification": {
        "push": [...]
      }
    }
    """
    device_type: str = "WASHER"
    
    # Propiedades del dispositivo
    # Según el schema, estas son las propiedades principales:
    state: Optional[Property] = None
    course: Optional[Property] = None
    smart_course: Optional[Property] = None
    initial_time_h: Optional[Property] = None
    initial_time_m: Optional[Property] = None
    remain_time_h: Optional[Property] = None
    remain_time_m: Optional[Property] = None
    reserve_time_h: Optional[Property] = None
    reserve_time_m: Optional[Property] = None
    current_state: Optional[Property] = None
    pre_state: Optional[Property] = None
    tcl_count: Optional[Property] = None
    temp_control: Optional[Property] = None
    spin_speed: Optional[Property] = None
    rinse_option: Optional[Property] = None
    dry_level: Optional[Property] = None
    error: Optional[Property] = None
    door_lock: Optional[Property] = None
    child_lock: Optional[Property] = None
    remote_start: Optional[Property] = None
    
    # Todas las propiedades adicionales
    additional_properties: Dict[str, Property] = field(default_factory=dict)
    
    # Notificaciones
    notification: Optional[Notification] = None
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'WasherProfile':
        """
        Parsear el JSON del Device Profile de LG.
        
        Args:
            json_data: Respuesta JSON de la API
            
        Returns:
            Instancia de WasherProfile
        """
        properties = json_data.get('property', {})
        
        # Mapear propiedades conocidas
        profile = cls(
            device_type=json_data.get('deviceType', 'WASHER')
        )
        
        # Parsear cada propiedad
        if 'state' in properties:
            profile.state = Property.from_json(properties['state'])
        
        if 'course' in properties:
            profile.course = Property.from_json(properties['course'])
        
        if 'smartCourse' in properties:
            profile.smart_course = Property.from_json(properties['smartCourse'])
        
        if 'initialTime_H' in properties:
            profile.initial_time_h = Property.from_json(properties['initialTime_H'])
        
        if 'initialTime_M' in properties:
            profile.initial_time_m = Property.from_json(properties['initialTime_M'])
        
        if 'remainTime_H' in properties:
            profile.remain_time_h = Property.from_json(properties['remainTime_H'])
        
        if 'remainTime_M' in properties:
            profile.remain_time_m = Property.from_json(properties['remainTime_M'])
        
        if 'reserveTime_H' in properties:
            profile.reserve_time_h = Property.from_json(properties['reserveTime_H'])
        
        if 'reserveTime_M' in properties:
            profile.reserve_time_m = Property.from_json(properties['reserveTime_M'])
        
        if 'currentState' in properties:
            profile.current_state = Property.from_json(properties['currentState'])
        
        if 'preState' in properties:
            profile.pre_state = Property.from_json(properties['preState'])
        
        if 'TCLCount' in properties:
            profile.tcl_count = Property.from_json(properties['TCLCount'])
        
        if 'tempControl' in properties:
            profile.temp_control = Property.from_json(properties['tempControl'])
        
        if 'spinSpeed' in properties:
            profile.spin_speed = Property.from_json(properties['spinSpeed'])
        
        if 'rinseOption' in properties:
            profile.rinse_option = Property.from_json(properties['rinseOption'])
        
        if 'dryLevel' in properties:
            profile.dry_level = Property.from_json(properties['dryLevel'])
        
        if 'error' in properties:
            profile.error = Property.from_json(properties['error'])
        
        if 'doorLock' in properties:
            profile.door_lock = Property.from_json(properties['doorLock'])
        
        if 'childLock' in properties:
            profile.child_lock = Property.from_json(properties['childLock'])
        
        if 'remoteStart' in properties:
            profile.remote_start = Property.from_json(properties['remoteStart'])
        
        # Guardar propiedades adicionales que no conocemos
        known_props = {
            'state', 'course', 'smartCourse', 'initialTime_H', 'initialTime_M',
            'remainTime_H', 'remainTime_M', 'reserveTime_H', 'reserveTime_M',
            'currentState', 'preState', 'TCLCount', 'tempControl', 'spinSpeed',
            'rinseOption', 'dryLevel', 'error', 'doorLock', 'childLock', 'remoteStart'
        }
        
        for key, value in properties.items():
            if key not in known_props:
                profile.additional_properties[key] = Property.from_json(value)
        
        # Parsear notificaciones
        if 'notification' in json_data:
            profile.notification = Notification.from_json(json_data['notification'])
        
        return profile
    
    def get_property(self, name: str) -> Optional[Property]:
        """
        Obtener una propiedad por nombre.
        
        Args:
            name: Nombre de la propiedad (en formato camelCase como viene de la API)
        """
        # Mapeo de nombres
        prop_map = {
            'state': self.state,
            'course': self.course,
            'smartCourse': self.smart_course,
            'initialTime_H': self.initial_time_h,
            'initialTime_M': self.initial_time_m,
            'remainTime_H': self.remain_time_h,
            'remainTime_M': self.remain_time_m,
            'reserveTime_H': self.reserve_time_h,
            'reserveTime_M': self.reserve_time_m,
            'currentState': self.current_state,
            'preState': self.pre_state,
            'TCLCount': self.tcl_count,
            'tempControl': self.temp_control,
            'spinSpeed': self.spin_speed,
            'rinseOption': self.rinse_option,
            'dryLevel': self.dry_level,
            'error': self.error,
            'doorLock': self.door_lock,
            'childLock': self.child_lock,
            'remoteStart': self.remote_start
        }
        
        # Buscar en propiedades conocidas
        if name in prop_map:
            return prop_map[name]
        
        # Buscar en propiedades adicionales
        return self.additional_properties.get(name)
    
    def get_allowed_values(self, property_name: str, mode: str = 'r') -> List[str]:
        """
        Obtener valores permitidos de una propiedad enum.
        
        Args:
            property_name: Nombre de la propiedad
            mode: 'r' para lectura, 'w' para escritura
            
        Returns:
            Lista de strings con valores permitidos
        """
        prop = self.get_property(property_name)
        if not prop or not prop.value:
            return []
        
        # Obtener valores de lectura o escritura
        enum_values = prop.value.r if mode == 'r' else prop.value.w
        if not enum_values:
            return []
        
        # Extraer todos los labels
        all_labels = []
        for enum_val in enum_values:
            all_labels.extend(enum_val.label)
        
        return all_labels
    
    def get_range(self, property_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtener rango de valores para una propiedad numérica.
        
        Returns:
            Diccionario con 'min', 'max', 'step', 'except' o None
        """
        prop = self.get_property(property_name)
        if not prop or not prop.range:
            return None
        
        result = {
            'min': prop.range.min,
            'max': prop.range.max,
            'step': prop.range.step
        }
        
        if prop.range.except_:
            result['except'] = prop.range.except_
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return asdict(self)


# ============================================================================
# DEVICE STATE (Snapshot del estado)
# ============================================================================

@dataclass
class WasherState(LGDeviceState):
    """
    Estado actual de la lavadora (snapshot).
    Basado en el Request/Response Schema.
    """
    
    # Estado principal
    state: str = "POWER_OFF"
    remote_start: Optional[bool] = False  # "ON" o "OFF"
    remain_time_h: Optional[int] = None
    remain_time_m: Optional[int] = None
    reserve_time_h: Optional[int] = None
    reserve_time_m: Optional[int] = None
    initial_time_h: Optional[int] = None
    initial_time_m: Optional[int] = None
    tcl_count: Optional[int] = None
    current_state: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'WasherState':
        """
        Parsear estado desde el snapshot de la API.
        
        Args:
            json_data: Diccionario con el snapshot
        """
        return cls(
            state=json_data.get('runState', 'POWER_OFF').get('currentState'),
            remote_start=json_data.get('remoteControlEnable').get('remoteControlEnabled'),
            remain_time_h=json_data.get('timer').get('remainHour'),
            remain_time_m=json_data.get('timer').get('remainMinute'),
            reserve_time_h=json_data.get('timer').get('relativeHourToStart'),
            reserve_time_m=json_data.get('timer').get('relativeMinuteToStart'),
            initial_time_h=json_data.get('timer').get('totalHour'),
            initial_time_m=json_data.get('timer').get('totalMinute'),
            tcl_count=json_data.get('cycle').get('cycleCount'),
            current_state=json_data.get('location').get('locationName'),
            error=json_data.get('error')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario"""
        return asdict(self)
    
    def is_online(self) -> bool:
        """Verificar si está en ejecución"""
        running_states = [
            'PREWASH', 'WASH', 'RINSE', 'SPIN', 'DRYING',
            'SMART_WASH_MAIN', 'SMART_RINSE', 'SMART_SPINNING'
        ]
        return self.state in running_states
    
    def is_complete(self) -> bool:
        """Verificar si terminó"""
        return self.state == 'COMPLETE'
    
    def has_error(self) -> bool:
        """Verificar si hay error"""
        return self.state == 'ERROR' or (self.error is not None and self.error != '')
    
    def get_remaining_minutes(self) -> int:
        """Obtener tiempo restante total en minutos"""
        hours = self.remain_time_h or 0
        minutes = self.remain_time_m or 0
        return (hours * 60) + minutes
    
    def is_remote_start_enabled(self) -> bool:
        """Verificar si el inicio remoto está habilitado"""
        return self.remote_start == 'ON'


# ============================================================================
# WASHER COMMAND (Comando para control)
# ============================================================================

@dataclass
class WasherCommand:
    """
    Comando para enviar a la lavadora.
    Basado en el Request Schema de control.
    """
    
    # Curso
    location_name: Optional[str] = None
    #smart_course: Optional[str] = None
    
    # Tiempo de reserva
    reserve_time_h: Optional[int] = None
    #reserve_time_m: Optional[int] = None
    
    # Opciones
    #temp_control: Optional[str] = None
    #spin_speed: Optional[int] = None
    #rinse_option: Optional[str] = None
    #dry_level: Optional[str] = None
    
    # Control remoto
    operation_mode: Optional[str] = None  # "START" o "STOP" "POWER_OFF"
    
    def to_api_format(self) -> Dict[str, Any]:
        """
        Convertir a formato de la API de LG.
        Solo incluye campos no-None.
        """
        result = {}
        
        if self.location_name is not None:
            result.update({'location':{'locationName': self.location_name}})
            
        if self.reserve_time_h is not None:
            result.update({'reserveTime_H': self.reserve_time_h})
        
        if self.operation_mode is not None:
            result.update({'operation':{'washerOperationMode': self.operation_mode}})
        
        return result
    
    #def validate(self, profile: WasherProfile) -> tuple[bool, Optional[str]]:
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validar comando contra el perfil.
        
        Returns:
            (es_válido, mensaje_error)
        """
        # Validar location
        if self.location_name is not None and not self.location_name not in ['MAIN', 'MINI']:
            return False, "La ubicación debe ser 'MAIN' o 'MINI'"
        
        if self.reserve_time_h is not None and not (0 <= self.reserve_time_h <= 19):
            return False, "Horas de reserva entre 0 y 19"
        
        # Validar remote_start
        if self.operation_mode is not None and self.operation_mode not in ['START', 'STOP', 'POWER_OFF']:
            return False, "remote_start debe ser 'ON' o 'OFF'"
        
        return True, None
    