import board
from adafruit_lis3dh import LIS3DH_I2C
import adafruit_lis3dh
from adafruit_io.adafruit_io import IO_MQTT, IO_HTTP
import pwmio
import time
import math
import os
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Pour affichage
from adafruit_display_text.label import Label
from displayio import I2CDisplay as BusEcran
from displayio import Group
import displayio
from adafruit_displayio_ssd1306 import SSD1306 as Ecran
import terminalio

# import aide_examen
# Fonctions disponibles pour l'aide à l'examen
# def connection_serveur_mqtt(self,code_etudiant: str) -> IO_MQTT
# def connection_serveur_http(self,code_etudiant: str) -> IO_HTTP
# def conversion_roulis(self,x: float, y: float, z: float) -> float
# def conversion_tangage(self,x: float, y: float, z: float) -> float
# def recuperation_accelerations(self) -> tuple[float, float, float]
# def envoi_donnees(self,roll: float, pitch: float) -> None
# def recuperation_date_heure(self) -> struct_time

class Navigation():

    def __init__(self):
        self.LIS3DH = LIS3DH_I2C(board.I2C(), address=0x19)
        self.LIS3DH.range = adafruit_lis3dh.RANGE_2_G
        self.init_ecran()
        self.buzzer = pwmio.PWMOut(board.IO10, variable_frequency=True, duty_cycle=2 ** 15)
        
        self.aio = self.connection_aio()

        self.min_acq_accel = time.monotonic_ns()
        self.min_envoi_donnees_aio = time.monotonic_ns()
        self.min_maj_ecran = time.monotonic_ns()
        
        self.temps_acquisition_acceleration = 1_000_000_000 # 1 seconde
        self.temps_envoi_donnees_aio = 10_000_000_000 # 5 secondes
        self.temps_maj_ecran = 1_000_000_000 # 1 seconde

        self.priorite = 0
        self.TONE = [500,300]

    def init_ecran(self) -> None:
        displayio.release_displays()
        self._bus_ecran = BusEcran(board.I2C(), device_address=0x3C)
        self._ecran = Ecran(self._bus_ecran, width=128, height=64, rotation=180)
        self._splash = Group()
        self._ecran.root_group = self._splash
        self._zone_texte = Label(terminalio.FONT, text="", color=0xFFFFFF, x=5, y=10)
        self._splash.append(self._zone_texte)
    
    def init_sd(self) -> None:
        pass # À remplir

    def connection_aio(self) -> IO_HTTP|IO_MQTT: # À remplir
       pass
            
        #secrets = {
            #"aio_username": "julienbosco",
            #"aio_key": "Ta clé",  #J'ai pas eu le temp de te la demander
            #"ssid": os.getenv("CIRCUITPY_WIFI_SSID"),
            #"password": os.getenv("CIRCUITPY_WIFI_PASSWORD"),
        #}
            

       # pool = socketpool.SocketPool(wifi.radio)
       # mqtt = MQTT.MQTT(socket_pool=pool,
                        #username=secrets["aio_username"],
                       # password=secrets["aio_key"],
                       # ssl_context=ssl.create_default_context(),
                       # broker="io.adafruit.com",
                        #is_ssl=True,
                        #port=8883)
        
        #io = IO_MQTT(mqtt)
        #io.connect()
        
        #io.subscribe('examen-final.202208852')

        #return io
        

        


    def maj_acceleration(self) -> None:
        self.x, self.y, self.z = self.LIS3DH.acceleration

    def maj_ecran(self, texte: str) -> None:
        self._zone_texte.text = texte
        self._ecran.refresh()

    def envoi_donnees_aio(self) -> None: 
        #self.aio.publish('examen-final.202208852', {
        #    "roll":self.roulis(),
        #    "pitch":self.tangage()
        #})
        pass

    def acceleration(self) -> tuple:
        return self.LIS3DH.acceleration
    
    def roulis(self) -> float:
        return (math.atan2(self.y,self.z))*57.3
    def tangage(self) -> float:
        return (math.atan2(-self.x, math.sqrt((self.y)*2 + (self.z)*2)))*57.3
    
    def maj_avertissement(self) -> None:
       
        if self.tangage() < -20 or self.tangage() > 20:
            if self.tangage() < -35 or self.tangage() > 35:
                self.priorite = 1
            else:
                self.priorite = 2  
        elif self.roulis() < -15 or self.roulis() > 15:
            if self.roulis() < -30 or self.roulis() > 30:
                self.priorite = 3
            else:
                self.priorite = 4
        else:
            self.priorite = 5
            
            
    
    def maj_buzzer(self) -> None:
        if self.tangage() < -20 or self.tangage() > 20:
            self.buzzer.duty_cycle = 2 ** 15
            if self.tangage() < -35 or self.tangage() > 35:
                self.buzzer.frequency = self.TONE[0]
            else:
                self.buzzer.frequency = self.TONE[1]
        elif self.roulis() < -15 or self.roulis() > 15:
            self.buzzer.duty_cycle = 2 ** 15
            if self.roulis() < -30 or self.roulis() > 30:
                self.buzzer.frequency = self.TONE[0]
            else:
                self.buzzer.frequency = self.TONE[1]
        else:
            self.buzzer.duty_cycle = 0

    def ecrire_sd(self, data: str) -> None:
        # Écriture sur la carte SD
        pass
    
    def boucle(self) -> None:
        if time.monotonic_ns() - self.min_acq_accel > self.temps_acquisition_acceleration:
            self.min_acq_accel = time.monotonic_ns()
            self.maj_acceleration()
            self.maj_avertissement()
            self.maj_buzzer()
            

        if time.monotonic_ns() - self.min_envoi_donnees_aio > self.temps_envoi_donnees_aio:
            self.envoi_donnees_aio()
            self.min_envoi_donnees_aio = time.monotonic_ns()
        
        if time.monotonic_ns() - self.min_maj_ecran > self.temps_maj_ecran:
            if self.priorite != 5:
                if self.priorite == 1:
                    self.maj_ecran("Pitch CRITIQUE")
                elif self.priorite == 2:
                    self.maj_ecran("Pitch DANGER")
                
                if self.priorite == 3:
                    self.maj_ecran("\nRoll CRITIQUE")
                elif self.priorite == 4:
                    self.maj_ecran("\nRoll DANGER")
            else:
                self.maj_ecran("")

            self.min_maj_ecran = time.monotonic_ns()