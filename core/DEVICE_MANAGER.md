# DeviceManager — Documentación detallada

Este documento explica en detalle el funcionamiento de `core/device_manager.py`. El `DeviceManager` es el núcleo que mantiene el inventario de dispositivos, sincroniza su estado con las APIs de los fabricantes y notifica a los bridges/servicios cuando hay cambios.

## Responsabilidades principales

- Mantener una colección de `DeviceState` (por `device_id`).
- Proveer operaciones CRUD mínimas: `add_device`, `get_device`, `get_all_devices`.
- Permitir suscripción a cambios mediante callbacks por dispositivo.
- Sincronizar periódicamente el estado de cada dispositivo llamando a los `Plugin`s.
- Enviar comandos a dispositivos vía el `Plugin` correspondiente.

## Estructuras clave

- `DeviceState` (dataclass)
  - `device_id`, `brand`, `device_type`, `name`, `model` — identidad y metadatos.
  - `state` (dict) — snapshot actual parseado por el plugin.
  - `online` (bool), `last_update` (datetime)
  - `callbacks` (List[Callable]) — funciones a invocar cuando `state` cambie.

## API pública (resumen de funciones)

- `add_device(device_info: Dict) -> DeviceState`
  - Crea un `DeviceState` a partir del dict que provee el plugin (`device_id`, `brand`, `device_type`, `model`, `alias`).
  - Protegido por un `Lock` para evitar condiciones de carrera.
  - Si el `device_id` ya existe, devuelve la instancia existente.

- `get_device(device_id: str) -> DeviceState | None`
- `get_all_devices() -> List[DeviceState]`

- `subscribe_to_device(device_id: str, callback: Callable)`
  - Añade `callback` a la lista de callbacks del `DeviceState`.
  - La firma esperada: `callback(device_state: DeviceState)`.

- `update_device_state(device_id: str, new_state: Dict)`
  - Actualiza `state` y `last_update` y ejecuta todos los callbacks en el hilo que llamó a la función.
  - Los callbacks se envuelven en try/except para que una excepción no cancele las notificaciones.

- `send_command(device_id: str, command_data: Dict) -> bool`
  - Obtiene el `plugin` por `device.brand` usando `PluginManager.get_plugin()`.
  - Llama `plugin.send_command(...)` y, si retorna `True`, forzar una sincronización inmediata de ese dispositivo.

- `start_sync(interval: int = 10)` / `stop_sync()`
  - Inician y detienen un hilo daemon que ejecuta `_sync_loop()` cada `interval` segundos.
  - `_sync_loop()` llama `_sync_all_devices()` que a su vez llama `_sync_device(device_id)` por cada dispositivo.

## Detalles de sincronización

- `_sync_device(device_id)`
  - Obtiene el `plugin` adecuado y solicita `plugin.get_device_state(device_id, device_type)`.
  - El valor retornado puede ser:
    - Una instancia de modelo con `to_dict()` o `__dict__`.
    - Un `dict` ya parseado.
  - La función intenta detectar `to_dict` o `__dict__` para convertir el resultado a `dict` antes de llamar `update_device_state`.

- Errores durante la sincronización se capturan y loguean; no interrumpen el loop global.

## Concurrencia y seguridad

- Se utiliza `threading.Lock()` (`self._lock`) para proteger la creación y actualización de la estructura `self.devices`.
- Las notificaciones (callbacks) se ejecutan en el mismo hilo que realiza la actualización; si los callbacks realizan operaciones lentas o bloqueantes, se recomienda que el callback delegue trabajo a un hilo/cola propia para no bloquear la sincronización global.

## Consideraciones de diseño

- Idempotencia: `add_device` evita re-registrar dispositivos.
- Resiliencia: `_sync_loop` captura excepciones para evitar que el hilo termine.
- Separación de responsabilidades: el `DeviceManager` no conoce los detalles de las APIs; delega al `Plugin` la obtención de estados y el envío de comandos.

## Ejemplos prácticos

- Agregar dispositivo (desde `AppManager`):

```py
device_info = {'device_id': 'abc', 'brand': 'lg', 'device_type': 'DEVICE_WASHER', 'model': 'F4J6', 'alias': 'Lavadora'}
device_state = device_manager.add_device(device_info)
```

- Subscribirse y recibir actualizaciones:

```py
def on_change(ds):
    print('Nuevo estado:', ds.state)

device_manager.subscribe_to_device('abc', on_change)
```

- Forzar envío de comando:

```py
device_manager.send_command('abc', {'action': 'start'})
```

## Cómo probar

- Unit tests:
  - Mockear `PluginManager.get_plugin()` para devolver un plugin de prueba cuyo `get_device_state()` retorne payloads conocidos.
  - Verificar que `update_device_state()` llama a los callbacks y actualiza `last_update`.
- Integración:
  - Ejecutar el proceso y comprobar logs del hilo de sincronización.

## Problemas comunes y soluciones

- Una suscripción bloquea la sincronización: mover trabajo intensivo a otro hilo.
- `send_command` devuelve False: revisar que el plugin exista y que `client.send_command()` funcione; consultar logs detallados.

---
Archivo generado para explicar la lógica y uso de `DeviceManager`.
