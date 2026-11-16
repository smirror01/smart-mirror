"""Einstellungen für den Smart Mirror.

Das ist die einzige Datei, die du normalerweise anpassen musst.
Geheime Schlüssel gehören NICHT hier hinein, sondern in config_geheim.py.
"""

# ---------------------------------------------------------------
# Anschlüsse auf der GrovePi-Platine
# Die Zahl ist die Nummer der Buchse (D2 -> 2, A0 -> 0).
# None bedeutet: Dieses Modul ist nicht angeschlossen.
# ---------------------------------------------------------------
PORT_DHT = 2            # D2: Temperatur- und Feuchtesensor
DHT_TYP = 0             # 0 = blauer Sensor (DHT11), 1 = weißer Sensor (DHT22)
PORT_TASTER = 3         # D3: Taster, wechselt die Ansicht und stoppt Timer/Wecker
PORT_ULTRASCHALL = 4    # D4: Abstandssensor, erkennt ob jemand vor dem Spiegel steht
PORT_STATUS_LED = 5     # D5: LED, leuchtet solange der Spiegel zuhört
PORT_LICHT = 6          # D6: LED oder Relais für "Spiegel, Licht an"
PORT_SUMMER = 7         # D7: Summer, piept bei Timer und Wecker
PORT_DREHREGLER = 0     # A0: Drehregler für die Helligkeit der Schrift
LCD_AKTIV = True        # kleines LCD-Display an einer I2C-Buchse (False = nicht angeschlossen)

# ---------------------------------------------------------------
# Anwesenheit
# ---------------------------------------------------------------
ANWESENHEIT_CM = 120        # näher als so viele cm = jemand steht davor
AUSSCHALTEN_NACH_S = 30     # so viele Sekunden nach der letzten Erkennung wird die Anzeige schwarz
MONITOR_AUSSCHALTEN = False  # True = Monitor zusätzlich wirklich abschalten (geht nicht auf jedem System)

# ---------------------------------------------------------------
# Raumklima
# ---------------------------------------------------------------
LUEFTEN_AB_PROZENT = 60     # ab dieser Luftfeuchtigkeit erscheint "Bitte lüften"

# ---------------------------------------------------------------
# Wetter (kommt von open-meteo.com, kein Konto nötig)
# ---------------------------------------------------------------
WETTER_AKTIV = True
ORT_NAME = "Berlin"
BREITENGRAD = 52.52
LAENGENGRAD = 13.405

# ---------------------------------------------------------------
# Nachrichten (Schlagzeilen aus einem RSS-Feed)
# ---------------------------------------------------------------
NACHRICHTEN_AKTIV = True
NACHRICHTEN_URL = "https://www.tagesschau.de/index~rss2.xml"
NACHRICHTEN_ANZAHL = 8

# ---------------------------------------------------------------
# Abfahrten von Bus und Bahn (nur Berlin/Brandenburg, inoffizielle BVG-Schnittstelle)
# Name der Haltestelle so, wie er in der BVG-App steht. "" = ausgeschaltet.
# ---------------------------------------------------------------
HALTESTELLE = "U Ernst-Reuter-Platz"
ABFAHRTEN_ANZAHL = 4

# ---------------------------------------------------------------
# Kalender: Internetadresse (oder Dateipfad) eines Kalenders im ICS-Format.
# None = ausgeschaltet. Wie du die Adresse bekommst, steht in der README.
# ---------------------------------------------------------------
KALENDER_URL = None
KALENDER_TAGE = 7           # so viele Tage im Voraus anzeigen
KALENDER_ANZAHL = 4

# ---------------------------------------------------------------
# Countdowns: Name und Datum (Jahr-Monat-Tag). Vergangene werden ausgeblendet.
# ---------------------------------------------------------------
COUNTDOWNS = [
    ("Weihnachten", "2026-12-24"),
    ("Silvester", "2026-12-31"),
]

# ---------------------------------------------------------------
# Timer und Wecker
# ---------------------------------------------------------------
WECKER = None               # feste Weckzeit, z. B. "07:30". None = kein Wecker
KLINGEL_DAUER_S = 60        # so lange klingelt es höchstens

# ---------------------------------------------------------------
# Sprachsteuerung (braucht USB-Mikrofon und Lautsprecher, siehe README)
# ---------------------------------------------------------------
SPRACHE_AKTIV = True
AKTIVIERUNGSWOERTER = ["spiegel"]   # klein geschrieben; eines davon muss im Satz vorkommen
VOSK_MODELL = "modell"              # Ordner mit dem Sprachmodell, liegt neben spiegel.py
MIKROFON = None                     # None = Standardmikrofon, sonst z. B. "plughw:1,0"
SPRECHTEMPO = 150                   # Wörter pro Minute
BEGRUESSUNG_SPRECHEN = False        # True = Spiegel sagt "Guten Morgen", wenn jemand kommt

# ---------------------------------------------------------------
# Freie Fragen mit KI (optional, kostet Geld, braucht Internet)
# Wird nur benutzt, wenn in config_geheim.py ein Schlüssel steht.
# ---------------------------------------------------------------
KI_AKTIV = True
KI_MODELL = "claude-haiku-5-5"

# ---------------------------------------------------------------
# Musik: MP3-Dateien im Ordner "musik" oder ein Internetradio
# ---------------------------------------------------------------
MUSIK_ORDNER = "musik"
RADIO_URL = None            # Adresse eines MP3-Radiostreams, None = Dateien aus dem Ordner spielen

# ---------------------------------------------------------------
# Anzeige
# ---------------------------------------------------------------
VOLLBILD = True
SCHRIFTART = "DejaVu Sans"
MELDUNG_DAUER_S = 8         # so lange bleibt eine Antwort auf dem Bildschirm stehen
LAUFZEILE_WECHSEL_S = 12    # so oft wechselt die Zeile mit Spruch und Schlagzeilen

# ---------------------------------------------------------------
# Geheime Werte (KI-Schlüssel, private Kalenderadresse) stehen in config_geheim.py.
# Was dort steht, ersetzt die Werte aus dieser Datei.
# ---------------------------------------------------------------
KI_SCHLUESSEL = ""
try:
    from config_geheim import *     # noqa: F401,F403
except ImportError:
    pass
