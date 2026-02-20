from pathlib import Path
from dataclasses import dataclass

@dataclass
class Config:
    CONFIG_DIR = Path('./.smarthome/')
    CONFIG_FILE = CONFIG_DIR / 'config.conf'

    def __post_init__(self):
        # Crear directorios si no existen
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Crear archivo si no existe
        if not self.CONFIG_FILE.exists():
            self._create_credentials_template()

    def _create_credentials_template(self):
        """Crear plantilla de credenciales"""
        template = """
[HAPCONFIG]
port = 51827
persist_file_name = homekit.json
bridge_name = Mi Raspberry Hub

[LG]
access_token = TU_ACCESS_TOKEN_AQUI
message_id = TU_MESSAGE_ID
client_id = TU_CLIENT_ID
"""
        with open(self.CONFIG_FILE, 'w') as f:
            f.write(template)
        
        print(f"Plantilla creada en: {self.CONFIG_FILE}")
        print("Edita el archivo y agrega tus credenciales")


config = Config()