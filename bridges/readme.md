## Creación de bridge

Los *bridges* son adaptadores que traducen entre `DeviceManager` (fuente de la verdad de dispositivos y sus estados) y un servicio objetivo (por ejemplo HomeKit o SmartThings). Un bridge se encarga de:

- Crear la representación/`accessory` adecuada para cada `DeviceState` descubierto.
- Registrar ese `accessory` en el servicio (p. ej. `HAPService.add_accessory()` o `SmartThingsService.add_accessory()`).
- Suscribirse a actualizaciones de estado en `DeviceManager` y propagar cambios al `accessory`.

Objetivo de esta guía: explicar qué funciones deben implementarse en un bridge, qué elementos deben definirse y cómo consumir los ejemplos `hap_bridge.py` y `smartthings_bridge.py`.

### Conceptos clave

- `DeviceState`: objeto que contiene `device_id`, `brand`, `device_type`, `name`, `model` y `state` (entre otros). El bridge recibe instancias de `DeviceState` desde `DeviceManager`.
- `accessory`: objeto específico del servicio (para HomeKit suele ser una clase que hereda de `Accessory`; para SmartThings es una dataclass que conoce cómo serializarse y enviar su estado).
- `service`: instancia de `HAPService` o `SmartThingsService` que expondrá el `accessory`.

### Firma recomendada del bridge

El constructor normalmente recibe el `DeviceManager` y la instancia del servicio objetivo:

```python
def __init__(self, device_manager: DeviceManager, service: Any):
    self.device_manager = device_manager
    self.service = service
    self.accessories: Dict[str, object] = {}
```

### Funciones mínimas que debe implementar un bridge

1. `add_device(device_state: DeviceState)`
   - Crear el accessory desde `device_state` (llamando a un factory interno `_create_accessory`).
   - Registrar el accessory en el `service` (por ejemplo `service.add_accessory(device_id, accessory)`).
   - Guardar el mapping `self.accessories[device_id] = accessory`.
   - Suscribirse a `DeviceManager` para cambios: `device_manager.subscribe_to_device(device_id, callback)`.

2. `_create_accessory(device_state: DeviceState) -> object | None`
   - Lógica tipo factory: inspecciona `device_state.brand` y `device_state.device_type` para elegir la clase correcta.
   - Crear la instancia de accessory y, si necesita, inyectar `device_manager` o `service` mediante métodos como `set_device_manager()` o parámetros del constructor.
   - Debe devolver `None` si no existe soporte para ese tipo.

3. `_on_device_state_changed(device_state: DeviceState)`
   - Callback que se ejecuta cuando `DeviceManager` notifica un cambio.
   - Localizar el accessory por `device_id` y llamar su método `update_from_device_state(device_state)` o el método equivalente que exponga el accessory.

Ejemplo (esquema):

```python
def add_device(self, device_state):
    device_id = device_state.device_id
    if device_id in self.accessories:
        return
    accessory = self._create_accessory(device_state)
    if not accessory:
        return
    self.service.add_accessory(device_id, accessory)
    self.accessories[device_id] = accessory
    self.device_manager.subscribe_to_device(device_id, lambda ds: self._on_device_state_changed(ds))

def _on_device_state_changed(self, device_state):
    accessory = self.accessories.get(device_state.device_id)
    if accessory and hasattr(accessory, 'update_from_device_state'):
        accessory.update_from_device_state(device_state)
```

### Qué debe ofrecer un `accessory` para integrarse con un bridge

- Método `update_from_device_state(device_state)` — recibir el `DeviceState` y actualizar sus características internas / notificar al servicio.
- Si el accessory necesita enviar comandos al dispositivo, debe exponer una forma de invocar el `DeviceManager.send_command(device_id, command_data)` o tener una referencia inyectada al plugin/cliente.
- Opcional: métodos `set_device_manager(device_manager)` y `set_smartthings_service(service)` o `set_hap_service(service)` para inyección de dependencias cuando la clase se crea fuera del contexto del bridge.

### Ejemplos concretos del repositorio

- `bridges/hap_bridge.py` (patrón HomeKit):
  - `_create_accessory()` devuelve una instancia de `LGWasherAccessory(driver=..., display_name=..., device_id=..., device_manager=...)`.
  - `add_device()` registra el accessory en `HAPService` y se subscribe a `DeviceManager`.

- `bridges/smartthings_bridge.py` (patrón SmartThings):
  - `_create_accessory()` busca en un archivo de configuración (`smartthingsDevices.json`) la correspondencia `externalDeviceId` → crea `LGWasherAccessory` (SmartThings dataclass).
  - Inyecta `device_manager` y `smartthings_service` en el accessory para permitir envíos de estado y comandos.

### Recomendaciones al implementar un nuevo bridge

1. Mantén el factory `_create_accessory()` simple: delega la creación a clases específicas por marca/tipo.
2. Evita lógica bloqueante dentro de callbacks; si necesitas I/O, usa hilos o colas para no bloquear el hilo de eventos.
3. Valida `device_state` antes de crear el accessory (asegura `device_id`, `device_type`, `brand`).
4. Añade logs claros en cada paso (`info` cuando se agrega un dispositivo, `warning` si no hay soporte, `error` en excepciones).
5. Maneja idempotencia en `add_device()` (no volver a registrar el mismo `device_id`).

### Formato esperado de `DeviceState` (mínimo)

- `device_id` (str): identificador único.
- `brand` (str): marca del dispositivo (ej. `lg`).
- `device_type` (str): tipo (ej. `washer`).
- `name` (str): nombre para mostrar.
- `state` (dict): snapshot con propiedades concretas (p. ej. `power`, `remain_time_m`, `job_state`).

### Pruebas y verificación

1. Crea un `DeviceState` de ejemplo y llama `bridge.add_device(device_state)` manualmente desde un REPL o un script de pruebas.
2. Simula una actualización llamando la función de callback registrada por `DeviceManager` (o invoca `update_from_device_state()` directamente) y verifica que el accessory actualice sus características.
3. Para SmartThings, si trabajas con webhooks/OAuth, utiliza `ngrok` para exponer tu servidor local y verifica que los endpoints respondan correctamente.

### Ejemplo: añadir soporte para un nuevo `washer` de otra marca

1. Crear la clase accessory en `bridges/homekit/MarcaXWasherAccessory.py` siguiendo la estructura de `LGWasherAccessory`.
2. Añadir mapeo en `HAPBridge._create_accessory()`:

```python
if brand == 'marca_x' and 'washer' in device_type:
    return MarcaXWasherAccessory(...)
```

3. Si SmartThings también requiere soporte, crear `bridges/smartthings/MarcaXWasherAccessory.py` y añadir el mapeo en `SmartThingsBridge._create_accessory()`.

4. Probar localmente y escribir un caso de prueba que cree el `DeviceState` y verifique el ciclo completo.

### Buenas prácticas

- Documenta el `DeviceState` y las expectativas de campo para cada accesorio adicional que implementes.
- Mantén las funciones pequeñas y con responsabilidades claras (factory, registro, callback).
- Usa inyección de dependencias (p. ej. pasar `device_manager` y `service`) para facilitar pruebas.

---
Guía creada para ayudar a nuevos contribuidores a definir bridges confiables y fáciles de testear.
