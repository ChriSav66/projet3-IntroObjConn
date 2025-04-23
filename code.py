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
import projet2
import tamponDonnee

# Mise en place des objets de la carte Arduino
i2c = board.I2C()
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
bmp280.sea_level_pressure = 1016.10
pot = analogio.AnalogIn(board.A0)

ecran = projet2.ecran()
last_time = time.monotonic_ns()
last_time_ecran = time.monotonic_ns()
last_time_reconnected = time.monotonic_ns()
last_time_send = time.monotonic_ns()

temp_actuelle: float = bmp280.temperature
temp_moyenne: float = 0
temp_max: float = temp_actuelle
temp_min: float = temp_actuelle

histTempMoy = []

#--Function------------------------------------------------------------------------------>
#Vérifie si la board est connecter au reseaux
#Si oui, retourne true Si non retourne false + message d'erreur
def verifier_connexion_wifi():
    try:
        return wifi.radio.connected
    except Exception as e:
        print(f"Erreur lors de la vérification de la connexion WiFi: {e}")
        return False

#C'est la méthode callback
#Affiche l'info reçue + sur quelle feed
#tempConv est un pour l'affiche des valer en Farhenret ou Celsius
def on_message(client, feed_id, payload):
    print(f"Message reçu sur le sujet: {feed_id}: {payload}")
    if feed_id == 'unite-temperature':
        global tempConv
        if payload == 'F':
            tempConv = True
        else:
            tempConv = False
    elif feed_id == 'reset-minmax':
        reinitialiser_min_max()

def reinitialiser_min_max():
    global temp_max, temp_min, temp_actuelle
    temp_min = temp_actuelle
    temp_max = temp_actuelle
    print(f"Valeurs min/max réinitialisées")

def calculeMoyenneGlissante(nouv_val):
    histTempMoy.append(nouv_val)

    if len(histTempMoy) > 300:
        histTempMoy.pop(0)

    return sum(histTempMoy) / len(histTempMoy)

def synchroniser_heure():
    try:
        pool = projet2.getSocket()
        ntp = adafruit_ntp.NTP(pool, server="pool.ntp.org")
        rtc.RTC().datetime = ntp.datetime
        print("Heure synchronisée", obtenir_heure_form())
        return True
    except Exception as e:
        print(f"Erreur lors de la synchronisation de l'heure: {e}")
        return False


def obtenir_heure_form():
    try:
        #Ligne vue 
        t = time.localtime(time.time() - 4 * 3600)
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
            t.tm_year, t.tm_mon, t.tm_mday,
            t.tm_hour, t.tm_min, t.tm_sec
        )
    except Exception as e:
            print(f"Erreur lors de l'obtention de l'heure: {e}")
            return "0000-00-00 00:00:00"
    
def init_carte_sd():
    try:
        sd_spi = board.SPI()
        sd_cs = board.IO15
        sd_card = sdcardio.SDCard(sd_spi, sd_cs)
        vfs = storage.VfsFat(sd_card)
        storage.mount(vfs, "/sd")
        print("Carte SD montée avec succès")
        return True
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la carte SD: {e}")
        return False

def ecrire_sd(temp):
    try:
        if not os.listdir("/sd"):
            return False
        # Obtenir l'heure actuelle formatée
        date_str = obtenir_heure_form()
        
        # Préparer la nouvelle entrée
        nouvelle_entree = {
            "date": date_str,
            "valeur": f"{temp:.1f}"
        }
        
        # Lire le fichier existant ou créer une liste vide
        donnees = []
        try:
            with open("/sd/log.json", "r") as f:
                donnees = json.load(f)
        except (OSError, ValueError):
            pass
        
        # Ajouter la nouvelle entrée et écrire le fichier
        donnees.append(nouvelle_entree)
        with open("/sd/log.json", "w") as f:
            json.dump(donnees, f)

            
        return True
    except Exception as e:
        print(f"Erreur lors de l'écriture sur la carte SD: {e}")
        return False
    except OSError as e:
        print(f"Le dossier /sd est vide: {e}")


#--Main------------------------------------------------------------------------------>

# Initialisation
io = projet2.connecter_mqtt()

io.on_message = on_message

isSynchronise = synchroniser_heure()

isGood = init_carte_sd()

#Pour que le toggle sur adafruit.io soit coérent avec ce qui est afficher
tempConv = False
io.publish('unite-temperature', 'C')

while True:
    try:
        io.loop()
    except Exception as e:
        print(f"Erreur MQTT: {e}")
#Si il détecte pas de connection wifi il vas essyer de ce reconnecter toute en laisson un message d'erreur jusqu'a ce qu'on se reconnecte
    if verifier_connexion_wifi() == False:
        print(f"Vous n'êtes pas connecté")
        if last_time_reconnected*(10**9) - time.monotonic_ns()*(10**9) > 60:
            try:
                io = projet2.connecter_mqtt()
                io.on_message = on_message
            except Exception as e:
                print(e)
            last_time_reconnected = time.monotonic_ns()

    temp_moyenne = calculeMoyenneGlissante(temp_actuelle)
    

    if time.monotonic_ns()*(10**9) - last_time_ecran*(10**9) > 0.5:

        if temp_min > temp_actuelle:
            temp_min = temp_actuelle
        elif temp_max < temp_actuelle:
            temp_max = temp_actuelle

        if(time.monotonic_ns()*(10**9) - last_time > 1):
            temp_actuelle = bmp280.temperature
            last_time = time.monotonic_ns()
        
        

        if tempConv:
            ecran.rafraichir_texte("Température\nactuelle:{:.1f}°F\nmoyenne:{:.1f}°F\nmin:{:.1f}°F  max:{:.1f}°F".format(projet2.celcius_to_fahrenheit(temp_actuelle),projet2.celcius_to_fahrenheit(temp_moyenne),projet2.celcius_to_fahrenheit(temp_min),projet2.celcius_to_fahrenheit(temp_max)))
        else:
            ecran.rafraichir_texte("Température\nactuelle:{:.1f}°C\nmoyenne:{:.1f}°C\nmin:{:.1f}°C  max:{:.1f}°C".format(temp_actuelle,temp_moyenne,temp_min,temp_max))
        last_time_ecran = time.monotonic_ns()

    if isGood:
        ecrire_sd(temp_actuelle)
    
    if(time.monotonic_ns()*(10**9) - last_time_send*(10**9) > 1):
        io.publish('temperature', temp_actuelle)
        io.publish('temperature-moyenne',temp_moyenne)
        last_time_send = time.monotonic_ns()

        
