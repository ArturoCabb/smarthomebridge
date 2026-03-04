from flask import Flask, request, render_template_string, redirect, jsonify
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import grants
import secrets
from requests import post as send_req
from json import dumps, loads
from uuid import uuid4
import configparser
import os

app = Flask(__name__)
file_configuration_server = "smrtthingsSettings.json" # Este es la variable de la ruta de configuracion que si se mete el codigo de este archivo en una clase, esta variable se debe poder asignar valor
port = 5001 # Este es el puerto del servidor web que si se mete el codigo de este archivo en una clase, esta variable se debe poder asignar valor
# Almacén simple de códigos (en producción usa BD)
read_config = configparser.ConfigParser()
read_config.read("config.conf")
my_client_id = read_config.get("SMARTTHINGS", "my_client_id")
my_client_secret = read_config.get("SMARTTHINGS", "my_client_secret")
Endpoint_App_Id = read_config.get("SMARTTHINGS", "Endpoint_App_Id")
St_Client_Id = read_config.get("SMARTTHINGS", "St_Client_Id")
St_Client_Secret = read_config.get("SMARTTHINGS", "St_Client_Secret")
code = ""
callbackUrlsoauthToken = ""
callbackUrlsstateCallback = ""
token_from_smartthings = ""
refresh_token_sesion_smartthings = ""

def save_shake(data, file_name = "smrtthingsSettings.json"):
    with open(file_name, "w+") as file:
        file.write(dumps(data, indent=2))

def read_conf_file(file_name = "smrtthingsSettings.json"):
    global code
    global callbackUrlsoauthToken
    global callbackUrlsstateCallback
    global token_from_smartthings
    global refresh_token_sesion_smartthings
    with open(file_name, "r") as file:
        d = loads(file.read())
        code = d[1].get("callbackAuthentication").get("code")
        callbackUrlsoauthToken = d[2].get("callbackUrls").get("oauthToken")
        callbackUrlsstateCallback = d[2].get("callbackUrls").get("stateCallback")
        token_from_smartthings = d[3].get("callbackAuthentication").get("accessToken")
        refresh_token_sesion_smartthings = d[3].get("callbackAuthentication").get("refreshToken")

# --- Flujo de Autorización ---
@app.route('/oauth/login', methods=['GET', 'POST'])
def authorize():
    if request.method == 'GET':
        client_id = request.args.get('client_id')
        redirect_uri = request.args.get('redirect_uri')
        state = request.args.get('state')

        print(f"--- [GET /oauth/login] ---")
        print(f"SmartThings pide redirigir a: {redirect_uri}")
        print(f"State: {state}")
        print(f"Client ID: {client_id}")

        if client_id != my_client_id:
            return "Denegado, tu no tienes permiso para entrar.", 401
        
        # Si Nginx se comió la URL, forzamos la de US para que no falle
        if not redirect_uri:
            print("¡OJO! redirect_uri vino vacío. Forzando servidor de US...")
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
            print("-"*50)
            
            # Redirigimos
            return redirect(final_url), 200
        else:
            return "Acceso denegado", 403

# --- Endpoint de Token ---
@app.route('/oauth/token', methods=['POST'])
def token():
    print("-"*10 + " [Aqui inicia el token] " + "-"*10)
    data = request.form
    print(data)
    print("\n"*2 + " este es el Basic Auth ")
    data1 = request.authorization
    print(data1)
    # Genera tokens (en producción usa JWT o tokens persistentes)
    access_token = secrets.token_urlsafe(32)
    token_sesion = access_token
    refresh_token = secrets.token_urlsafe(32)
    refresh_token_sesion = refresh_token
    final_toke = {
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'refresh_token': refresh_token
    }
    print("Token generado final: " + str(final_toke))
    print("-"*50)
    return final_toke

