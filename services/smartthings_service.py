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
import configparser
import os
import logging
from typing import Dict, List
from config import config

logger = logging.getLogger(__name__)

class SmartThingsService:
    """Servicio SmartThings"""
    config_parser = configparser.ConfigParser()
    config_parser.read(config.CONFIG_FILE)
    
    def __init__(self):
        self.app = Flask(__name__)
        self.accessories: Dict[str, object] = {}  # device_id -> accessory
        self.code = ""
        self.callbackUrlsoauthToken = ""
        self.callbackUrlsstateCallback = ""
        self.token_from_smartthings = ""
        self.refresh_token_sesion_smartthings = ""
        self.my_client_id = self.config_parser.get("SMARTTHINGS", "my_client_id")
        self.my_client_secret = self.config_parser.get("SMARTTHINGS", "my_client_secret")
        self.Endpoint_App_Id = self.config_parser.get("SMARTTHINGS", "Endpoint_App_Id")
        self.St_Client_Id = self.config_parser.get("SMARTTHINGS", "St_Client_Id")
        self.St_Client_Secret = self.config_parser.get("SMARTTHINGS", "St_Client_Secret")
        self.host = self.config_parser.get("SMARTTHINGS", "host")
        self.port = self.config_parser.getint("SMARTTHINGS", "port")
        self.credentials_file = self.config_parser.get('SMARTTHINGS', 'credentials_file')
        self.devies_config_file = self.config_parser.get('SMARTTHINGS', 'devies_conmfig_file', fallback="./.smarthome/smartthingsDevices.json")

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
                logger.error(f"Error in discovery_callback: {e}")
                try:
                    self.refresh_token()
                except Exception as e2:
                    logger.error(f"Error refreshing token: {e2}")

    def health_check(self):
        """Health check endpoint para nginx y monitoreo"""
        return jsonify({
            "status": "ok",
            "service": "SmartThings",
            "accessories": len(self.accessories)
        }), 200

    def add_accessory(self, device_id: str, accessory):
        if device_id in self.accessories:
            logger.warning(f"Accesorio ya existe en smartthings service: {device_id}")
            return False
        
        self.accessories[device_id] = accessory
        logger.info(f"Accesorio agregado a smartthings service: {accessory.external_device_id}")
        return True

    def save_shake(self, data):
        with open(self.credentials_file, "w+") as file:
            file.write(dumps(data, indent=2))

    def save_new_token(self, access_token, refresh_token, expieres):
        try:
            with open(self.credentials_file, "r") as file:
                d = loads(file.read())
                d[3]["accessToken"] = access_token
                d[3]["refreshToken"] = refresh_token
                d[3]["expiresIn"] = expieres
                with open(self.credentials_file, "w+") as file:
                    file.write(dumps(d, indent=2))
        except (FileNotFoundError, JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"Error saving new token: {e}")

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
            logger.error(f"Error reading config file: {e}")
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
            logger.info(f"--- [GET /oauth/login] ---")
            logger.info(f"SmartThings pide redirigir a: {redirect_uri}")
            logger.info(f"State: {state}")
            logger.info(f"Client ID: {client_id}")
            if client_id != self.my_client_id:
                return "Denegado, tu no tienes permiso para entrar.", 401
            
            if not redirect_uri:
                logger.warning("¡OJO! redirect_uri vino vacío. Forzando servidor de US...")
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
                code = secrets.token_urlsafe(32)
                
                final_url = f"{redirect_uri}?code={code}&state={state}"
                logger.info("-"*50)
                
                return redirect(final_url), 200
            else:
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
        logger.info("Token generado final: " + str(final_toke))
        logger.info("-"*50)
        return final_toke
    
    def target_endpoint(self):
        logger.info("-"*10 + " [Aqui inicia target end point] " + "-"*10)
        respuesta = {}
        data: dict = request.get_json() if request.is_json else request.form.to_dict()
        if not data:
            return {'error': 'No data received'}, 400
        
        request_id = data.get('headers', {}).get('requestId')
        operatin_type: str = data.get('headers', {}).get('interactionType')
        if operatin_type == "discoveryRequest":
            respuesta = self.handle_device_discovered(request_id)
        elif operatin_type == "stateRefreshRequest":
            respuesta = self.state_refresh_request(request_id)
        elif operatin_type == "commandRequest":
            logger.info("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
            logger.info("data recibida del server de autorization " + str(request.authorization))
            logger.info("data recibida del server " + str(data))
            respuesta = self.command_request(request_id, data.get("commands"))
            logger.info("-"*50)
        elif operatin_type == "grantCallbackAccess":
            logger.info("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
            logger.info("data recibida del server " + str(data))
            self.code = data.get("callbackAuthentication").get("code")
            self.callbackUrlsoauthToken = data.get("callbackUrls").get("oauthToken")
            self.callbackUrlsstateCallback = data.get("callbackUrls").get("stateCallback")
            rr, status = self.send_token_request()
            if status == 200:
                datos = [data.get("authentication"), data.get("callbackAuthentication"), data.get("callbackUrls"), rr.get("callbackAuthentication")]
                self.save_shake(datos)
            logger.info("-"*50)
        return respuesta, 200
    
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
        logger.info("-"*50 + " Aqui inicia el [accesTokenRequest] " + "-"*50)
        result = send_req(self.callbackUrlsoauthToken, json=message)
        logger.info(result.json())
        logger.info("-"*50)
        return result.json(), result.status_code

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
        result = send_req(self.callbackUrlsoauthToken, json=message)
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
            result = send_req(self.callbackUrlsstateCallback, json=message)
            return {}, result.status_code
        except Exception as e:
            logger.error(f"Error in send_device_status: {e}")
            try:
                self.refresh_token()
            except Exception as e2:
                logger.error(f"Error refreshing token: {e2}")
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
            result = send_req(self.callbackUrlsstateCallback, json=message)
            return {}, result.status_code
        except Exception as e:
            logger.error(f"Error in discovery_callback: {e}")
            try:
                self.refresh_token()
            except Exception as e2:
                logger.error(f"Error refreshing token: {e2}")
            return None, 500
