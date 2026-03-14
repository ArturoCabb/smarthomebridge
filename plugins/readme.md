# Plugins — Cómo crear un plugin de marca

Los `Plugin`s son la capa que conecta un `client` (conector a API de la marca) con el resto del sistema. Su responsabilidad principal es:

- Proveer el `client` mediante `get_api_client()`.
- Descubrir dispositivos (`discover_devices()`) y devolverlos en un formato estándar.
- Crear instancias de modelo/objeto de dispositivo (`create_device()`).
- Obtener el estado actual de un dispositivo (`get_device_state()`).
- Enviar comandos a dispositivos (`send_command()`).

Este documento explica qué debe definir un plugin nuevo y cómo organizar modelos y clientes.

## Interfaz mínima (ver `plugins/base_plugin.py`)

### Todos los archivos de plugin deben de llamarser xxx_plugin.py para que puedan ser reconocidos automaticamente

Un `BasePlugin` define los métodos abstractos que debes implementar:

- `get_supported_devices() -> List[str]` — tipos soportados (ej. `['washer','tv']`).
- `get_api_client() -> object` — instancia del client de la marca (ver `brandconnectors/`).
- `create_device(device_type: str, device_data: dict) -> object` — factory que devuelve una instancia de la clase de modelo correspondiente.
- `discover_devices() -> List[dict]` — lista de dispositivos en formato estándar.
- `get_device_state(device_id: str, device_type: str) -> Dict` — estado actual, puede devolver una instancia de modelo o un dict parsado.
- `send_command(device_id: str, command_data: Dict, credentials: Dict | None = None) -> bool` — enviar comando.

## Formato estándar de `discover_devices()`

Cada elemento debe ser un diccionario con, al menos, los siguientes campos:

- `device_id` (str)
- `device_type` (str) — preferentemente en mayúsculas y coincidente con tus modelos (ej. `DEVICE_WASHER`).
- `model` (str)
- `alias` o `name` (str)
- `brand` (str)

Ejemplo:

```py
{ 'device_id': 'abc123', 'device_type': 'DEVICE_WASHER', 'model': 'F4J6', 'alias': 'Lavadora cocina', 'brand': 'lg' }
```

## Organización recomendada

1. `brandconnectors/` — implementa el client HTTP/OAuth que habla con la API del fabricante (hereda de `BaseClient`).
2. `plugins/<brand>_plugin.py` — plugin que usa el client y transforma datos a `DeviceState`/modelos.
3. `models/<Brand>/` — clases que representan dispositivos concretos (p. ej. `washer.py`) con métodos de parseo y serialización.

### Modelo de dispositivo (ejemplo)

En `models/LG/washer.py` define una clase `LGWasher` y una clase `WasherState` con métodos como:

- `@classmethod def from_json(cls, raw_snapshot: dict) -> WasherState` — parsea snapshot crudo.
- `def to_discovery_dict(self) -> dict` — si el modelo necesita exponer datos para SmartThings u otros.
- `def to_command_request(self, action, params) -> dict` — normaliza payloads para `send_command()`.

Separar `modelo` (estructura/parseo) de `state` (snapshot actual) facilita testing y reutilización.

## Implementación paso a paso (ejemplo simplificado)

```py
class MiBrandPlugin(BasePlugin):
    brand = 'mibrand'

    def __init__(self):
        self.client: MiBrandClient | None = None

    def get_supported_devices(self):
        return ['washer', 'tv']

    def get_api_client(self):
        if not self.client:
            # Leer configuración (tokens, base_url) y crear client
            self.client = MiBrandClient(base_url, access_token, client_id)
        return self.client

    def discover_devices(self):
        client = self.get_api_client()
        raw = client.get_devices_list()
        devices = []
        for d in raw:
            devices.append({'device_id': d['id'], 'device_type': d['type'].upper(), 'model': d.get('model'), 'alias': d.get('alias'), 'brand': self.brand})
        return devices

    def create_device(self, device_type, device_data):
        if 'WASHER' in device_type:
            return models.LG.washer.LGwasher(device_data)
        raise ValueError('Tipo no soportado')

    def get_device_state(self, device_id, device_type):
        client = self.get_api_client()
        snapshot = client.get_device_state(device_id)
        if 'WASHER' in device_type:
            return WasherState.from_json(snapshot)
        return snapshot

    def send_command(self, device_id, command_data, credentials=None):
        client = self.get_api_client()
        return client.send_command(device_id, command_data)
```

## Buenas prácticas

- Centraliza la creación del client en `get_api_client()` para reutilizar sesiones y manejar refresh tokens.
- Normaliza y documenta el formato que retornan tus métodos (`discover_devices`, `get_device_state`) para facilitar al `DeviceManager`.
- Maneja errores y devuelve valores por defecto (`{}` o `False`) en lugar de propagar excepciones no controladas.
- Escribe tests para `discover_devices()` y `get_device_state()` usando respuestas mock de la API.
- En `create_device()` devuelve instancias de las clases en `models/`, no diccionarios crudos.

## Integración con `PluginManager`

`PluginManager` busca archivos `*_plugin.py` dentro de `plugins/`, importa la clase que herede de `BasePlugin` y la registra automáticamente. Asegúrate de nombrar tu archivo siguiendo el patrón y de que la clase tenga el atributo `brand`.

## Ejemplo real en este repo

Revisa `plugins/lg_plugin.py` que implementa el patrón: crea el `LGThinQClient`, transforma la lista de dispositivos y usa `WasherState.from_json()` para parsear estados.

---
Documento creado para guiar la implementación de nuevos plugins de marca.
