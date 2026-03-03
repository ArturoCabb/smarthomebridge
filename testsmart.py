from flask import Flask, request, render_template_string, redirect, jsonify
from authlib.integrations.flask_client import OAuth
from authlib.oauth2.rfc6749 import grants
import secrets
from requests import post as send_req
from json import dumps

app = Flask(__name__)

# Almacén simple de códigos (en producción usa BD)
url = "https://c2c-us.smartthings.com/oauth/callback"
client_id = "arturocabb"
client_secret = "arturocasahouseiot"
scopes = ""
authorization_codes = {}
token_sesion = ""
refresh_token_sesion = ""
Endpoint_App_Id = "viper_a344df40-14d7-11f1-8d45-1b8707fbd01e"
St_Client_Id = "e9b12e22-5528-4a51-9e43-13a83e00ba58"
St_Client_Secret = "3ad66aeea9df843f165eb85ed9f6adc6afc7e29a1c828fbf163f9201f8c25c581acce9b1e10c6af008b9769a7316b555bf85811532da42b6bb44a27936ec86b4b2758a955a7c2e4d641470b4355e298beec051425e56e65856ca0156706137fed57e12c56cab903c2f2863b9ad8dbb672929f53da0b4f6bc90c079af411c0e0d12e5f4e71fccc9dcad4a3dd7656db7330e1f77eb29fd1d4640bb147bb07df7d4715db1b28105028cb10b478894012ec432455a61481309c02716a85c74958ef6ee8825c390739a166ac19259a9fe2f30301d43f19ad723b33feef49752ba6912d8b83e6497f66d862be89269fb9349f6d50030f913762d227ef06f6560f27360"

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
            authorization_codes[code] = {
                'client_id': client_id,
                'user_id': 'usuario_prueba'
            }
            
            final_url = f"{redirect_uri}?code={code}&state={state}"
            print(f"--- [POST /oauth/login] ---")
            print(f"Redirigiendo finalmente a: {final_url}")
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

    code = data.get('code')
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')
    
    # Valida credenciales y código
    #if client_id != St_Client_Id or client_secret != St_Client_Secret:
    #    return {'error': 'invalid_client'}, 401
    
    #if code not in authorization_codes:
    #    return {'error': 'invalid_grant'}, 400
    
    # Elimina el código usado (one-time use)
    #del authorization_codes[code]
    
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
    respuesta = {}
    data: dict = request.get_json() if request.is_json else request.form.to_dict()
    if not data:
        return {'error': 'No data received'}, 400
    
    request_id = data.get('headers', {}).get('requestId')
    operatin_type: str = data.get('headers', {}).get('interactionType')
    if operatin_type == "discoveryRequest":
        print("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
        print("data recibida del server " + str(data))
        print("-"*50)
        respuesta = handle_device_discovered(request_id)
    elif operatin_type == "stateRefreshRequest":
        print("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
        print("data recibida del server " + str(data))
        print("-"*50)
        respuesta = state_refresh_request(request_id)
    elif operatin_type == "commandRequest":
        # TODO: Aqui hay que validar el token
        print("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
        print("data recibida del server " + str(data))
        print("-"*50)
        respuesta = command_request(request_id)
    elif operatin_type == "grantCallbackAccess":
        print("-"*10 + f" Respuesta recibida para {operatin_type} " + "-"*10)
        print("data recibida del server " + str(data))
        print("-"*50)
    return respuesta, 200

def handle_device_discovered(request_id):
    result = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "discoveryResponse",
            "requestId": request_id
        },
        "requestGrantCallbackAccess": True,
        "devices": [
            {
            "externalDeviceId": "Tedst no wifi",
            "deviceCookie": {"updatedcookie": "old or new value"},
            "friendlyName": "Kitchen Bulb",
            "manufacturerInfo": {
                "manufacturerName": "LIFX",
                "modelName": "A19 Color Bulb",
                "hwVersion": "v1 US bulb",
                "swVersion": "23.123.231"
            },
            "deviceContext" : {
                "roomName": "Kitchen",
                "groups": ["Kitchen Lights", "House Bulbs"],
                "categories": ["light", "switch"]
            },
            "deviceHandlerType": "c2c-rgbw-color-bulb",
            "deviceUniqueId": "Tedst no wifi"
            },
        ]
    }
    return result

def state_refresh_request(request_id):
    result = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "stateRefreshResponse",
            "requestId": request_id
        },
        "deviceState": [
            {
                "externalDeviceId": "Tedst no wifi",
                "deviceCookie": {},
                "states": [
                    {
                        "component": "main",
                        "capability": "st.healthCheck",
                        "attribute": "healthStatus",
                        "value": "online"
                    },
                    {
                        "component": "main",
                        "capability": "st.switch",
                        "attribute": "switch",
                        "value": "on"
                    },
                    {
                        "component": "main",
                        "capability": "st.switchLevel",
                        "attribute": "level",
                        "value": 80
                    },
                    {
                        "component": "main",
                        "capability": "st.colorControl",
                        "attribute": "hue",
                        "value": 0
                    },
                    {
                        "component": "main",
                        "capability": "st.colorControl",
                        "attribute": "saturation",
                        "value": 0          
                    },
                    {
                        "component": "main",
                        "capability": "st.colorTemperature",
                        "attribute": "colorTemperature",
                        "value": 3500
                    }        
                ]
            }
        ]
    }
    return result

