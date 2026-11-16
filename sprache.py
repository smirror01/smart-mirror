"""Sprachausgabe (Sprecher) und Spracherkennung (Zuhoerer).

Beides läuft ohne Internet direkt auf dem Pi:
- Ausgabe mit espeak-ng
- Erkennung mit Vosk, das Mikrofon wird über das Programm arecord gelesen

Fehlt etwas davon, gibt es einen Hinweis im Terminal und der Spiegel
läuft ohne Sprache weiter.
"""

import json
import os
import queue
import shutil
import subprocess
import threading
import time

import config

ABTASTRATE = 16000   # Hertz, so erwartet es das Sprachmodell
SCHARF_SEKUNDEN = 8  # so lange wartet der Spiegel nach "Spiegel" auf den Befehl


class Sprecher:
    """Spricht Texte nacheinander aus, ohne die Anzeige zu blockieren."""

    def __init__(self):
        self.programm = shutil.which("espeak-ng") or shutil.which("espeak")
        self.spricht = threading.Event()   # gesetzt, solange gesprochen wird
        self._warteschlange = queue.Queue()
        if config.SPRACHE_AKTIV and not self.programm:
            print("[Sprache] espeak-ng fehlt, Antworten erscheinen nur als Text. "
                  "Installieren mit: sudo apt install espeak-ng")
        threading.Thread(target=self._lauf, daemon=True).start()

    def sage(self, text):
        if config.SPRACHE_AKTIV and self.programm:
            self.spricht.set()
            self._warteschlange.put(text)

    def _lauf(self):
        while True:
            text = self._warteschlange.get()
            try:
                subprocess.run(
                    [self.programm, "-v", "de", "-s", str(config.SPRECHTEMPO), text],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            except Exception as fehler:
                print("[Sprache] Ausgabe fehlgeschlagen: {}".format(fehler))
            if self._warteschlange.empty():
                time.sleep(0.4)            # Nachhall abwarten
                self.spricht.clear()


class Zuhoerer(threading.Thread):
    """Hört dauerhaft zu und meldet Befehle, die mit dem Aktivierungswort beginnen.

    Beispiel: "Spiegel, wie warm ist es?"  ->  Ereignis ("befehl", "wie warm ist es")
    Sagt jemand nur "Spiegel", gilt der nächste Satz als Befehl.
    """

    def __init__(self, ereignisse, sprecher):
        super().__init__(daemon=True)
        self.ereignisse = ereignisse
        self.sprecher = sprecher
        self.bereit = False        # True, sobald wirklich zugehört wird
        self._scharf_bis = 0
        self._wach = False

    def run(self):
        try:
            from vosk import KaldiRecognizer, Model, SetLogLevel
        except ImportError:
            print("[Sprache] Vosk ist nicht installiert, Spracherkennung aus. "
                  "Installieren mit: pip3 install vosk")
            return
        ordner = os.path.dirname(os.path.abspath(__file__))
        modellpfad = os.path.join(ordner, config.VOSK_MODELL)
        if not os.path.isdir(modellpfad):
            print("[Sprache] Sprachmodell fehlt (Ordner '{}'), Spracherkennung aus. "
                  "Siehe README, Abschnitt Sprachsteuerung.".format(modellpfad))
            return
        if not shutil.which("arecord"):
            print("[Sprache] Das Programm arecord fehlt, Spracherkennung aus. "
                  "Installieren mit: sudo apt install alsa-utils")
            return

        SetLogLevel(-1)
        print("[Sprache] Lade Sprachmodell ...")
        modell = Model(modellpfad)

        befehl = ["arecord", "-q", "-f", "S16_LE", "-r", str(ABTASTRATE), "-c", "1", "-t", "raw"]
        if config.MIKROFON:
            befehl += ["-D", config.MIKROFON]

        gemeldet = False
        while True:
            aufnahme = subprocess.Popen(befehl, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            gelesen = self._hoere(aufnahme, KaldiRecognizer, modell)
            aufnahme.kill()
            aufnahme.wait()
            self.bereit = False
            if not gelesen and not gemeldet:
                print("[Sprache] Kein Mikrofon gefunden. Ist das USB-Mikrofon eingesteckt? "
                      "Mit 'arecord -l' prüfen und MIKROFON in config.py setzen.")
                gemeldet = True
            if gelesen:
                gemeldet = False
            time.sleep(5)   # dann neu versuchen, z. B. nach dem Einstecken

    def _hoere(self, aufnahme, KaldiRecognizer, modell):
        """Liest Ton vom Mikrofon, bis die Aufnahme abbricht. True, wenn Ton ankam."""
        erkenner = KaldiRecognizer(modell, ABTASTRATE)
        gelesen = False
        pausiert = False
        while True:
            daten = aufnahme.stdout.read(4000)   # eine Achtelsekunde Ton
            if not daten:
                return gelesen
            if not gelesen:
                gelesen = True
                self.bereit = True
                print("[Sprache] Ich höre zu. Sag zum Beispiel: Spiegel, wie spät ist es?")
            # Während der Spiegel selbst spricht, nicht zuhören,
            # sonst versteht er seine eigene Antwort als Befehl.
            if self.sprecher.spricht.is_set():
                pausiert = True
                continue
            if pausiert:
                erkenner = KaldiRecognizer(modell, ABTASTRATE)
                pausiert = False
            if erkenner.AcceptWaveform(daten):
                self._satz(json.loads(erkenner.Result()).get("text", ""))
            elif not self._wach:
                teil = json.loads(erkenner.PartialResult()).get("partial", "")
                if self._finde_wort(teil) is not None:
                    self._wach = True
                    self.ereignisse.put(("hoert_zu", None))

    def _finde_wort(self, text):
        """Gibt den Text hinter dem Aktivierungswort zurück, sonst None."""
        woerter = text.lower().split()
        for stelle, wort in enumerate(woerter):
            if wort in config.AKTIVIERUNGSWOERTER:
                return " ".join(woerter[stelle + 1:])
        return None

    def _satz(self, text):
        """Wird aufgerufen, sobald ein ganzer Satz erkannt wurde."""
        war_wach = self._wach
        self._wach = False
        if not text:
            if war_wach:
                self.ereignisse.put(("abbruch", None))
            return
        rest = self._finde_wort(text)
        jetzt = time.time()
        if rest is not None:
            if rest:
                self._scharf_bis = 0
                self.ereignisse.put(("befehl", rest))
            else:                                   # nur "Spiegel" gesagt
                self._scharf_bis = jetzt + SCHARF_SEKUNDEN
                self.ereignisse.put(("hoert_zu", None))
        elif jetzt < self._scharf_bis:
            self._scharf_bis = 0
            self.ereignisse.put(("befehl", text))
        elif war_wach:
            self.ereignisse.put(("abbruch", None))
