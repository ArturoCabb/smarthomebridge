NOTA: Bienvenido a mi proyecto y gracias por visitarlo.

Este proyecto es un software DIY el cual busca que cualquier persona interesada en el desarrollo de seoftware y automatizacion de dispositivos IoT
pueda conectar sus dispositivos a la aplicación de Apple Home y Samsung SmartThings o en general a la de su preferencia.

Este código está pensado como una base para que cualquiera pueda montar su propio bridge, expandiendolo a traves de desarrollo de plugins y compartiendo sus aportaciones para que puedan crear su propio Bridge entre sus dispositivos IoT y las aplicaciones de sus plataforma preferidas, disminuyendo la necesidad de instalar más aplicaciones en sus celulares. Cualquier contribución de su parte será bien recibida

## Requisitos para la instalación:

1. Se recomienda tener instalada una versión superior a python 11.
2. Tener acceso al router o módem de tu hogar para configurar la IP estática.
3. En caso de utilizar un contenedor, tener docker instalado
4. En el caso de la versión para Apple sólo bastará con que la máquina donde estes instalando el bridge este es la misma lan en la que está tu teléfono o dispositivo.
5. En el caso de usar Samsung SmartThings, se necesita una IP pública, un nombre de dominio y unos certificados Para la conexión https.
6. La guía también incluye una configuración de Nginx para hacer la conexión con smartthings

## Proceso de instalación
1. Crea una carpeta para tu smartbridge con: mkdir nombre_de_mi_carpeta
1. Clona el repositorio con: `git clone <repo name>`
2. Crear un entorno virtual de pyhton y instalar requeriments.txt con: pip install requeriments.txt

## Creacion de archivo de configuración inicial
1. En la carpeta donde vayas a ejecutar el bridge crea una carpte llamada .smarthome con el comando: mkdir .smarthome
2. Dentro de la carpeta crear el archivo config.conf con el siguiente comando: vi config.conf
    
    El contenido del archivo sería:

    [HAPCONFIG]
    port = 51827
    persist_file_name = ./.smarthome/homekit.json

    bridge_name = Mi Raspberry Hub

    #listen_address = 0.0.0.0

    #address = 192.168.1.#

    [SMARTTHINGS]
    my_client_id = client id generado por la consola de smartthings

    my_client_secret = client secret generado por la consola de smartthings

    Endpoint_App_Id = app id generado por la consola de smartthings

    St_Client_Id = st client id generado por la consola de smartthings

    St_Client_Secret = client secret generado por la consola de smartthings

    host = 0.0.0.0

    port = 5001

    credentials_file = ./.smarthome/smartthingsSettings.json

    devies_conmfig_file = ./.smarthome/smartthings_device_conf.json

El smartthings_device_conf.json se genera llenando la información del perfil del dispositivo. Para más información sobre como generar los archivos y configuraciones de smartthings puedes consultar mi guía en Patreon.

Una vez creados los archivos de configuración puedes ejecutar el programa con python main.py

Nota: En caso de no llenar la configuración de un servicio el programa va a arrogar mensajes de error pero eso no evitará que se interrumpa su ejecución. En caso de uno utilizar un servicio se puede eliminar los archivos de ese servicio y eliminar la función que lo invoca.

En el caso de que no use un plugin, puede eliminar el script relacionado con el plugin y los modelos de los dispositivos asociados.

## Para docker
1. Crea una carpeeta para tu proyecto con: mkdir nombre_de_mi_carpeta
2. Descarga o copia el archivo compose.yaml
3. Edita el archivo compose para definir la ubicación de tu volumen
    volumes:
     - mi_folder:/app/.smarthome
4. Los archivos de configuracion son los mismo de la guía de cracion de archivos de configuración inicial
5. Ejecuta el archivo con docker con el comando: docker compose -f ~/public/compose.yaml up

En caso de querer saber como realizar la configuración de smartthings favor de revisar la publicación de Patreon: <liga patreon>

Para quien decida ayudar a contribuir en el proyecto favor de pasar a leer la documentación dentro de la carpeta core. <link carpeta>