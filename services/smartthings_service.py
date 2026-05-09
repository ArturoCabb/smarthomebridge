"""
Servicio SmartThings que maneja el Bridge y accesorios
"""
from flask import Flask, request, render_template_string, redirect, jsonify
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import grants
import secrets
from requests import post as send_req
from json import dumps, loads, JSONDecodeError
from uuid import uuid4
import os
import logging
from typing import Dict
from config import SmartThingsConfig

logger = logging.getLogger(__name__)

class SmartThingsService:
    """Servicio SmartThings"""
    
    # Mapeo seguro de identificadores a URIs permitidas
    ALLOWED_REDIRECT_URIS = [
        "https://c2c-us.smartthings.com/",
        "https://c2c-eu.smartthings.com/",
        "https://c2c-ap.smartthings.com/"
    ]
    
    def __init__(self):
        self.app = Flask(__name__)
        self.accessories: Dict[str, object] = {}  # device_id -> accessory
        self.code = ""
        self.callbackUrlsoauthToken = ""
        self.callbackUrlsstateCallback = ""
        self.token_from_smartthings = ""
        self.refresh_token_sesion_smartthings = ""
        self.my_client_id = SmartThingsConfig().my_client_id
        self.my_client_secret = SmartThingsConfig().my_client_secret
        self.Endpoint_App_Id = SmartThingsConfig().Endpoint_App_Id
        self.St_Client_Id = SmartThingsConfig().St_Client_Id
        self.St_Client_Secret = SmartThingsConfig().St_Client_Secret
        self.host = SmartThingsConfig().host
        self.port = SmartThingsConfig().port
        self.credentials_file = SmartThingsConfig().credentials_file
        self.devies_config_file = SmartThingsConfig().devies_config_file
        
        # Registrar rutas
        self.app.add_url_rule('/', 'health', self.health_check, methods=['GET'])
        self.app.add_url_rule('/oauth/login', 'authorize', self.authorize, methods=['GET', 'POST'])
        self.app.add_url_rule('/oauth/token', 'token', self.token, methods=['POST'])
        self.app.add_url_rule('/target-endpoint', 'target_endpoint', self.target_endpoint, methods=['GET', 'POST'])

    def initialize(self):
        """Inicializar el servicio SmartThings"""
        logger.info("Inicializando servicio SmartThings...")
        
        if os.path.exists(self.credentials_file):
            self.read_conf_file()
            try:
                self.discovery_callback()
            except Exception as e:
                logger.error("Error in discovery_callback: %s", e, exc_info=True)
                try:
                    self.refresh_token()
                except Exception as e2:
                    logger.error("Error refreshing token: %s", e2, exc_info=True)

    def health_check(self):
        """Health check endpoint para nginx y monitoreo"""
        return jsonify({
            "status": "ok",
            "service": "SmartThings",
            "accessories": len(self.accessories)
        }), 200

    def add_accessory(self, device_id: str, accessory):
        if device_id in self.accessories:
            logger.warning("Accesorio ya existe en smartthings service: %s", device_id)
            return False
        
        self.accessories[device_id] = accessory
        logger.info("Accesorio agregado a smartthings service: %s", accessory.external_device_id)
        return True

    def save_shake(self, data):
        with open(self.credentials_file, "w+", encoding='utf-8') as file:
            file.write(dumps(data, indent=2))

    def save_new_token(self, access_token, refresh_token, expieres):
        try:
            with open(self.credentials_file, "r", encoding='utf-8') as file:
                d = loads(file.read())
                d[3]["accessToken"] = access_token
                d[3]["refreshToken"] = refresh_token
                d[3]["expiresIn"] = expieres
                with open(self.credentials_file, "w+", encoding='utf-8') as file:
                    file.write(dumps(d, indent=2))
        except (FileNotFoundError, JSONDecodeError, KeyError, IndexError) as e:
            logger.error("Error saving new token: %s", e, exc_info=True)

    def start(self):
        """Iniciar el servidor smartthings (bloqueante)"""
        logger.info("Servidor smartthings en ejecución...")
        self.app.run(host=self.host, port=self.port)

    def stop(self):
        """Detener el servidor smartthings"""
        return

    def read_conf_file(self):
        try:
            with open(self.credentials_file, "r") as file:
                d = loads(file.read())
                self.code = d[1].get("code", "")
                self.callbackUrlsoauthToken = d[2].get("oauthToken", "")
                self.callbackUrlsstateCallback = d[2].get("stateCallback", "")
                self.token_from_smartthings = d[3].get("accessToken", "")
                self.refresh_token_sesion_smartthings = d[3].get("refreshToken", "")
        except (FileNotFoundError, JSONDecodeError, KeyError, IndexError) as e:
            logger.error("Error reading config file: %s", e, exc_info=True)
            # Reset to defaults
            self.code = ""
            self.callbackUrlsoauthToken = ""
            self.callbackUrlsstateCallback = ""
            self.token_from_smartthings = ""
            self.refresh_token_sesion_smartthings = ""

    def authorize(self):
        if request.method == 'GET':
            client_id = request.args.get('client_id')
            redirect_uri = request.args.get('redirect_uri')
            state = request.args.get('state')
            logger.info("--- [GET /oauth/login] ---")
            if client_id != self.my_client_id:
                return "Denegado, tu no tienes permiso para entrar.", 401

            if not redirect_uri or redirect_uri not in self.ALLOWED_REDIRECT_URIS:
                logger.error("redirect_uri no permitida en GET: %s", redirect_uri)
                return "URI de redirección no autorizada", 403

            return render_template_string('''
                <h2>Autorizar a SmartThings</h2>
                <form method="post">
                    <input type="hidden" name="redirect_uri" value="{{ redirect_uri }}">
                    <input type="hidden" name="state" value="{{ state }}">
                    <input type="hidden" name="client_id" value="{{ client_id }}">
                    <button type="submit" name="approve">Permitir</button>
                </form>
            ''', redirect_uri=redirect_uri, state=state, client_id=client_id), 200
            
        else:  # POST
            if 'approve' in request.form:
                redirect_uri = request.form.get('redirect_uri')
                state = request.form.get('state')
                client_id = request.form.get('client_id')

                if client_id != self.my_client_id:
                    return "Denegado, tu no tienes permiso para entrar.", 401

                if not redirect_uri or redirect_uri not in self.ALLOWED_REDIRECT_URIS:
                    logger.error("redirect_uri no permitida en POST: %s", redirect_uri)
                    return "URI de redirección no autorizada", 403

                code = secrets.token_urlsafe(32)
                final_url = f"{redirect_uri}?code={code}&state={state}"
                return redirect(final_url)

            return "Acceso denegado", 403

    def token(self):
        logger.info("-"*10 + " [Aqui inicia el token] " + "-"*10)
        data = request.form
        logger.info(data)
        logger.info("\n"*2 + " este es el Basic Auth ")
        data1 = request.authorization
        logger.info(data1)
        access_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)
        final_toke = {
            'access_token': access_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'refresh_token': refresh_token
        }
        logger.info("Token generado final: %s", str(final_toke))
        logger.info("-"*50)
        return final_toke
    
    def target_endpoint(self):
        logger.info("-"*10 + " [Aqui inicia target end point] " + "-"*10)
        logger.info("Content-Type: %s", request.content_type)
        data = request.get_json(silent=True)
        if data is None:
            body_text = request.get_data(as_text=True)
            try:
                data = loads(body_text) if body_text else {}
            except JSONDecodeError:
                data = request.form.to_dict()
        if not data:
            logger.error("target_endpoint: no request body received")
            return jsonify({"error": "No data received"}), 400

        request_id = data.get('headers', {}).get('requestId')
        interaction_type = data.get('headers', {}).get('interactionType')
        logger.info("target_endpoint interactionType=%s requestId=%s", interaction_type, request_id)

        if interaction_type == "discoveryRequest":
            respuesta = self.handle_device_discovered(request_id)
        elif interaction_type == "stateRefreshRequest":
            respuesta = self.state_refresh_request(request_id)
        elif interaction_type == "commandRequest":
            respuesta = self.command_request(request_id, data.get("devices") or data.get("commands") or [])
            logger.info("-"*50)
        elif interaction_type == "grantCallbackAccess":
            callback_auth = data.get("callbackAuthentication", {})
            callback_urls = data.get("callbackUrls", {})
            self.code = callback_auth.get("code")
            self.callbackUrlsoauthToken = callback_urls.get("oauthToken") if callback_urls.get("oauthToken") in self.ALLOWED_REDIRECT_URIS else "https://c2c-us.smartthings.com/oauth/token"
            self.callbackUrlsstateCallback = callback_urls.get("stateCallback") if callback_urls.get("oauthToken") in self.ALLOWED_REDIRECT_URIS else "https://c2c-us.smartthings.com/oauth/token"
            if not self.code or not self.callbackUrlsoauthToken or not self.callbackUrlsstateCallback:
                logger.error("grantCallbackAccess missing callbackAuthentication or callbackUrls")
                return jsonify({"error": "Missing callbackAuthentication or callbackUrls"}), 400
            rr, status = self.send_token_request()
            if status == 200:
                datos = [data.get("authentication"), callback_auth, callback_urls, rr.get("callbackAuthentication")]
                self.save_shake(datos)
            else:
                logger.error("grantCallbackAccess accessTokenRequest failed: %s", rr)
            logger.info("-"*50)
            respuesta = rr if isinstance(rr, dict) else {}
        else:
            logger.error("target_endpoint unknown interactionType: %s", interaction_type)
            return jsonify({"error": "Unsupported interactionType"}), 400

        return jsonify(respuesta), 200
    
    def handle_device_discovered(self, request_id):
        result = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "discoveryResponse",
                "requestId": request_id
            },
            "requestGrantCallbackAccess": True,
            "devices": [
                i.to_discovery_dict() for i in self.accessories.values()
            ]
        }
        return result

    def state_refresh_request(self, request_id):
        result = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "stateRefreshResponse",
                "requestId": request_id
            },
            "deviceState": [
                i.state_refresh_request() for i in self.accessories.values()
            ]
        }
        return result

    def command_request(self, request_id, commands=None):
        # TODO: Cambiar toda la funcion, smartthings debe de mandar el lote de comando
        if commands:
            for command in commands:
                device_id = command.get("externalDeviceId")
                accessory = self.accessories.get(device_id)
                if accessory:
                    accessory.handle_smartthings_command(command)
        result = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "commandResponse",
                "requestId": request_id
            },
            "deviceState": [
                i.state_refresh_request() for i in self.accessories.values()
            ]
        }
        return result

    def send_token_request(self):
        if not self.callbackUrlsoauthToken:
            logger.error("send_token_request: oauthToken callback URL is empty")
            return {"error": "Missing oauthToken callback URL"}, 400

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
                "clientId": self.St_Client_Id,
                "clientSecret": self.St_Client_Secret
            }
        }
        logger.info("-"*50 + " Aqui inicia el [accessTokenRequest] " + "-"*50)
        logger.info("accessTokenRequest url=%s payload=%s", self.callbackUrlsoauthToken, message)
        result = send_req(self.callbackUrlsoauthToken, json=message, headers={"Content-Type": "application/json"}, timeout=10)
        try:
            body = result.json()
        except Exception as exc:
            logger.error("send_token_request: invalid JSON response: %s", exc)
            body = {"error": "Invalid JSON response"}
        logger.info("accessTokenResponse=%s status=%s", body, result.status_code)
        logger.info("-"*50)
        return body, result.status_code

    def refresh_token(self):
        message = {
            "headers": {
                "schema": "st-schema",
                "version": "1.0",
                "interactionType": "refreshAccessTokens",
                "requestId": str(uuid4())
            },
            "callbackAuthentication": {
                "grantType": "refresh_token",
                "refreshToken": self.refresh_token_sesion_smartthings,
                "clientId": self.St_Client_Id,
                "clientSecret": self.St_Client_Secret
            }
        }
        result = send_req(self.callbackUrlsoauthToken, json=message, timeout=10)
        logger.info("Refresh token")
        rr = result.json()
        logger.info(rr)
        if result.status_code == 200:
            self.token_from_smartthings = rr.get("callbackAuthentication").get("accessToken")
            self.refresh_token_sesion_smartthings = rr.get("callbackAuthentication").get("refreshToken")
            self.save_new_token(rr.get("callbackAuthentication").get("accessToken"), rr.get("callbackAuthentication").get("refreshToken"), rr.get("callbackAuthentication").get("expiresIn"))
        logger.info("-"*50)
        return rr, result.status_code

    def send_device_status(self, devices_list=None):
        if devices_list is None:
            devices_list = list(self.accessories.values())
            result = None
        try:
            message = {
                "headers": {
                    "schema": "st-schema",
                    "version": "1.0",
                    "interactionType": "stateCallback",
                    "requestId": str(uuid4())
                },
                "authentication": {
                    "tokenType": "Bearer",
                    "token": self.token_from_smartthings
                },
                "deviceState": [
                    i.send_device_status() for i in devices_list
                ]
            }
            print("Este es el mensaje que se va a enviar a SmartThings en send_device_status: " + str(message))
            result = send_req(self.callbackUrlsstateCallback, json=message, timeout=10)
            return {}, result.status_code
        except Exception as e:
            logger.error("Error in send_device_status: %s", e, exc_info=True)
            try:
                self.refresh_token()
            except Exception as e2:
                logger.error("Error refreshing token: %s", e2, exc_info=True)
            return None, 500

    def discovery_callback(self, devices_list=None):
        if devices_list is None:
            devices_list = list(self.accessories.values())
        try:
            message = {
                "headers": {
                    "schema": "st-schema",
                    "version": "1.0",
                    "interactionType": "discoveryCallback",
                    "requestId": str(uuid4())
                },
                "authentication": {
                    "tokenType": "Bearer",
                    "token": self.token_from_smartthings
                },
                "devices": [
                    i.to_discovery_dict() for i in devices_list
                ]
            }
            result = send_req(self.callbackUrlsstateCallback, json=message, timeout=10)
            return {}, result.status_code
        except Exception as e:
            logger.error("Error in discovery_callback: %s", e, exc_info=True)
            try:
                self.refresh_token()
            except Exception as e2:
                logger.error("Error refreshing token: %s", e2, exc_info=True)
            return None, 500
