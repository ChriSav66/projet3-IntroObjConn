import board
import digitalio
import analogio
import time
import adafruit_bmp280
import wifi
import socketpool
import rtc
import adafruit_ntp
import sdcardio
import storage
import json
import os
import pwmio
from adafruit_motor import servo
import adafruit_vcnl4200
import projet2

global etatSys

def init_sensor():
    i2c = board.I2C()
    pwm = pwmio.PWMOut(board.IO18, duty_cycle=2 ** 15, frequency=50)

    ecran = servo_motor = presence = dc_motor = bouton = None

    try:
        ecran = projet2.ecran()
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur écran : {e}")

    try:
        potentiometre = analogio.AnalogIn(board.IO17)
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur potentiomètre : {e}")

    try:
        led = digitalio.DigitalInOut(board.IO11)
        led.direction = digitalio.Direction.OUTPUT
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur LED : {e}")

    try:
        servo_motor = servo.Servo(pwm)
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur servo : {e}")

    try:
        presence = adafruit_vcnl4200.Adafruit_VCNL4200(i2c)
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur capteur de proximité : {e}")

    try:
        dc_motor = digitalio.DigitalInOut(board.IO12)
        dc_motor.direction = digitalio.Direction.OUTPUT
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur moteur DC : {e}")

    try:
        bouton = digitalio.DigitalInOut(board.IO10)
        bouton.direction = digitalio.Direction.INPUT
        bouton.pull = digitalio.Pull.DOWN
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur bouton : {e}")

    capteurs_ok = all([ecran, servo_motor, presence, led, potentiometre, dc_motor, bouton])
    return ecran, servo_motor, presence, capteurs_ok, led, potentiometre, dc_motor, bouton

def verifier_connexion_wifi():
    try:
        return wifi.radio.connected
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur lors de la vérification WiFi: {e}")
        return False

def on_message(client, feed_id, payload):
    global etatDemande, capteurs_ok, etatSys, qteNour
    print(f"[{obtenir_heure_form()}] Message reçu sur {feed_id}: {payload}")
    if feed_id == 'projet3.mode':
        if payload == "1":
            etatDemande = True
        elif payload == "2":
            etatDemande = False
        else:
            print(f"[{obtenir_heure_form()}] Payload mode invalide, mode manuel forcé : {payload}")
            etatDemande = False
        etatSys = etatDemande and capteurs_ok
    elif feed_id == 'projet3.quantite-nourriture':
        try:
            qteNour = int(payload)
            print(f"[{obtenir_heure_form()}] Quantité nourriture reçue : {qteNour} kg")
        except ValueError:
            print(f"[{obtenir_heure_form()}] Valeur invalide pour nourriture: {payload}")

def synchroniser_heure():
    try:
        pool = projet2.getSocket()
        ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org", tz_offset=-4)
        rtc.RTC().datetime = ntp.datetime
        print(f"[{obtenir_heure_form()}] Heure synchronisée.")
        return True
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur synchro heure: {e}")
        return False

def obtenir_heure_form():
    try:
        t = time.localtime()
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
    except Exception as e:
        return "0000-00-00 00:00:00"

def get_pot_value_percent():
    return potentiometre.value / 65535 * 100

def gerer_leds_nourriture():
    global led_time, led_state
    global dc_motor_active, dc_motor_start_time, dc_motor_authorized

    pourcentage = get_pot_value_percent()

    if 10 < pourcentage <= 25:
        print(f"[{obtenir_heure_form()}] Il reste moins de 25% de nourriture.")
        led.value = True
    elif pourcentage <= 10:
        if time.monotonic_ns() - led_time >= (10**9):
            print(f"[{obtenir_heure_form()}] Il reste moins de 10% de nourriture.")
            led_state = not led_state
            led_time = time.monotonic_ns()
        led.value = led_state
    else:
        led.value = False

    if pourcentage <= 25:
        dc_motor_authorized = True
        if not dc_motor_active and dc_motor:
            dc_motor.value = False

    if pourcentage > 25 and dc_motor_authorized and not dc_motor_active:
        dc_motor_active = True
        dc_motor_authorized = False 
        dc_motor_start_time = time.monotonic_ns()
        if dc_motor:
            print(f"[{obtenir_heure_form()}] Moteur DC activé.")
            dc_motor.value = True

    if dc_motor_active and time.monotonic_ns() - dc_motor_start_time >= qteNour * 1.5 * 1e9:
        if dc_motor:
            print(f"[{obtenir_heure_form()}] Moteur DC désactivé après {1.5 * qteNour} sec.")
            dc_motor.value = False
        dc_motor_active = False



