# Flujo de Ejecución - ControlSmartHome

## 📊 Diagrama General

```
main.py (Punto de entrada)
    ↓
AppManager.__init__()
    ├─ PluginManager() → Descubre plugins automáticamente
    ├─ DeviceManager() → Gestor de dispositivos
    └─ HAPService() → Servicio HomeKit
    ↓
AppManager.start()
    ├─ 1️⃣ initialize() → Descubre y agrega dispositivos
    │   ├─ _discover_all_devices()
    │   │   └─ plugin.discover_devices() [LG, Samsung, Xiaomi]
    │   └─ device_manager.add_device() [SINCRÓNICO]
    │
    ├─ 2️⃣ device_manager.start_sync() [HILO SINCRONIZACIÓN]
    │   └─ Cada 30s: Actualiza estado de todos los dispositivos
    │
    └─ 3️⃣ Hilo HomeKit (_homekit)
        ├─ hap_service.initialize()
        ├─ HAPBridge() → Conecta DeviceManager con HAP
        ├─ Agrega dispositivos al bridge (add_device)
        │   └─ Se suscribe a cambios: subscribe_to_device()
        └─ hap_service.start() [BLOQUEANTE - Servidor HomeKit]
```

---

## 🔄 Ciclo de Actualización de Estado

```
DeviceManager.start_sync() [HILO]
    ↓
Cada 30 segundos:
    ├─ _sync_devices()
    │   └─ Para cada dispositivo:
    │       ├─ plugin.get_device_state(device_id)
    │       ├─ device_state.state = nuevo_estado
    │       └─ _notify_callbacks(device_state) ← LLAMA A SUSCRIPTORES
    │
    └─ HAPBridge._on_device_state_changed(device_state)
        └─ accessory.update_from_device_state(device_state)
```

---

## 📁 Orden de Inicialización de Archivos

### **FASE 1: ARRANQUE (sincrónico)**

```
1. main.py
   ↓
2. core/app_manager.py (AppManager.__init__)
   ├─ core/plugin_manager.py
   │   ├─ plugins/base_plugin.py
   │   ├─ plugins/lg_plugin.py
   │   ├─ plugins/samsung_plugin.py
   │   └─ plugins/xiaomi_plugin.py
   ├─ core/device_manager.py
   ├─ core/device_factory.py
   └─ services/hap_service.py

3. AppManager.start() → initialize()
   ├─ core/plugin_manager.py (discovery)
   ├─ brandconnectors/*.py (obtener API clients)
   └─ core/device_manager.py (add_device)
```

### **FASE 2: EJECUCIÓN (hilos paralelos)**

```
HILO PRINCIPAL:
  ├─ core/device_manager.py::start_sync() [DAEMON]
  │   └─ Actualiza estado cada 30s
  │
  └─ Monitorea el hilo HomeKit
     └─ Si falla, registra error

HILO HOMEKIT:
  ├─ services/hap_service.py::initialize()
  ├─ bridges/hap_bridge.py::add_device()
  │   └─ homekit/LGWasherAccessory.py (ejemplo)
  └─ services/hap_service.py::start() [BLOQUEANTE]
     └─ Servidor HAP escuchando en puerto 5222
```

---

## 🔗 Flujo de Datos: Estado del Dispositivo

```
Plugin (LG, Samsung, Xiaomi)
    ↓
plugin.get_device_state()
    ↓
DeviceManager._sync_devices()
    ├─ Actualiza device_state.state
    ├─ Llama a callbacks registrados
    └─ Callback: HAPBridge._on_device_state_changed()
        ↓
        Accesorio HAP
        └─ update_from_device_state()
            ├─ Actualiza propiedades HomeKit
            └─ Notifica a HomeKit si cambiaron
```

---

## 📋 Arquitectura de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│                    (Punto de entrada)                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    AppManager                               │
│  • initialize(): Descubre dispositivos                      │
│  • start(): Inicia hilos                                    │
│  • stop(): Detiene servicios                                │
└─┬────────────────────┬────────────────────────┬─────────────┘
  │                    │                        │
  ▼                    ▼                        ▼
