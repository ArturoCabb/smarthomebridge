"""
Servicio SmartThings que maneja webhooks y comunicación con SmartThings API
"""
import logging
import json
import secrets
from typing import Dict, Optional, Callable
from pathlib import Path
from flask import Flask, request, render_template_string, redirect, jsonify
from requests import post as send_req
from uuid import uuid4
import configparser
import time
from config import config

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Manejador de webhooks para eventos de SmartThings"""
    def __init__(self):
        self.on_device_event: Optional[Callable] = None


class SmartThingsService:
    """Servicio SmartThings con Flask app para webhooks"""

    def __init__(self):
        self.accessories: Dict[str, object] = {}
        self.webhook = WebhookHandler()

        # Configuración
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(config.CONFIG_FILE)

        # Credenciales
        self.credentials = {}
        self.code = ""
        self.callback_urls = {}
        self.access_token = ""
        self.refresh_token = ""
        # token expiry info (segundos desde obtención)
        self.expires_in: int = 0
        self.token_obtained_at: float = 0.0

        # Flask app
        self.app = Flask(__name__)
        self.app.logger.setLevel(logging.INFO)

        # Configuración de Flask
        self._host = self.config_parser.get('SMARTTHINGS', 'host', fallback='0.0.0.0')
        self._port = self.config_parser.getint('SMARTTHINGS', 'port', fallback=5001)
        self._cred_file = self.config_parser.get('SMARTTHINGS', 'credentials_file', fallback='./.smarthome/smartthingsSettings.json')

        # Credenciales de cliente
        self.my_client_id = self.config_parser.get('SMARTTHINGS', 'my_client_id', fallback='')
        self.my_client_secret = self.config_parser.get('SMARTTHINGS', 'my_client_secret', fallback='')
        self.st_client_id = self.config_parser.get('SMARTTHINGS', 'St_Client_Id', fallback='')
        self.st_client_secret = self.config_parser.get('SMARTTHINGS', 'St_Client_Secret', fallback='')

    def initialize(self):
        """Inicializar el servicio SmartThings"""
        logger.info("Inicializando servicio SmartThings...")

        # Cargar credenciales guardadas
        self._load_credentials()

        # Configurar rutas Flask
        self._setup_routes()

        logger.info(f"SmartThings Service configurado en {self._host}:{self._port}")

    def _load_credentials(self):
        """Cargar credenciales desde archivo JSON"""
        try:
            cred_path = Path(self._cred_file)
            if cred_path.exists():
                with open(cred_path, 'r') as f:
                    creds_list = json.load(f)

                if len(creds_list) > 0:
                    self.credentials = creds_list[0]  # authentication
                if len(creds_list) > 1:
                    callback_auth = creds_list[1].get('callbackAuthentication', {})
                    self.code = callback_auth.get('code', '')
                if len(creds_list) > 2:
                    self.callback_urls = creds_list[2].get('callbackUrls', {})
                if len(creds_list) > 3:
                    callback_auth = creds_list[3].get('callbackAuthentication', {})
                    self.access_token = callback_auth.get('accessToken', '')
                    self.refresh_token = callback_auth.get('refreshToken', '')
                    self.expires_in = callback_auth.get('expiresIn', 0) or 0
                    self.token_obtained_at = callback_auth.get('obtainedAt', 0.0) or 0.0

                logger.info("Credenciales cargadas desde archivo")
        except Exception as e:
            logger.warning(f"No se pudieron cargar credenciales: {e}")

    def _setup_routes(self):
        """Configurar rutas Flask"""

        @self.app.route('/oauth/login', methods=['GET', 'POST'])
        def oauth_login():
            if request.method == 'GET':
                client_id = request.args.get('client_id')
                redirect_uri = request.args.get('redirect_uri')
                state = request.args.get('state')

                logger.info(f"OAuth login request - Client: {client_id}")

                if client_id != self.my_client_id:
                    return "Acceso denegado", 401

                if not redirect_uri:
                    redirect_uri = "https://c2c-us.smartthings.com/oauth/callback"

                return render_template_string('''
                    <h2>Autorizar a SmartThings</h2>
                    <form method="post">
                        <input type="hidden" name="redirect_uri" value="{{ redirect_uri }}">
                        <input type="hidden" name="state" value="{{ state }}">
                        <input type="hidden" name="client_id" value="{{ client_id }}">
                        <button type="submit" name="approve">Permitir</button>
                    </form>
                ''', redirect_uri=redirect_uri, state=state, client_id=client_id), 201

            else:  # POST
                if 'approve' in request.form:
                    redirect_uri = request.form.get('redirect_uri')
                    state = request.form.get('state')
                    client_id = request.form.get('client_id')

                    self.code = secrets.token_urlsafe(32)
                    final_url = f"{redirect_uri}?code={self.code}&state={state}"

                    logger.info(f"OAuth aprobado - Redirigiendo a {redirect_uri}")
                    return redirect(final_url), 200
                else:
                    return "Acceso denegado", 403

        @self.app.route('/oauth/token', methods=['POST'])
        def oauth_token():
            logger.info("Token request")

            # Generar tokens
            access_token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)

            self.access_token = access_token
            self.refresh_token = refresh_token

            final_token = {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': 3600,
                'refresh_token': refresh_token
            }

            logger.info("Token generado")
            return final_token

        @self.app.route('/target-endpoint', methods=['GET', 'POST'])
        def target_endpoint():
            respuesta = {}
            data = request.get_json() if request.is_json else request.form.to_dict()
            if not data:
                return {'error': 'No data received'}, 400

            request_id = data.get('headers', {}).get('requestId')
            operation_type = data.get('headers', {}).get('interactionType')

            logger.info(f"Target endpoint - Operación: {operation_type}")

            if operation_type == "discoveryRequest":
                respuesta = self._handle_discovery_request(request_id)
            elif operation_type == "stateRefreshRequest":
                devices = data.get("devices", [])
                respuesta = self._handle_state_refresh(request_id, devices)
            elif operation_type == "commandRequest":
                devices = data.get("devices", [])
                respuesta = self._handle_command_request(request_id, devices)
            elif operation_type == "grantCallbackAccess":
                respuesta = self._handle_grant_callback_access(data)
            return respuesta, 200

        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return {'status': 'healthy', 'service': 'SmartThings'}, 200

    def _handle_discovery_request(self, request_id):
        """Manejar solicitud de descubrimiento"""
        result = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "discoveryResponse",
                "requestId": request_id
            },
            "requestGrantCallbackAccess": True,
            "devices": [
                acc.to_discovery_dict() for acc in self.accessories.values()
            ]
        }
        return result

    def _handle_state_refresh(self, request_id, devices):
        """Manejar solicitud de refresco de estado"""
        result = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "stateRefreshResponse",
                "requestId": request_id
            },
            "deviceState": [
                acc.state_refresh_request() for acc in self.accessories.values()
            ]
        }
        return result

    def _handle_command_request(self, request_id, devices):
        """Manejar solicitud de comando"""
        result = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "commandResponse",
                "requestId": request_id
            },
            "deviceState": [
                acc.to_command_request() for acc in self.accessories.values()
            ]
        }
        return result

    def _handle_grant_callback_access(self, data):
        """Manejar otorgamiento de acceso callback"""
        try:
            self.code = data.get("callbackAuthentication", {}).get("code", "")
            self.callback_urls = data.get("callbackUrls", {})

            # Solicitar token de acceso
            self._request_access_token()

            # Guardar credenciales
            self._save_credentials()

            logger.info("Acceso callback otorgado y tokens guardados")
            return {'status': 'success'}
        except Exception as e:
            logger.error(f"Error otorgando callback access: {e}")
            return {'error': str(e)}, 400

    def _request_access_token(self):
        """Solicitar token de acceso a SmartThings"""
        if not self.callback_urls.get('oauthToken'):
            logger.warning("Callback URL de OAuth no disponible")
            return

        message = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "accessTokenRequest",
                "requestId": str(uuid4())
            },
            "callbackAuthentication": {
                "grantType": "authorization_code",
                "code": self.code,
                "clientId": self.st_client_id,
                "clientSecret": self.st_client_secret
            }
        }

        try:
            result = send_req(self.callback_urls['oauthToken'], json=message)
            if result.status_code == 200:
                response = result.json()
                callback_auth = response.get('callbackAuthentication', {})
                self.access_token = callback_auth.get('accessToken', '')
                self.refresh_token = callback_auth.get('refreshToken', '')
                # extraer expiración si viene
                self.expires_in = response.get('expiresIn', callback_auth.get('expiresIn', 0)) or 0
                self.token_obtained_at = time.time()
                logger.info("Token de acceso obtenido")
        except Exception as e:
            logger.error(f"Error solicitando token de acceso: {e}")

    def _refresh_access_token(self) -> bool:
        """
        Renovar token de acceso usando el refresh token.
        Se llama cuando el access token expira (401/403 responses) o de forma proactiva.

        Returns:
            True si se renovó exitosamente, False si falló
        """
        if not self.refresh_token:
            logger.warning("No refresh_token disponible para renovación")
            return False

        if not self.callback_urls.get('oauthToken'):
            logger.warning("Callback URL de OAuth no disponible para refresh")
            return False

        message = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "refreshTokenRequest",
                "requestId": str(uuid4())
            },
            "callbackAuthentication": {
                "grantType": "refresh_token",
                "refreshToken": self.refresh_token,
                "clientId": self.st_client_id,
                "clientSecret": self.st_client_secret
            }
        }

        try:
            result = send_req(self.callback_urls['oauthToken'], json=message)
            if result.status_code == 200:
                response = result.json()
                callback_auth = response.get('callbackAuthentication', {})
                self.access_token = callback_auth.get('accessToken', '')
                self.refresh_token = callback_auth.get('refreshToken', '')
                self.expires_in = response.get('expiresIn', callback_auth.get('expiresIn', 0)) or 0
                self.token_obtained_at = time.time()
                self._save_credentials()
                logger.info("Token de acceso renovado exitosamente")
                return True
            else:
                logger.error(f"Error renovando token: {result.status_code} - {result.text}")
                return False
        except Exception as e:
            logger.error(f"Error renovando token de acceso: {e}")
            return False

    def _save_credentials(self):
        """Guardar credenciales en archivo JSON"""
        try:
            creds = [
                self.credentials,
                {"callbackAuthentication": {"code": self.code}},
                {"callbackUrls": self.callback_urls},
                {"callbackAuthentication": {
                    "accessToken": self.access_token,
                    "refreshToken": self.refresh_token,
                    "expiresIn": self.expires_in,
                    "obtainedAt": self.token_obtained_at
                }}
            ]

            # make sure parent directory exists
            cred_path = Path(self._cred_file)
            if cred_path.parent and not cred_path.parent.exists():
                cred_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Creada carpeta de credenciales: {cred_path.parent}")

            with open(cred_path, 'w') as f:
                json.dump(creds, f, indent=2)

            logger.info("Credenciales guardadas")
        except Exception as e:
            logger.error(f"Error guardando credenciales: {e}")

    def _token_expired(self) -> bool:
        """Return True if the currently held access token appears expired."""
        if self.expires_in <= 0 or self.token_obtained_at <= 0:
            return False
        # consider a small safety margin
        return time.time() > self.token_obtained_at + self.expires_in - 60

    def add_accessory(self, device_id: str, accessory):
        """
        Agregar un accesorio al servicio.

        Args:
            device_id: ID único del dispositivo
            accessory: Objeto accesorio SmartThings
        """
        if device_id in self.accessories:
            logger.warning(f"Accesorio ya existe: {device_id}")
            return False

        self.accessories[device_id] = accessory
        logger.info(f"Accesorio agregado: {device_id}")
        return True

    def remove_accessory(self, device_id: str):
        """Remover un accesorio"""
        if device_id in self.accessories:
            del self.accessories[device_id]
            logger.info(f"Accesorio removido: {device_id}")
            return True
        return False

    def get_access_token(self) -> Optional[str]:
        """Obtener token de acceso actual"""
        return self.access_token if self.access_token else None

    def get_callback_url(self) -> Optional[str]:
        """Obtener URL de callback para notificaciones (stateCallback)"""
        return self.callback_urls.get('stateCallback') if self.callback_urls else None

    def start(self):
        """Iniciar el servidor Flask (bloqueante)"""
        if not self.app:
            raise RuntimeError("Servicio SmartThings no inicializado. Llama a initialize() primero")

        logger.info("=" * 60)
        logger.info("Iniciando servidor SmartThings...")
        logger.info(f"Accesorios registrados: {len(self.accessories)}")
        logger.info(f"Endpoint: http://{self._host}:{self._port}")
        logger.info("=" * 60)

        # Iniciar Flask (bloqueante)
        self.app.run(host=self._host, port=self._port, debug=False, use_reloader=False)

    def stop(self):
        """Detener el servidor Flask"""
        logger.info("Deteniendo servidor SmartThings...")
        # Flask no tiene método stop() directo, se maneja con signals externamente
        logger.info("Servidor SmartThings detenido")
