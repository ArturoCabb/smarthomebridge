Para una isntalacion de sistema

Se necesita correr el archivo runme.sh como sudo, este le ayudará a crear las variables de entono necesarias para correr el programa, al igual que inciar el servicio de miscript.service

Para poder utilizar este proyecto corra telegramNoti.py, 
este le ayudará a configurar sus credenciales de LG si es que no tiene el archivo
SMARTHOME/configuration/config.json configurado. De lo contrario asegurese que lo
tenga en el directorio donde corre el script.

En caso de que use un contendor de docker, asegurese de crear un volumen y agregar
el archivo SMARTHOME/configuration/config.json configurando como valor minimo
"x-client-id" que puede generar con la api de LGThinQ
El archivo se debe de ver la siguiente manera
{
    "x-client-id": <Valor generado por api>
}
Las variables de entono son las siguientes
API_KEYLG=<Generada desde la cuenta de LGThinQ>
TELEGRAM_URL=<La url del chat para usar el chatbot de Telegram que despacha las notificaciones>
chat_id=<El id del chat con el que vamos a hablar para recibir notificaciones>

En caso de usar contenedor, asegurece de pasar las variables de entorno al contenedor.

Se puede crear un compose como en el archivo adjunto
