# DeviceFactory — Documentación detallada

`DeviceFactory` es una capa ligera cuya responsabilidad es crear instancias de dispositivos concretos (model objects) usando la lógica provista por los `Plugin`s.

Este archivo documenta `core/device_factory.py` y muestra cómo usarlo y extenderlo.

## Responsabilidad principal

- Recibir datos de descubrimiento (por ejemplo el resultado de `Plugin.discover_devices()`) y delegar la creación del objeto de dispositivo al plugin correspondiente mediante `plugin.create_device()`.

## API pública

- `__init__(plugin_manager: PluginManager)` — recibe la instancia de `PluginManager` para poder localizar el plugin que crea dispositivos para cada marca.

- `create_from_discovery(brand: str, device_info: dict) -> BaseDevice`
  - Busca el plugin por `brand` y llama `plugin.create_device(device_info['device_type'], device_info)`.
  - Si no existe plugin para la `brand`, lanza `ValueError`.

## Diseño y motivación

- Separar la responsabilidad de creación de objetos del código que orquesta el descubrimiento (por ejemplo `AppManager`) facilita pruebas y extensibilidad.
- `DeviceFactory` no conoce los detalles internos de cada plugin ni de cómo se construyen las clases de modelo; sólo delega.

## Ejemplo de flujo típico

1. `AppManager` o el orquestador obtiene `discovered = plugin.discover_devices()`.
2. Para cada `device_info` en `discovered`, llama `device_factory.create_from_discovery(plugin.brand, device_info)`.
3. `DeviceFactory` localiza el plugin y retorna la instancia creada por `plugin.create_device()`.

## Buenas prácticas

- Validar que `device_info` contiene las llaves esperadas (`device_type`, `device_id`).
- Manejar errores de fábrica (por ejemplo tipos no soportados) de forma explicativa: lanzar `ValueError` con mensaje claro.
- Mantener `DeviceFactory` libre de lógica de negocio (no parsear snapshots, no tocar estados); eso corresponde al plugin y a los modelos.

## Extensiones posibles

- Añadir `create_from_db(db_record)` (comentado en el archivo) para construir dispositivos desde un registro persistido, útil al recuperar la configuración guardada.
- Registrar hooks o validadores que verifiquen compatibilidad entre `device_info` y los modelos disponibles.

---
Archivo generado para explicar la lógica y uso de `DeviceFactory`.
