from pathlib import Path
import configparser

class ConfigFile:
    CONFIG_DIR = Path('./.smarthome/')
    CONFIG_FILE = CONFIG_DIR / 'config.conf'

class Config:
    CONFIG_FILE = ConfigFile().CONFIG_FILE

    def __init__(self):
        ConfigFile.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not ConfigFile.CONFIG_FILE.exists():
            self._create_credentials_template()

    def _create_credentials_template(self):
        """Crear plantilla de credenciales"""
        template = """
[HAPCONFIG]
address =
port = 51827
pincode = 031-45-154
persist_file_name = ./.smarthome/homekit.json
listen_address =
bridge_name = Mi Raspberry Hub

[SMARTTHINGS]
host = 0.0.0.0
port = 5001
my_client_id = TU_CLIENT_ID
my_client_secret = TU_CLIENT_SECRET
Endpoint_App_Id = TU_ENDPOINT_ID
St_Client_Id = TU_ST_CLIENT_ID
St_Client_Secret = TU_ST_CLIENT_SECRET
credentials_file = ./.smarthome/smartthingsSettings.json

[LG]
base_url = https://api-aic.lgthinq.com
access_token = TU_ACCESS_TOKEN_AQUI
message_id = TU_MESSAGE_ID
client_id = TU_CLIENT_ID

[TELEGRAM]
base_url = https://api.telegram.org/bot\{id\}/sendMessage
chat_id = TU_CHAT_ID

"""
        with open(ConfigFile().CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(template)

        print(f"Plantilla creada en: {ConfigFile().CONFIG_FILE}")
        print("Edita el archivo y agrega tus credenciales")

config = Config()

config_parser = configparser.ConfigParser()
config_parser.read(ConfigFile().CONFIG_FILE, encoding='utf-8')

class HAPConfig:
    address = config_parser.get('HAPCONFIG', 'address', fallback=None)
    port = config_parser.getint('HAPCONFIG', 'port', fallback=51827)
    pincode = config_parser.get('HAPCONFIG', 'pincode', fallback="031-45-154").encode()
    persist_file_name = config_parser.get('HAPCONFIG', 'persist_file_name', fallback="./homekit.json")
    listen_address = config_parser.get('HAPCONFIG', 'listen_address', fallback=None)
    bridge_name = config_parser.get('HAPCONFIG', 'bridge_name', fallback="Mi Raspberry Hub")

class SmartThingsConfig:
    my_client_id = config_parser.get("SMARTTHINGS", "my_client_id")
    my_client_secret = config_parser.get("SMARTTHINGS", "my_client_secret")
    Endpoint_App_Id = config_parser.get("SMARTTHINGS", "Endpoint_App_Id")
    St_Client_Id = config_parser.get("SMARTTHINGS", "St_Client_Id")
    St_Client_Secret = config_parser.get("SMARTTHINGS", "St_Client_Secret")
    host = config_parser.get("SMARTTHINGS", "host")
    port = config_parser.getint("SMARTTHINGS", "port")
    credentials_file = config_parser.get('SMARTTHINGS', 'credentials_file')
    devies_config_file = config_parser.get('SMARTTHINGS', 'devies_conmfig_file', fallback="./.smarthome/smartthingsDevices.json")


class LGClientConfig:
    base_url = config_parser.get('LG', 'base_url')
    access_token = config_parser.get('LG', 'access_token')
    message_id = config_parser.get('LG', 'message_id')
    client_id = config_parser.get('LG', 'client_id')

class TelegramConfig:
    telegram_url = config_parser.get('TELEGRAM', 'base_url')
    telegram_chatid = config_parser.getint('TELEGRAM', 'chat_id')
