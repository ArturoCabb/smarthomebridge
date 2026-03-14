## El orquestador App Manager

El Archivo app_manager es el que crea las instancias del programa, levanta los servicios de bridge como HomeKit y smartthings, también es el encargado de hacer el llamado a la identificación de dispositivos en base a los plugins instalados y dispositivos definidos por este.

Su propósito es orquestar el descubrimiento de dispositivos, sincronización y levantar dos servicios en hilos separados: HomeKit (HAP) y SmartThings (HTTP/OAuth).

## ¿Cómo funiona el levantamiento de servicios?
Primero debes de crear un servicio que se definirá en el la carpeta services la cual deberá implementar la interfaz correspondiente. (Puede pasar a la carpeta de services para saber como crear un servicio) y tu bridge (en la carpeta de bridges puedes encontrar información de como se crea un bridge)

1. Primero tienes que crear una funcion para tu servicio, el cual deberá traer la funcion de inicialización del servicio `self.mi_servicio.initialize()` que es la que levanta el conector del servicio, ya sea un socket un servidor web o un driver para la comunicación con la plataforma que estes usando. Ejemplo: Google Home, Smartthings Cloud to Cloud o Apple Home

2. Deberás crear tu bridge que es el que consumirá tu servicio y creará las instancias de los dispositivos que tengas conectados para ser enviados al servicio, así como el manejo de las actualizaciones cuando el dispositivo cambia de estado. `mi_bridge =  MiBridge(self.device_manager, self.mi_servicio)`

3. Luego, la lista de dispositivos que App Manager enlista los podrás enviar a tu bridge para que haga la suscripción (creacion de instancia del dispositivo) para ser reconocido por tu servicio.
```python
for device_state in self.device_manager.get_all_devices():
                self.smartthings_bridge.add_device(device_state)
```

4. Toca iniciar el servicio con `self.smartthings_service.start()`

Una vez definida la función solo bastará copn crear el hilo correspondiente a tu funcion y iniciarlo dentro de la función `start()`. Por defecto start inicia la actualización de los dispositivos en un intervalo de 10 segundos