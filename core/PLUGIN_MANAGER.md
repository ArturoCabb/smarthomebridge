# PluginManager — Documentación detallada

Este documento describe `core/plugin_manager.py`. `PluginManager` es responsable de descubrir, instanciar y exponer los plugins (implementaciones de `BasePlugin`) que permiten hablar con distintas marcas.

## Responsabilidades principales

- Descubrir automáticamente archivos `*_plugin.py` dentro del directorio `plugins/`.
- Importar dinámicamente los módulos y detectar clases que hereden de `BasePlugin`.
- Instanciar y registrar plugins en un mapa `brand -> plugin_instance`.
- Exponer utilidades para obtener un plugin por `brand` o la lista completa de plugins.

## Flujo de descubrimiento

1. `__init__()` llama a `_discover_plugins()` al crearse el `PluginManager`.
2. `_discover_plugins()` construye la ruta a `plugins/` y itera sobre archivos que coinciden con `*_plugin.py`.
3. Para cada archivo se importa el módulo dinámicamente usando `importlib.import_module()`.
4. Se usa `inspect.getmembers()` para localizar clases que sean subclases de `BasePlugin` (y no `BasePlugin` misma).
5. Cada clase encontrada se instancia (llamando al constructor sin parámetros) y se registra vía `register_plugin(plugin)`.

## API pública (resumen)

- `register_plugin(plugin: BasePlugin)`
  - Añade `plugin` a `self.plugins` utilizando `plugin.brand` como clave.
  - Emite `logger.info` indicando el plugin registrado.

- `get_plugin(brand: str) -> Optional[BasePlugin]`
  - Retorna la instancia registrada para esa marca (busca en minúsculas).

- `get_all_plugins() -> List[BasePlugin]`
  - Devuelve una lista con todas las instancias registradas.

## Reglas y supuestos

- Convención de nombres: los módulos de plugin deben llamarse `xxx_plugin.py` para que `PluginManager` los detecte.
- La clase concreta debe heredar de `BasePlugin` y definir el atributo `brand` (por ejemplo `brand = 'lg'`).
- El constructor del plugin debe ser sencillo (no requiere parámetros); si necesita cargar configuración, debe hacerlo internamente en `get_api_client()` para evitar efectos secundarios en el descubrimiento.

## Manejo de errores y robustez

- Si la importación de un módulo de plugin falla (por error de sintaxis o dependencia), `PluginManager` dejará que la excepción suba y el proceso fallará — es deseable en entornos de desarrollo para detectar errores.
- Recomendación: pruebas unitarias para cada plugin que verifiquen que la clase se puede instanciar sin parámetros.

## Cómo escribir un plugin compatible

1. Crear `plugins/mybrand_plugin.py`.
2. Definir una clase que herede de `BasePlugin` y declarar `brand = 'mybrand'`.
3. Implementar los métodos requeridos (`get_api_client`, `discover_devices`, `create_device`, `get_device_state`, `send_command`).
4. Evitar efectos secundarios en la importación del módulo (por ejemplo, no iniciar conexiones en el top-level module).

## Ejemplo de verificación rápida

```py
pm = PluginManager()
print([p.brand for p in pm.get_all_plugins()])
```

Si tu plugin no aparece:

- Verifica que el archivo sigue el patrón `*_plugin.py`.
- Verifica que la clase hereda de `BasePlugin` y que su constructor no lanza excepciones.

---
Archivo generado para explicar la lógica y uso de `PluginManager`.