┌─────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ PluginManager   │ │ DeviceManager    │ │  HAPService      │
│                 │ │                  │ │                  │
│ • Descubre      │ │ • Mantiene estado│ │ • Crea driver    │
│   plugins       │ │ • Sincroniza     │ │ • Crea bridge    │
│ • LG, Samsung   │ │ • Notifica       │ │ • Gestiona       │
│   Xiaomi        │ │   cambios        │ │   accesorios     │
└────────┬────────┘ └────────┬─────────┘ └─────────┬────────┘
         │                   │                     │
         └───────────────────┼─────────────────────┘
                             │
                ┌────────────▼────────────┐
                │    HAPBridge           │
                │                        │
                │ • Conecta Manager      │
                │   con HAP Service      │
                │ • Traduce estados      │
                │ • Crea accesorios      │
                └────────┬───────────────┘
                         │
            ┌────────────▼────────────┐
            │  Accesorios HAP         │
            │                         │
            │ • LGWasherAccessory     │
            │ • Samsung...            │
            │ • Xiaomi...             │
            └─────────────────────────┘
```

---

## ⚙️ Parámetros Clave

| Componente | Parámetro | Valor | Propósito |
|-----------|-----------|-------|----------|
| DeviceManager | `_sync_interval` | 30s | Frecuencia de actualización |
| HAPService | `port` | 5222 | Puerto del servidor HomeKit |
| HAPService | `pincode` | config | PIN para emparejar |
| AppManager | `daemon=True` | Sí | Hilo HomeKit muere con app |

---

## 🚨 Puntos Críticos

### 1. **Lock en DeviceManager**
```python
with self._lock:
    # Actualización thread-safe de estado
```
Previene race conditions entre hilos de sincronización y actualizaciones.

### 2. **Callbacks - Cómo se notifican cambios**
```python
# En add_device (hap_bridge.py):
subscribe_to_device(device_id, _on_device_state_changed)

# En sync (device_manager.py):
_notify_callbacks(device_state)  # Llama a todos los subscribers
```

### 3. **Hilo HomeKit Daemon**
```python
Thread(target=_homekit, daemon=True)
```
- Si falla, mata todo
- Ahora registra errores y los detecta

---

## 🔍 Estados Posibles del Dispositivo

```
CICLO DE VIDA:

1. Descubrimiento (discover_devices)
   └─ plugin devuelve device_info

2. Agregación (add_device)
   └─ DeviceManager crea DeviceState

3. Registración HAP (add_device en bridge)
   └─ HAPBridge crea Accessory
   └─ Se suscribe a cambios

4. Sincronización (sync cada 30s)
   └─ Obtiene estado del plugin
   └─ Actualiza DeviceState
   └─ Notifica a Accessory

5. Actualización HomeKit
   └─ Accessory actualiza propiedades
   └─ HomeKit notifica clientes (iPhone, etc)
```

---

## 📊 Vista Temporal

```
TIEMPO │ HILO PRINCIPAL        │ HILO SYNC (cada 30s)   │ HILO HOMEKIT
────────┼─────────────────────┼──────────────────────┼─────────────────
  0s   │ initialize()        │                      │ Esperando...
       │ ├─ discover         │                      │
       │ └─ add_device       │                      │
       │ start_sync()        │ [INICIA]             │
       │ start_homekit()     │                      │ initialize()
       │                     │                      │ add_device()
  1s   │ Monitorea hilo      │ [ESPERANDO]          │ Agrega accesorios
       │                     │                      │ start() [BLOQUEANTE]
  30s  │ [ESPERANDO]         │ _sync_devices()      │ [ESCUCHANDO]
       │                     │ ├─ get_state()       │
       │                     │ └─ notify_callbacks()│ update_from_state()
       │                     │ [ESPERANDO]          │
  60s  │ [ESPERANDO]         │ _sync_devices()      │ [ESCUCHANDO]
       │                     │ ├─ get_state()       │
       │                     │ └─ notify_callbacks()│ update_from_state()
```

