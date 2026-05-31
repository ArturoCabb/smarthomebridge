from pyhap.accessory import Accessory
from pyhap.const import CATEGORY_OTHER
import requests
from config import TelegramConfig

class LGWasherAccessory(Accessory):
    """Accessory to turn on/off the LG Washer."""
    category = CATEGORY_OTHER

    telegram_trigger = False
    change_state_prev_value = None
    change_remote_start_prev_value = None
    change_remaining_time_prev_value = None

    def __init__(self, driver, display_name, device_id, device_manager):
        super().__init__(driver=driver, display_name=display_name)

        self.device_id = device_id
        self.device_manager = device_manager

        self.is_paused = True
        self.delay = 0

        # --- 1. SERVICIO DE CONTROL PRINCIPAL (Usamos Television para el menú) ---
        # El servicio 'Television' es el que permite tener la lista de selección
        self.serv_main = self.add_preload_service('Television', chars=['ConfiguredName', 'ActiveIdentifier'])
        self.encendido = self.serv_main.configure_char('Active', setter_callback=self.set_power, value=0)
        self.serv_main.configure_char('ConfiguredName', value="LG Controller")
        self.char_active_input = self.serv_main.configure_char('ActiveIdentifier', setter_callback=self.set_delay_time, value=0)

        # --- 2. SWITCH DE INICIAR LAVADO ---
        # Lo añadimos como un servicio vinculado
        self.serv_power = self.add_preload_service('Switch', chars=['Name'])
        self.serv_power.configure_char('Name', value="Iniciar Pausar")
        self.char_on = self.serv_power.configure_char('On', setter_callback=self.set_pause_resume, value=0)
        self.serv_main.add_linked_service(self.serv_power)

        # --- 3. DEFINICIÓN DE TIEMPO DE RETRASO (Input Sources) ---
        self.tiempo_retardo = [i for i in range(0, 20)]  # Tiempo de retardo de 1 a 19 Horas

        for index, time in enumerate(self.tiempo_retardo):
            input_serv = self.add_preload_service('InputSource', chars=['ConfiguredName', 'IsConfigured', 'InputSourceType', 'Identifier', 'Name'])
            input_serv.configure_char('ConfiguredName', value=time)
            input_serv.configure_char('IsConfigured', value=1)
            input_serv.configure_char('InputSourceType', value=10) # 10 = Application / Modo
            input_serv.configure_char('Identifier', value=index) # ID que recibirá el callback
            
            # Vinculamos cada ciclo al servicio principal
            self.serv_main.add_linked_service(input_serv)

        # 5. MOSTRAR EL TIEMPO RESTANTE
        self.serv_timer = self.add_preload_service('HumiditySensor', chars=['Name', 'CurrentRelativeHumidity'])
        self.serv_timer.configure_char('Name', value="Minutos Restantes")
        self.char_timer_value = self.serv_timer.get_characteristic('CurrentRelativeHumidity')
        self.char_timer_value.set_value(0) # Inicia en 0 minutos
        
        # 6. # Creamos un servicio de ocupación (que solo sirve para mostrar texto)
        self.serv_status = self.add_preload_service('OccupancySensor', chars=['Name', 'StatusActive', 'StatusTampered'])
        # Este es el objeto que cambiaremos para "pintar" texto
        self.char_status_ocupancy_detected = self.serv_status.configure_char('OccupancyDetected', value=0)  
        self.serv_status.configure_char('StatusActive', value=True)
        self.char_status_ocupancy_status_tampered = self.serv_status.configure_char('StatusTampered', value=1)
        self.serv_status.configure_char('Name', value="Estado: Enjuagando")

    def set_power(self, value):
        command = {
            'location': {
                'locationName': 'MAIN',
            },
            'operation': {
                'washerOperationMode': 'POWER_OFF'
            }
        }
        self.device_manager.send_command(self.device_id, command)
        self.encendido.set_value(0)

    def set_pause_resume(self, value):
        if self.is_paused:
            command = {
                'location': {
                    'locationName': 'MAIN',
                },
                'operation': {
                    'washerOperationMode': 'START'
                },
                'timer': {
                    'relativeHourToStart': self.delay
                }
            }
            print("LG Washer is turned ON")
            self.device_manager.send_command(self.device_id, command)
            self.char_on.set_value(1)
            self.change_remote_start_prev_value = "PREVENT_ON"
        else:
            command = {
                'location': {
                    'locationName': 'MAIN',
                },
                'operation': {
                    'washerOperationMode': 'STOP'
                }
            }
            print("LG Washer is turned OFF")
            self.device_manager.send_command(self.device_id, command)
            self.char_on.set_value(0)
            

    def set_delay_time(self, value):
        # 'value' será el número (index) que seleccionaste
        tiempo_seleccionado = self.tiempo_retardo[value]
        self.delay = tiempo_seleccionado
        print(f"Cambiando retardo a: {tiempo_seleccionado}")

    def update_from_device_state(self, state):
        """
        Actualizar la interfaz HAP con el estado real del dispositivo.
        
        Args:
            state: WasherState obtenido del plugin
        """
        # Actualizar estado de encendido
        device_state = state.state.get('state')
        if device_state != self.change_state_prev_value:
            if device_state != "POWER_OFF":
                self.encendido.set_value(1)
            else:
                self.encendido.set_value(0)
            # Actualiza notificacion para centrifugado
            if device_state == "RINSING":
                self.char_status_ocupancy_detected.set_value(1)
                self.char_status_ocupancy_status_tampered.set_value(1)
                if self.telegram_trigger is False:
                    requests.get(url=TelegramConfig().telegram_url, json={"chat_id": TelegramConfig().telegram_chatid, "text": "La lavadora termino de lavar y ahora va a enjuagar"}, timeout=10)
                    self.telegram_trigger = True
            else:
                self.char_status_ocupancy_detected.set_value(0)
                self.char_status_ocupancy_status_tampered.set_value(0)
                self.telegram_trigger = False
            self.change_state_prev_value = device_state
        
        if device_state != self.change_remote_start_prev_value:
            # Actualizar estado de boton iniciar/pausar
            if device_state != "POWER_OFF" and device_state != "PAUSE" and state.state.get('remote_start'):
                self. is_paused = False
                if self.char_on.value != 1:
                    self.char_on.set_value(1)
            else:
                self.is_paused = True
                self.char_on.set_value(0)
            self.change_remote_start_prev_value = device_state
            
        # Actualizar tiempo restante
        remain_time = state.state.get('remain_time_m')
        if remain_time != self.change_remaining_time_prev_value:
            self.char_timer_value.set_value(min(remain_time, 100))
            self.change_remaining_time_prev_value = remain_time
