from models.base import BaseDevice, BaseDeviceProfile, BaseDeviceState


class LGDeviceProfile(BaseDeviceProfile):
    """Perfil específico de LG con su estructura de properties"""
    pass

class LGDeviceState(BaseDeviceState):
    """Estado específico de LG"""
    pass

class LGDevice(BaseDevice):
    """Dispositivo específico de LG"""
    brand = "lg"
    # Lógica común a todos los dispositivos LG
