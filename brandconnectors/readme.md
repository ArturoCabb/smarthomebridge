
## Crear un client (conector de marca)

Los archivos dentro de `brandconnectors/` son implementaciones concretas de APIs de fabricantes (LG, Samsung, Xiaomi, etc.). Cada client debe implementar la interfaz definida por `BaseClient` y exponer las operaciones necesarias para:

- listar dispositivos de la cuenta (`get_devices_list()`),
- obtener el snapshot o estado actual del dispositivo (`get_device_state()`),
- obtener el perfil o metadatos del dispositivo (`get_device_profile()`),
- enviar comandos/controles al dispositivo (`send_command()`).

La aplicación espera que los `Plugin`s usen estos clients para obtener estados y enviar órdenes. Por tanto, los clients deben ser robustos, devolver estructuras previsibles y manejar errores de red y autenticación.

### Requisitos mínimos (interfaz)

Implementa una clase que herede de `BaseClient` y provea las cuatro funciones abstractas:

- `get_device_state(device_id: str) -> Dict[str, Any]` — devuelve un diccionario con el snapshot del dispositivo. Nunca debe devolver `None`; devolver `{}` ante error.
- `get_device_profile(device_id: str) -> Dict[str, Any]` — metadatos del dispositivo (modelo, capacidades, etc.).
- `send_command(device_id: str, command_data: Dict[str, Any]) -> bool` — envía un comando; retornar `True` si se aceptó/ejecutó, `False` si falló.
- `get_devices_list() -> List[Dict[str, Any]]` — lista de dispositivos en la cuenta; cada ítem debe contener al menos `device_id`, `device_type`, `model`, `alias`/`name`, `brand`.

### Estructura de la clase de acuerdo a como se consuma la API, incluso adaptar si se usa MQTT

1. Constructor: configurar `requests.Session()` (o cliente HTTP), inyectar credenciales y valores de configuración (timeout, base_url).
2. Método helper `_make_request()` centralizado para:
   - añadir headers comunes (Authorization, x-client-id, etc.),
   - manejar timeouts, reintentos simples o backoff (opcional),
   - mapear errores HTTP a excepciones conocidas (p. ej. dispositivo offline).
3. Implementar los métodos de la interfaz usando `_make_request()` y normalizar la respuesta para que los `Plugin`s no dependan del formato crudo.

Ejemplo de esqueleto:

```python
class MiBrandClient(BaseClient):
	def __init__(self, base_url: str, access_token: str, client_id: str):
		self.base_url = base_url
		self.session = requests.Session()
		self.session.headers.update({'Authorization': f'Bearer {access_token}', 'x-client-id': client_id})

	def _make_request(self, method, endpoint, params=None, json_data=None):
		url = f"{self.base_url}{endpoint}"
		resp = self.session.request(method, url, params=params, json=json_data, timeout=30)
		resp.raise_for_status()
		return resp.json()

	def get_devices_list(self):
		data = self._make_request('GET', '/devices')
		# Normalizar a la estructura esperada por los plugins
		return [{'device_id': d['id'], 'device_type': d['type'], 'model': d.get('model'), 'alias': d.get('alias'), 'brand': 'mi_brand'} for d in data.get('devices', [])]

	def get_device_state(self, device_id):
		try:
			data = self._make_request('GET', f'/devices/{device_id}/state')
			return data.get('state', {})
		except Exception:
			return {}

	def get_device_profile(self, device_id):
		data = self._make_request('GET', f'/devices/{device_id}/profile')
		return data.get('profile', {})

	def send_command(self, device_id, command_data):
		try:
			resp = self._make_request('POST', f'/devices/{device_id}/control', json_data=command_data)
			return resp.get('result', False)
		except Exception:
			return False
```

### Buenas prácticas

- Normaliza las respuestas: los `Plugin`s esperan dicts/arrays previsibles; documenta cualquier campo especial.
- Nunca propagues excepciones inesperadas al `DeviceManager` — captura y maneja en el client, devolviendo valores vacíos o `False` según corresponda.
- Implementa logs (`logger.debug`/`logger.info`/`logger.warning`) en los puntos clave (peticiones, respuestas inesperadas, errores de auth).
- Maneja errores de autenticación (refresh token) en el client: si la API usa OAuth, añade un método para refrescar el token y reintentar la petición.
- Agrega timeouts y opcionalmente reintentos con backoff exponencial para llamadas inestables.
- Para APIs que devuelven códigos especiales (p. ej. 416 para dispositivo offline), define excepciones específicas (como `LGDeviceOfflineError`) para diferenciar casos.

### Integración con `Plugin`s

- Los `Plugin`s deben exponer un método `get_api_client()` que instancie y retorne el client. `PluginManager` llamará `plugin.get_api_client()` antes de usar otros métodos.
- Asegúrate de que `get_devices_list()` devuelva campos mínimos para que `AppManager` y `DeviceManager` puedan crear `DeviceState`s.

### Tests / Verificación

- Escribe tests unitarios para `_make_request()` (simular respuestas HTTP con `responses` o `requests-mock`).
- Testea `get_devices_list()` con ejemplos de respuesta cruda y valida la estructura normalizada.
- Verifica `send_command()` con casos de éxito y fallo (dispositivo offline).

### Ejemplo real en este repositorio

Revisa `brandconnectors/lg_client.py` como ejemplo de implementación real: usa `requests.Session`, centraliza `_make_request()` y trata códigos HTTP especiales (por ejemplo 416) lanzando `LGDeviceOfflineError`.

---
Documentación creada para facilitar la implementación de nuevos conectores API.

