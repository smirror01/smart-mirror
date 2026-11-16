"""Liest die Grove-Sensoren aus und schaltet LEDs, Relais, Summer und LCD.

Alle Zugriffe auf die GrovePi-Platine laufen über diese Datei. Die Platine
verträgt keine gleichzeitigen Zugriffe, deshalb sichert ein Schloss
(threading.Lock) jeden einzelnen ab.

Fehlt die GrovePi-Bibliothek (z. B. auf deinem eigenen Rechner), startet
automatisch der Simulationsmodus mit ausgedachten Messwerten.
"""

import json
import math
import os
import threading
import time

import config

try:
    import grovepi
    SIMULATION = False
except Exception as fehler:  # nicht installiert oder I2C abgeschaltet
    grovepi = None
    SIMULATION = True
    print("[Sensoren] GrovePi nicht verfügbar ({}). Simulationsmodus.".format(fehler))

VERLAUF_DATEI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verlauf.json")
VERLAUF_ABSTAND_S = 300         # alle 5 Minuten einen Messwert merken
VERLAUF_DAUER_S = 24 * 3600     # 24 Stunden aufbewahren


class Zustand:
    """Alles, was der Spiegel gerade weiß. Anzeige und Befehle lesen von hier."""

    def __init__(self):
        # von den Sensoren
        self.temperatur = None          # Raumtemperatur in °C
        self.feuchte = None             # Luftfeuchtigkeit in %
        self.abstand = None             # Abstand in cm
        self.zuletzt_gesehen = time.time()  # wann zuletzt jemand vor dem Spiegel stand
        self.helligkeit = 1.0           # 0.25 (dunkel) bis 1.0 (hell)
        self.verlauf = []               # Liste aus (Zeitstempel, Temperatur) der letzten 24 h
        # aus dem Internet (None = nicht verfügbar)
        self.wetter = None
        self.nachrichten = None
        self.abfahrten = None
        self.termine = None
        # geschaltete Dinge
        self.licht = False              # ist das Licht an D6 eingeschaltet?
        self.musik = False              # läuft Musik?
        self.timer_ende = None          # Zeitstempel, wann der Timer abläuft
        self.wecker = config.WECKER     # "07:30" oder None
        self.klingelt = None            # "Timer" oder "Wecker", solange es klingelt