@app.route('/target-endpoint', methods=['GET', 'POST'])
def target_endpoint():
    print("-"*10 + " [Aqui inicia target end point] " + "-"*10)
    respuesta = {}
    data: dict = request.get_json() if request.is_json else request.form.to_dict()
    if not data:
        return {'error': 'No data received'}, 400
    
    request_id = data.get('headers', {}).get('requestId')
    operatin_type: str = data.get('headers', {}).get('interactionType')
    if operatin_type == "discoveryRequest":
        respuesta = handle_device_discovered(request_id)
    elif operatin_type == "stateRefreshRequest":
        devicess = data.get("devices")
        respuesta = state_refresh_request(request_id, devicess)
    elif operatin_type == "commandRequest":
        # TODO: Aqui hay que validar el token
        print("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
        print("data recibida del server de autorization " + str(request.authorization))
        print("data recibida del server " + str(data))
        respuesta = command_request(request_id)
        print("-"*50)
    elif operatin_type == "grantCallbackAccess":
        global code
        global callbackUrlsoauthToken
        global callbackUrlsstateCallback
        print("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
        print("data recibida del server " + str(data))
        code = data.get("callbackAuthentication").get("code")
        callbackUrlsoauthToken = data.get("callbackUrls").get("oauthToken")
        callbackUrlsstateCallback = data.get("callbackUrls").get("stateCallback")
        rr = send_token_request()
        datos = [data.get("authentication"), data.get("callbackAuthentication"), data.get("callbackUrls"), rr.get("callbackAuthentication")]
        save_shake(datos)
        print("-"*50)
    return respuesta, 200

def handle_device_discovered(request_id, devices_list: list):
    result = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "discoveryResponse",
            "requestId": request_id
        },
        "requestGrantCallbackAccess": True,
        "devices": [
            i.to_discovery_dict() for i in devices_list
        ]
    }
    return result

def state_refresh_request(request_id, devices_list: list):
    result = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "stateRefreshResponse",
            "requestId": request_id
        },
        "deviceState": [
            i.state_refresh_request() for i in devices_list
        ]
    }
    return result

def command_request(request_id, devices_list: list):
    # Este regresa el estado del dispositivo
    result = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "commandResponse",
            "requestId": request_id
        },
        "deviceState": [
            i.to_command_request() for i in devices_list
        ]
    }
    return result

def send_token_request():
    global code
    global callbackUrlsoauthToken
    global token_from_smartthings
    global refresh_token_sesion_smartthings
    message = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "accessTokenRequest",
            "requestId": str(uuid4())
        },
        "callbackAuthentication": {
            "grantType": "authorization_code",
            "code":code,
            "clientId": St_Client_Id,
            "clientSecret": St_Client_Secret
        }
    }
    print("-"*50 + " Aqui inicia el [accesTokenRequest] " + "-"*50)
    result = send_req(callbackUrlsoauthToken, data=dumps(message))
    print(result.json())
    print("-"*50)
    return result.json(), result.status_code

def refresh_token():
    global callbackUrlsoauthToken
    global refresh_token_sesion_smartthings
    message = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "refreshAccessTokens",
            "requestId": str(uuid4())
        },
        "callbackAuthentication": {
            "grantType": "refresh_token",
            "refreshToken": refresh_token_sesion_smartthings,
            "clientId": St_Client_Id,
            "clientSecret": St_Client_Secret
        }
    }
    result = send_req(callbackUrlsoauthToken, data=dumps(message))
    print("Refresh token")
    print(result.json())
    print("-"*50)
    return result.json(), result.status_code

def send_device_status(devices_list: list):
    message = {
    "headers": {
        "schema": "st-schema",
        "version": "1.0",
        "interactionType": "stateCallback",
        "requestId": str(uuid4())
    },
    "authentication": {
        "tokenType": "Bearer",
        "token": token_from_smartthings
    },
    "deviceState": [
        i.send_device_status() for i in devices_list
    ]
}
    result = send_req(callbackUrlsstateCallback, data=message)
    return result.json(), result.status_code 

def discovery_callback(devices_list: list):
    message = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "discoveryCallback",
            "requestId": str(uuid4())
        },
        "authentication": {
            "tokenType": "Bearer",
            "token": token_from_smartthings
        },
        "devices": [
            i.to_discovery_dict() for i in devices_list
        ]
    }
    result = send_req("una_url", data=dumps(message))
    return result.json(), result.status_code


if __name__ == '__main__':
    if os.path.exists(file_configuration_server):
        read_conf_file(file_configuration_server)
    app.run(host='0.0.0.0', port=port)  # Puerto diferente a tu bridge