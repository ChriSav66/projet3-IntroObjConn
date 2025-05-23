import board
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import os
import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT


class ecran:

    def __init__(self):
        displayio.release_displays()
        self.i2c = board.I2C()
        self.display_bus = displayio.I2CDisplay(self.i2c, device_address=0x3C)
        self.display = adafruit_displayio_ssd1306.SSD1306(self.display_bus, width=128, height=64, rotation=180)
        self.splash = displayio.Group()
        self.display.root_group = self.splash

        self.text = ""
        self.text_area = label.Label(terminalio.FONT, text=self.text, color=0xFFFFFF, x=5, y=10)
        self.splash.append(self.text_area)

    def rafraichir_texte(self, texte):
        self.text_area.text = texte
        self.display.refresh()

    @property
    def texte(self):
        return self.text_area.text

# Fonctions pour MQTT
# Définir les fonctions de rappel qui seront appelées lorsque certains événements se produisent.
# pylint: disable=unused-argument
def connected(client):
    # La fonction Connected sera appelée lorsque le client sera connecté à Adafruit IO.
    # C'est un bon endroit pour s'abonner aux changements de flux. Le paramètre client
    # passé à cette fonction est le client MQTT Adafruit IO, vous pouvez donc effectuer
    # des appels facilement.
    print("Connecté à Adafruit IO !")


def subscribe(client, userdata, topic, granted_qos):
    # Cette méthode est appelée lorsque le client s'abonne à un nouveau flux.
    print("Abonné à {0} avec un niveau de QOS {1}".format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # Cette méthode est appelée lorsque le client se désabonne d'un flux.
    print("Désabonné de {0} avec PID {1}".format(topic, pid))


# pylint: disable=unused-argument
def disconnected(client):
    # La fonction Disconnected sera appelée lorsque le client se déconnecte.
    print("Déconnecté d'Adafruit IO !")

# pylint: disable=unused-argument
def message(client, feed_id, payload):
    # La fonction message sera appelée lorsque le flux auquel on est abonné a une nouvelle valeur.
    # Le paramètre feed_id identifie le flux, et le paramètre payload contient la nouvelle valeur.
    print("Le flux {0} a reçu une nouvelle valeur : {1}".format(feed_id, payload))

def connecter_mqtt():
    # Connexion au WIFI à partir des informations de settings.toml
    try:
        if os.getenv("AIO_USERNAME") and os.getenv("AIO_KEY"):
            secrets = {
                "aio_username": os.getenv("AIO_USERNAME"),
                "aio_key": os.getenv("AIO_KEY"),
                "ssid": os.getenv("CIRCUITPY_WIFI_SSID"),
                "password": os.getenv("CIRCUITPY_WIFI_PASSWORD"),
            }
        else:
            raise ImportError
    except ImportError:
        print(
            "Les informations pour la connexion au WIFI et pour Adafruit IO ne sont pas disponibles dans le fichier settings.toml")
        raise

    aio_username = secrets["aio_username"]
    aio_key = secrets["aio_key"]

    if not wifi.radio.connected:
        print("Connexion à %s" % secrets["ssid"])
        wifi.radio.connect(secrets["ssid"], secrets["password"])
        print("Connecté à %s!" % secrets["ssid"])

    pool = socketpool.SocketPool(wifi.radio)
    mqtt = MQTT.MQTT(socket_pool=pool,
                    username=secrets["aio_username"],
                    password=secrets["aio_key"],
                    ssl_context=ssl.create_default_context(),
                    broker="io.adafruit.com",
                    is_ssl=True,
                    port=8883)
    io = IO_MQTT(mqtt)

    io.on_connect = connected
    io.on_disconnect = disconnected
    io.on_subscribe = subscribe
    io.on_unsubscribe = unsubscribe
    io.on_message = message

    io.connect()

    io.subscribe('projet3.mode')
    io.subscribe('projet3.quantite-nourriture')
    return io

def getSocket():
 return socketpool.SocketPool(wifi.radio)
