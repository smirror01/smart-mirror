"""Spielt MP3-Dateien aus dem Ordner "musik" oder ein Internetradio.

Benutzt ein Abspielprogramm, das auf dem Pi installiert ist
(mpg123, mpv, VLC oder mplayer). Fehlt eines: sudo apt install mpg123
"""

import glob
import os
import shutil
import subprocess

import config

# Programm -> (Befehl für Dateien in zufälliger Endlosschleife, Befehl für einen Radiostream)
PROGRAMME = [
    ("mpg123", ["mpg123", "-q", "-Z"], ["mpg123", "-q"]),
    ("mpv", ["mpv", "--no-video", "--really-quiet", "--shuffle", "--loop-playlist"],
     ["mpv", "--no-video", "--really-quiet"]),
    ("cvlc", ["cvlc", "--quiet", "--random", "--loop"], ["cvlc", "--quiet"]),
    ("mplayer", ["mplayer", "-really-quiet", "-shuffle", "-loop", "0"],
     ["mplayer", "-really-quiet"]),
]


class Musik:
    def __init__(self):
        self.prozess = None
        self.ordner = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.MUSIK_ORDNER)

    def laeuft(self):
        return self.prozess is not None and self.prozess.poll() is None

    def an(self):
        """Startet die Musik und gibt einen Antwortsatz zurück."""
        if self.laeuft():
            return "Die Musik läuft schon."
        programm = next((p for p in PROGRAMME if shutil.which(p[0])), None)
        if not programm:
            return "Es ist kein Abspielprogramm installiert."
        if config.RADIO_URL:
            befehl = programm[2] + [config.RADIO_URL]
            antwort = "Radio läuft."
        else:
            dateien = sorted(glob.glob(os.path.join(self.ordner, "*.mp3")))
            if not dateien:
                return "Im Musikordner liegen keine MP3-Dateien."
            befehl = programm[1] + dateien
            antwort = "Musik läuft."
        try:
            self.prozess = subprocess.Popen(befehl, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as fehler:
            print("[Musik] Start fehlgeschlagen: {}".format(fehler))
            return "Die Musik lässt sich nicht starten."
        return antwort

    def aus(self):
        if self.laeuft():
            self.prozess.terminate()
            try:
                self.prozess.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.prozess.kill()
        self.prozess = None