class Sensoren(threading.Thread):
    """Läuft im Hintergrund und fragt die Sensoren regelmäßig ab."""

    TAKT = 0.05  # Sekunden zwischen zwei Durchläufen

    def __init__(self, zustand, ereignisse):
        super().__init__(daemon=True)
        self.zustand = zustand
        self.ereignisse = ereignisse
        self.sim_anwesend = True        # nur im Simulationsmodus (Taste A)
        self._schloss = threading.Lock()
        self._gemeldet = set()
        self._taster_vorher = 0
        self._summer_an = False
        self._lcd = None
        self._lcd_sim = None
        self._verlauf_laden()

    # ---------- Schalten ----------

    def schalte(self, port, an):
        """Schaltet einen digitalen Ausgang (LED, Relais, Summer) ein oder aus."""
        if port is None:
            return
        if SIMULATION:
            if port != config.PORT_SUMMER:      # das Piepen würde das Terminal fluten
                print("[Simulation] D{} {}".format(port, "AN" if an else "AUS"))
            return
        try:
            with self._schloss:
                grovepi.digitalWrite(port, 1 if an else 0)
        except Exception as fehler:
            self._melde("Ausgang D{}".format(port), fehler)

    def licht(self, an):
        self.zustand.licht = an
        self.schalte(config.PORT_LICHT, an)

    def status_led(self, an):
        self.schalte(config.PORT_STATUS_LED, an)

    def aufraeumen(self):
        """Beim Beenden alles ausschalten."""
        self.zustand.klingelt = None
        self.status_led(False)
        self.schalte(config.PORT_LICHT, False)
        self.schalte(config.PORT_SUMMER, False)
        if self._lcd:
            try:
                with self._schloss:
                    self._lcd.aus()
            except Exception:
                pass

    # ---------- Lesen ----------

    def run(self):
        self._einrichten()
        naechster_abstand = 0
        naechstes_klima = 0
        while True:
            jetzt = time.time()
            self._lies_taster()
            self._summer(jetzt)
            if jetzt >= naechster_abstand:      # alle 0,5 s
                self._lies_abstand()
                self._lies_drehregler()
                naechster_abstand = jetzt + 0.5
            if jetzt >= naechstes_klima:        # alle 15 s
                self._lies_klima()
                self._zeige_lcd()
                naechstes_klima = jetzt + 15
            time.sleep(self.TAKT)

    def _einrichten(self):
        if SIMULATION:
            return
        try:
            with self._schloss:
                if config.PORT_TASTER is not None:
                    grovepi.pinMode(config.PORT_TASTER, "INPUT")
                for port in (config.PORT_STATUS_LED, config.PORT_LICHT, config.PORT_SUMMER):
                    if port is not None:
                        grovepi.pinMode(port, "OUTPUT")
                        grovepi.digitalWrite(port, 0)
        except Exception as fehler:
            self._melde("Einrichten", fehler)
        if config.LCD_AKTIV:
            try:
                from lcd import Lcd
                self._lcd = Lcd()
            except Exception as fehler:
                self._melde("LCD", fehler)

    def _lies_taster(self):
        if config.PORT_TASTER is None or SIMULATION:
            return
        try:
            with self._schloss:
                wert = grovepi.digitalRead(config.PORT_TASTER)
        except Exception as fehler:
            self._melde("Taster", fehler)
            return
        if wert == 1 and self._taster_vorher == 0:
            self.ereignisse.put(("taster", None))
        if wert in (0, 1):
            self._taster_vorher = wert

    def _summer(self, jetzt):
        """Piept im Rhythmus kurz-kurz-Pause, solange Timer oder Wecker klingeln."""
        if config.PORT_SUMMER is None:
            return
        phase = jetzt % 1.0
        soll = bool(self.zustand.klingelt) and (phase < 0.15 or 0.3 <= phase < 0.45)
        if soll != self._summer_an:
            self._summer_an = soll
            self.schalte(config.PORT_SUMMER, soll)

    def _lies_abstand(self):
        if config.PORT_ULTRASCHALL is None:
            self.zustand.zuletzt_gesehen = time.time()
            return
        if SIMULATION:
            abstand = 60 if self.sim_anwesend else 300
        else:
            try:
                with self._schloss:
                    abstand = grovepi.ultrasonicRead(config.PORT_ULTRASCHALL)
            except Exception as fehler:
                self._melde("Ultraschallsensor", fehler)
                return
        if not isinstance(abstand, (int, float)) or abstand <= 0 or abstand > 500:
            return  # Messfehler, Wert verwerfen
        self.zustand.abstand = int(abstand)
        if abstand < config.ANWESENHEIT_CM:
            self.zustand.zuletzt_gesehen = time.time()

    def _lies_drehregler(self):
        if config.PORT_DREHREGLER is None or SIMULATION:
            return
        try:
            with self._schloss:
                wert = grovepi.analogRead(config.PORT_DREHREGLER)
        except Exception as fehler:
            self._melde("Drehregler", fehler)
            return
        if not isinstance(wert, (int, float)) or wert < 0 or wert > 1023:
            return
        neu = 0.25 + 0.75 * wert / 1023.0
        if abs(neu - self.zustand.helligkeit) > 0.03:  # kleines Zittern ignorieren
            self.zustand.helligkeit = neu

    def _lies_klima(self):
        if config.PORT_DHT is None:
            return
        if SIMULATION:
            self.zustand.temperatur, self.zustand.feuchte = 21.5, 45.0
            return
        try:
            with self._schloss:
                temperatur, feuchte = grovepi.dht(config.PORT_DHT, config.DHT_TYP)
        except Exception as fehler:
            self._melde("Temperatursensor", fehler)
            return
        # Der Sensor liefert manchmal "nan" oder Unsinn. Solche Werte verwerfen.
        try:
            if -20 <= temperatur <= 60 and 0 < feuchte <= 100:
                self.zustand.temperatur = float(temperatur)
                self.zustand.feuchte = float(feuchte)
                self._verlauf_merken(float(temperatur))
        except TypeError:
            pass

    def _zeige_lcd(self):
        """Raumklima auf dem kleinen Display: blau = kühl, grün = angenehm, rot = warm."""
        temperatur, feuchte = self.zustand.temperatur, self.zustand.feuchte
        if not config.LCD_AKTIV or temperatur is None:
            return
        text = "Raum {:.1f} C\nFeuchte {:.0f} %".format(temperatur, feuchte)
        if temperatur < 19:
            farbe = (0, 80, 255)
        elif temperatur <= 24:
            farbe = (0, 200, 80)
        else:
            farbe = (255, 60, 0)
        if SIMULATION:
            if (text, farbe) != self._lcd_sim:
                self._lcd_sim = (text, farbe)
                print("[Simulation] LCD {}: {}".format(farbe, text.replace("\n", " | ")))
            return
        if self._lcd is None:
            return
        try:
            with self._schloss:
                self._lcd.zeige(text, farbe)
        except Exception as fehler:
            self._melde("LCD", fehler)
            self._lcd = None    # nicht angeschlossen: nicht weiter versuchen

    # ---------- Temperaturverlauf ----------

    def _verlauf_laden(self):
        jetzt = time.time()
        if SIMULATION:      # ausgedachte Kurve, damit man in der Simulation etwas sieht
            self.zustand.verlauf = [
                (jetzt - alter, 20.5 + 1.5 * math.sin(alter / 14000.0) + 0.4 * math.sin(alter / 2500.0))
                for alter in range(VERLAUF_DAUER_S, 0, -VERLAUF_ABSTAND_S)]
            return
        try:
            with open(VERLAUF_DATEI) as datei:
                self.zustand.verlauf = [(float(z), float(t)) for z, t in json.load(datei)
                                        if jetzt - z < VERLAUF_DAUER_S]
        except (OSError, ValueError, TypeError):
            self.zustand.verlauf = []

    def _verlauf_merken(self, temperatur):
        jetzt = time.time()
        verlauf = self.zustand.verlauf
        if verlauf and jetzt - verlauf[-1][0] < VERLAUF_ABSTAND_S:
            return
        neu = [punkt for punkt in verlauf if jetzt - punkt[0] < VERLAUF_DAUER_S]
        neu.append((jetzt, temperatur))
        self.zustand.verlauf = neu
        try:
            with open(VERLAUF_DATEI, "w") as datei:
                json.dump(neu, datei)
        except OSError as fehler:
            self._melde("Verlauf speichern", fehler)

    def _melde(self, name, fehler):
        """Gibt jeden Fehler nur einmal aus, damit das Terminal lesbar bleibt."""
        if name not in self._gemeldet:
            self._gemeldet.add(name)
            print("[Sensoren] Problem mit {}: {}. Anschluss und config.py prüfen.".format(name, fehler))
