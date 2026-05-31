# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SmartHomeBridge is a Python-based DIY software bridge that connects IoT devices to Apple HomeKit and Samsung SmartThings. It supports multiple brands (LG, Samsung, Xiaomi) through a plugin architecture and provides bidirectional communication between cloud APIs and smart home platforms.

## Common Development Tasks

### Environment Setup
```bash
# Create virtual environment and install dependencies
make install

# Run the bridge
make run

# Check Python version compatibility
make check

# Clean virtual environment
make clean
```

### Configuration
Configuration files are stored in `./.smarthome/`. The main configuration file `config.conf` is automatically created with a template on first run if missing. Edit this file with your credentials:

- `[HAPCONFIG]` – HomeKit bridge settings (port, PIN, persist file)
- `[SMARTTHINGS]` – SmartThings OAuth credentials and endpoint settings
- `[LG]` – LG ThinQ API credentials
- `[TELEGRAM]` – Telegram bot notifications (optional)

SmartThings device configuration is stored in `smartthings_device_conf.json` (generated from device profiles).

### Running Tests
```bash
# Run the test server for SmartThings (legacy)
python testsmart.py
```

### Docker Deployment
```bash
# Using docker-compose
docker compose -f compose.yaml up
```

The Docker configuration maps `~/public/SMARTHOME` to `/app/.smarthome` for persistent configuration storage. Adjust the volume path in `compose.yaml` as needed. Environment variables can be set via `.env` file.

### Development Workflow
1. **Setup**: Run `make install` to create virtual environment and install dependencies
2. **Configuration**: Edit `./.smarthome/config.conf` with your credentials
3. **Run**: Execute `make run` to start the bridge
4. **Debug**: Check logs in `./.smarthome/homebridge_hap.log`
5. **Testing**: Use `testsmart.py` for isolated SmartThings endpoint testing
6. **Adding Brands**: Follow the plugin architecture pattern in `plugins/` and `brandconnectors/`

## Architecture

For detailed execution flow diagrams and timing, see `FLUJO_EJECUCION.md`.

### Core Components
1. **AppManager** (`core/app_manager.py`) – Orchestrates plugin discovery, device management, and service startup
2. **PluginManager** (`core/plugin_manager.py`) – Discovers and loads brand plugins dynamically
3. **DeviceManager** (`core/device_manager.py`) – Central registry of device states with synchronization loop
4. **DeviceFactory** (`core/device_factory.py`) – Creates device instances from plugin data

### Plugin System
- **BasePlugin** (`plugins/base_plugin.py`) – Abstract base class for all brand plugins
- **Brand Plugins** (`plugins/lg_plugin.py`, `plugins/samsung_plugin.py`, `plugins/xiaomi_plugin.py`) – Implement device discovery and control for specific brands
- **Brand Clients** (`brandconnectors/`) – API clients for each brand (LG ThinQ, Samsung SmartThings, Xiaomi)

### Bridges
- **HAPBridge** (`bridges/hap_bridge.py`) – Translates device states to HomeKit accessories
- **SmartThingsBridge** (`bridges/smartthings_bridge.py`) – Translates device states to SmartThings devices

### Services
- **HAPService** (`services/hap_service.py`) – HomeKit Accessory Protocol server using `pyhap`
- **SmartThingsService** (`services/smartthings_service.py`) – SmartThings webhook server using Flask

### Models
- **Device Models** (`models/`) – Structured device profiles and states per brand
- **LG Washer** (`models/LG/washer.py`) – Example implementation with full state/command models

### Data Flow
1. **Discovery**: PluginManager discovers devices via brand APIs → DeviceManager creates DeviceState objects
2. **Synchronization**: DeviceManager runs sync loop (default 10s) polling plugins for state updates
3. **Bridge Registration**: Bridges subscribe to device state changes and create platform-specific accessories
4. **Command Handling**: User interactions → Bridge → DeviceManager → Plugin → Brand API
5. **State Updates**: Plugin polling → DeviceManager.update_device_state() → Bridge callbacks → Service updates

### Threading Model
- **Main thread**: Orchestrates startup and monitors service threads
- **Sync thread** (daemon): Polls device states every configurable interval (default 10s)
- **HomeKit thread**: Runs blocking HAP server
- **SmartThings thread**: Runs Flask web server

## Key Design Patterns

### Plugin Architecture
New brands can be added by:
1. Creating `plugins/{brand}_plugin.py` implementing BasePlugin
2. Creating `brandconnectors/{brand}_client.py` extending BaseClient
3. Adding device models in `models/{brand}/`
4. Adding accessory implementations in `bridges/homekit/` and `bridges/smartthings/`

### State Management
- DeviceState objects are brand-agnostic containers for device state
- Plugins convert brand-specific API responses to DeviceState-compatible dictionaries
- Bridges translate DeviceState to platform-specific representations (HAP characteristics, SmartThings capabilities)

### Bridge Pattern
Each smart home platform has:
- A bridge that maps DeviceState to platform accessories
- An accessory implementation per device type (e.g., `LGWasherAccessory`)
- A service that handles platform-specific communication (HAP driver, Flask endpoints)

## Configuration Notes

### HomeKit
- PIN code defaults to `031-45-154` (editable in config.conf)
- Persistence file: `./.smarthome/homekit.json`
- Port: 51827 (configurable)

### SmartThings
- Requires public IP, domain name, and HTTPS (typically via nginx reverse proxy)
- OAuth flow handled by SmartThingsService
- Device configuration must match `smartthings_device_conf.json`