# -- Initialisation --------------------------------------------------------------->
ecran, servoMotor, presence, capteurs_ok, led, potentiometre, dc_motor, bouton = init_sensor()

dc_motor_authorized = True
etatDemande = False
etatSys = etatDemande and capteurs_ok
last_time_reconnected = last_time_ecran = servo_time = presence_time = led_time = time.monotonic_ns()
is_time_servo = led_state = etat_bouton_precedent = servo_ouvert = dc_motor_active = False
dc_motor_start_time = 0
qteNour = 1  

io = projet2.connecter_mqtt()
io.on_message = on_message

while True:
    try:
        io.loop()
    except Exception as e:
        print(f"[{obtenir_heure_form()}] Erreur MQTT: {e}")

    if not verifier_connexion_wifi():
        print(f"[{obtenir_heure_form()}] Perte de connexion Internet.")
        if last_time_reconnected - time.monotonic_ns() > 60 * (10**9):
            try:
                io = projet2.connecter_mqtt()
                io.on_message = on_message
            except Exception as e:
                print(f"[{obtenir_heure_form()}] Erreur reconnexion: {e}")
            last_time_reconnected = time.monotonic_ns()
        else:
            synchroniser_heure()

    if capteurs_ok:
        try:
             proximite_val = presence.proximity
        except Exception as e:
            print(f"[{obtenir_heure_form()}] Perte de communication capteur: {e}")
            capteurs_ok = False
            etatSys = False
            io.publish('projet3.mode', '2')

    etatSys = etatDemande and capteurs_ok

    etat_bouton = bouton.value 

    if etatSys:
        t = time.localtime()
        if t.tm_hour >= 15 and t.tm_min >= 30 and not is_time_servo:
            if presence and presence.proximity > 10000 and time.monotonic_ns() - presence_time > 5 * (10**9):
                if servoMotor:
                    temps_activation_ms = qteNour * 1500
                    print(f"[{obtenir_heure_form()}] Servo activé pour {temps_activation_ms} ms (qte: {qteNour} kg).")
                    is_time_servo = True
                    servo_time = presence_time = time.monotonic_ns()
                    servoMotor.angle = 180

       

        if is_time_servo and time.monotonic_ns() - servo_time > (qteNour * 1.5 * 10**6):
            if servoMotor:
                print(f"[{obtenir_heure_form()}] Servo désactivé.")
                servoMotor.angle = 0
                is_time_servo = False

    if etat_bouton and not etat_bouton_precedent:
        if not etatSys:
            servo_ouvert = not servo_ouvert
            if servoMotor:
                servoMotor.angle = 180 if servo_ouvert else 0
                print(f"[{obtenir_heure_form()}] [MANUEL] Bouton : servo {'ouvert' if servo_ouvert else 'fermé'}.")
        else:
            print(f"[{obtenir_heure_form()}] [INFO] Appui bouton ignoré : système en mode automatique.")


    etat_bouton_precedent = etat_bouton  

    gerer_leds_nourriture()

    if ecran and time.monotonic_ns() - last_time_ecran > 10**9:

        if presence:
            proximite_val = presence.proximity
        else:
            proximite_val = "Err"

        pot_val = get_pot_value_percent()
        etat_dc = "ON" if dc_motor_active else "OFF"
        etat_bouton_str = "Pressé" if etat_bouton else "Relâché"

        ecran.rafraichir_texte("Mode: {} Qte: {} kg\nPot: {:.1f}%  Prox: {}\nBtn: {} DC: {}".format("A" if etatSys else "M",qteNour,pot_val,proximite_val,etat_bouton_str,etat_dc))
        last_time_ecran = time.monotonic_ns()