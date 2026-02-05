Para una isntalacion de sistema

Se necesita correr el archivo runme.sh como sudo, este le ayudará a crear las variables de entono necesarias para correr el programa, al igual que inciar el servicio de miscript.service

Para poder utilizar este proyecto corra telegramNoti.py, 
este le ayudará a configurar sus credenciales de LG si es que no tiene el archivo
.smarthome/config.conf configurado. De lo contrario asegurese que lo
tenga en el directorio donde corre el script.

En caso de que use un contendor de docker, asegurese de crear un volumen y agregar
el archivo  configurando como valor minimo
"x-client-id" que puede generar con la api de LGThinQ
El archivo se debe de ver la siguiente manera
[HAPCONFIG]
port = 51827
persist_file_name = ./.smarthome/homekit.json
bridge_name = Mi Raspberry Hub
#listen_address = 0.0.0.0
#address = 192.168.1.1

[LG]
base_url=https://api-aic.lgthinq.com
access_token=
message_id=
client_id=

[TELEGRAM]
base_url = 
chat_id = 



Para el docker compose, puede copiar la siguiente configuracion

services:
  mi-servicio:
    image: arturocabb/testspersonales:controlSmartHome
    network_mode: host
    restart: unless-stopped
    environment:
      - API_KEYLG=${API_KEYLG}
      - TELEGRAM_URL=${TELEGRAM_URL}
      - chat_id=${chat_id}
    env_file:
      - .env
    volumes:
      - ~/public/SMARTHOME:/app/.smarthome
    ports:
      - 51827:51827