def command_request(request_id):
    result = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "commandResponse",
            "requestId": request_id
        },
        "deviceState": [
            {
                "externalDeviceId": "Tedst no wifi",
                "deviceCookie": {},
                "states": [
                    {
                        "component": "main",
                        "capability": "st.colorControl",
                        "attribute": "hue",
                        "value": 0.8333333333333334
                    },
                    {
                        "component": "main",
                        "capability": "st.switch",
                        "attribute": "switch",
                        "value": "off"
                    },
                    {
                        "component": "main",
                        "capability": "st.switchLevel",
                        "attribute": "level",
                        "value": 80
                    }
                ]
            }
        ]
    }
    return result

@app.route('/send-token-request', methods=['GET'])
def send_token_request():
    request_id = request.get_json().get("request_id")
    code = request.get_json().get("code")
    message = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "accessTokenRequest",
            "requestId": request_id
        },
        "callbackAuthentication": {
            "grantType": "authorization_code",
            "code": code,
            "clientId": St_Client_Id,
            "clientSecret": St_Client_Secret
        }
    }
    result = send_req("una_url", data=dumps(message)).json()
    return result, 200

@app.route('/refresh-token', methods=['GET'])
def refresh_token():
    request_id = request.get_json().get("request_id")
    refresh_token = request.get_json().get("refresh_token")
    message = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "refreshAccessTokens",
            "requestId": request_id
        },
        "callbackAuthentication": {
            "grantType": "refresh_token",
            "refreshToken": refresh_token,
            "clientId": St_Client_Id,
            "clientSecret": St_Client_Secret
        }
    }
    result = send_req("una_url", data=dumps(message)).json()
    return result, 200

@app.route('/send-device-status', methods=['GET'])
def send_device_status():
    request_id = request.get_json().get("request_id")
    token = request.get_json().get("token")
    temp_dev_id = "Tedst no wifi"
    result = {
    "headers": {
        "schema": "st-schema",
        "version": "1.0",
        "interactionType": "stateCallback",
        "requestId": request_id
    },
    "authentication": {
        "tokenType": "Bearer",
        "token": token
    },
    "deviceState": [
        {
            "externalDeviceId": "Tedst no wifi",
            "states": [
                {
                    "component": "main",
                    "capability": "st.button",
                    "attribute": "button",
                    "value": "pushed",
                    "timestamp": 1568248946010,
                    "stateChange": "Y"
                }
            ]
        },
    ]
}
    result = send_req(f"https://api.smartthings.com/v1/devices/{temp_dev_id}").json()
    return result, 200

@app.route('/discovery-callback', methods=['GET'])
def discovery_callback():
    request_id = request.get_json().get("request_id")
    token = request.get_json().get("token")
    message = {
        "headers": {
            "schema": "st-schema",
            "version": "1.0",
            "interactionType": "discoveryCallback",
            "requestId": request_id
        },
        "authentication": {
            "tokenType": "Bearer",
            "token": token
        },
        "devices": [
            {
            "externalDeviceId": "Tedst no wifi",
            "deviceCookie": {"updatedcookie": "old or new value"},
            "friendlyName": "Kitchen Bulb",
            "manufacturerInfo": {
                "manufacturerName": "LIFX",
                "modelName": "A19 Color Bulb",
                "hwVersion": "v1 US bulb",
                "swVersion": "23.123.231"
            },
            "deviceContext" : {
                "roomName": "Kitchen",
                "groups": ["Kitchen Lights", "House Bulbs"]
            },
            "deviceHandlerType": "c2c-rgbw-color-bulb"
        },
        {
            "externalDeviceId": "partner-device-id-2",
            "deviceCookie": {"updatedcookie": "old or new value"},
            "friendlyName": "Toaster",
            "manufacturerInfo": {
                "manufacturerName": "LIFX",
                "modelName": "Outlet",
                "hwVersion": "v1 US outlet",
                "swVersion": "3.03.11"
            },
            "deviceContext" : {
                "roomName": "Living Room",
                "groups": ["Hall Lights"]
            },
            "deviceHandlerType": "<DEVICE-PROFILE-ID>"
            }
        ]
        }
    result = send_req("una_url", data=dumps(message)).json()
    return result, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # Puerto diferente a tu bridge