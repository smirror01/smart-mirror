"""Hilfen für alles, was aus dem Internet kommt."""

import threading
import time
import urllib.request


def hole(adresse, kopf=None, daten=None, timeout=10):
    """Lädt eine Internetadresse und gibt den Inhalt als Bytes zurück."""
    alle_kopfzeilen = {"User-Agent": "smart-mirror/1.0"}
    alle_kopfzeilen.update(kopf or {})
    anfrage = urllib.request.Request(adresse, data=daten, headers=alle_kopfzeilen)
    with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
        return antwort.read()


class Abruf(threading.Thread):
    """Ruft eine Lade-Funktion regelmäßig im Hintergrund auf.

    name:           für Meldungen im Terminal
    lade:           Funktion, die die Daten holt und zurückgibt
    speichere:      Funktion, die die Daten ablegt (bekommt None, wenn sie veraltet sind)
    intervall_s:    Abstand zwischen zwei Abrufen
    verfaellt_s:    nach so langer Zeit ohne Erfolg gelten die Daten als veraltet
    """

    def __init__(self, name, lade, speichere, intervall_s, verfaellt_s):
        super().__init__(daemon=True)
        self.name_ = name
        self.lade = lade
        self.speichere = speichere
        self.intervall_s = intervall_s
        self.verfaellt_s = verfaellt_s

    def run(self):
        gemeldet = False
        letzter_erfolg = time.time()
        while True:
            try:
                self.speichere(self.lade())
                letzter_erfolg = time.time()
                gemeldet = False
                pause = self.intervall_s
            except Exception as fehler:
                if not gemeldet:
                    print("[{}] Konnte nicht geladen werden ({}). "
                          "Internetverbindung prüfen.".format(self.name_, fehler))
                    gemeldet = True
                if time.time() - letzter_erfolg > self.verfaellt_s:
                    self.speichere(None)
                pause = min(60, self.intervall_s)
            time.sleep(pause)