### Device Profiles
SmartThings integration requires device profile definitions that map physical devices to SmartThings capabilities. Example LG washer profile is included as `Device profile (Lavadora LG).json`. To add new device types:

1. Create a device profile in the SmartThings Developer Workspace
2. Export the profile JSON and place it in the project root
3. Update `smartthings_device_conf.json` with the external device IDs and mapping

The `smartthings_device_conf.json` file maps discovered device IDs to SmartThings device definitions with fields:
- `externalDeviceId`: Device ID from plugin discovery
- `friendlyName`: Display name in SmartThings app
- `deviceHandlerType`: Capability profile ID from SmartThings
- `manufacturerName`, `modelName`, `hwVersion`, `swVersion`: Device metadata
- `roomName`, `groups`, `categories`: Organizational metadata

### Logging
Logs to `./.smarthome/homebridge_hap.log` with rotation. Log level is INFO by default.

## Adding New Device Types

1. **Create Plugin Support**
   - Add device type to plugin's `get_supported_devices()` list
   - Implement `create_device()` factory method
   - Ensure `get_device_state()` returns appropriate state model

2. **Create Device Model**
   - Add model class in `models/{brand}/`
   - Include from_json/to_dict methods for API response parsing

3. **Create HomeKit Accessory**
   - Add `{Brand}{DeviceType}Accessory.py` in `bridges/homekit/`
   - Inherit from `pyhap.accessory.Accessory`
   - Implement `update_from_device_state()` to map DeviceState to HAP characteristics

4. **Create SmartThings Accessory**
   - Add corresponding file in `bridges/smartthings/`
   - Implement `to_discovery_dict()`, `state_refresh_request()`, `handle_smartthings_command()`

5. **Update Bridge Factories**
   - Extend `_create_accessory()` methods in both bridges to recognize new device type

## Common Issues & Debugging

### Plugin Discovery Fails
- Check brand API credentials in config.conf
- Verify network connectivity to brand cloud APIs
- Check plugin logs for authentication errors

### HomeKit Not Showing Devices
- Verify HAPService starts successfully (logs show PIN)
- Check that accessories are created in HAPBridge
- Ensure DeviceManager has discovered devices before bridge registration

### SmartThings OAuth Flow Issues
- Ensure nginx reverse proxy is configured for HTTPS
- Verify callback URLs match SmartThings developer console
- Check `smartthingsSettings.json` for valid tokens

### State Sync Not Working
- DeviceManager sync interval defaults to 10s (adjustable via `start_sync(interval)`)
- Check plugin `get_device_state()` implementation returns proper state dict
- Verify DeviceState.callbacks are registered (bridges subscribe on add_device)

## File Structure Summary

```
.
├── main.py                    # Entry point
├── config.py                  # Configuration management
├── core/                      # Core orchestration
│   ├── app_manager.py        # Main application lifecycle
│   ├── device_manager.py     # Device state management
│   ├── plugin_manager.py     # Dynamic plugin loading
│   └── device_factory.py     # Device instance creation
├── plugins/                   # Brand plugins
│   ├── base_plugin.py        # Abstract plugin interface
│   ├── lg_plugin.py          # LG ThinQ integration
│   ├── samsung_plugin.py     # Samsung SmartThings integration
│   └── xiaomi_plugin.py     # Xiaomi integration
├── brandconnectors/           # API clients
│   ├── base_client.py        # Base HTTP client
│   ├── lg_client.py          # LG ThinQ API client
│   ├── samsung_client.py     # Samsung API client
│   └── xiaomi_client.py      # Xiaomi API client
├── bridges/                   # Platform bridges
│   ├── hap_bridge.py         # HomeKit bridge
│   ├── homekit/              # HomeKit accessory implementations
│   ├── smartthings_bridge.py # SmartThings bridge
│   └── smartthings/          # SmartThings accessory implementations
├── services/                  # Platform services
│   ├── hap_service.py        # HomeKit HAP server
│   ├── smartthings_service.py # SmartThings web server
│   └── base_service.py       # Base service interface
├── models/                    # Device models
│   ├── base.py               # Base device classes
│   ├── LG/                   # LG device models
│   ├── Samsung/              # Samsung device models
│   └── Xiaomi/               # Xiaomi device models
├── database/                  # Database layer (unused in current version)
├── .smarthome/               # Configuration directory (created at runtime)
│   ├── config.conf           # Main configuration
│   ├── homekit.json          # HomeKit pairing data
│   ├── smartthingsSettings.json # SmartThings OAuth tokens
│   └── smartthings_device_conf.json # SmartThings device definitions
└── testsmart.py              # Legacy SmartThings test server
```

## Dependencies

See `requirements.txt` for full Python dependencies. Key packages:
- `HAP-python` (5.0.0) – HomeKit Accessory Protocol implementation
- `Flask` (3.1.3), `authlib` (1.6.9) – SmartThings OAuth and web server
- `requests` (2.32.5) – HTTP client for brand APIs
- `zeroconf` (0.148.0) – mDNS discovery for HomeKit
- `cryptography` (46.0.4) – Security for HAP

Python 3.10+ is required (configured in makefile).

## Development Notes

- The project uses Python 3.10+ (configured in makefile)
- All paths are relative to project root
- Configuration is managed via configparser with fallbacks
- Logging uses Python's standard logging module with file and stdout handlers
- Thread safety in DeviceManager uses `threading.Lock` for state updates
- Error handling is exception-based with comprehensive logging