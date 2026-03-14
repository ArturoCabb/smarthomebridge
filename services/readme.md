## Creacion de servicio
En esta seccion se describe como crear un servicio que es el que generara la conexion para consumir el servicio del proveedor seleccionado

1. En el script que crees de tu servicio es donde leeras las variables de configuracion que definas en el archivo de config.conf el cual se puede llamar impoortando config `
conf_parser = configparser.ConfigParser()
conf_parser.read(config.CONFIG_FILE)`

2. `initialize()` Es la funcion donde creas tu driver, aquí debes crear tu conector en caso de ser requerido, de lo contrario lo puedes usar para importar la configuración de tu servicio.

3. `add_accessory()` Es la funcion que recibirá cada uno de tus dispositivos y creará la lista de instancias correspondientes a cada uno de ellos. Por ejemplo: asignar el dispositivo a la instancia de una lavadora o aspiradora. Esta funcion sabe como como se debe de formar el dispositivo que enviaras a la plataforma que estas desarrollando.

4. `start()` Simplemente inicia el servicio, puede ser tu socket o tu servidor web de flask

5. `stop()` Detiene el servicio, puede ser tu socket o tu servidor web de flask