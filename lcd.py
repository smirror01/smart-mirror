"""Steuert das kleine Grove-LCD mit farbigem Hintergrundlicht (I2C-Buchse).

Das Display hat 2 Zeilen mit je 16 Zeichen und kann keine Umlaute.
"""

import time

ADRESSE_FARBE = 0x62
ADRESSE_TEXT = 0x3e


class Lcd:
    def __init__(self):
        """Löst einen Fehler aus, wenn I2C auf diesem Rechner nicht verfügbar ist."""
        try:
            import smbus
        except ImportError:
            import smbus2 as smbus
        self.bus = smbus.SMBus(1)
        self.text = None
        self.farbe = None

    def zeige(self, text, farbe):
        """Schreibt Text (Zeilen mit \\n trennen) und setzt die Farbe (rot, grün, blau)."""
        if farbe != self.farbe:
            rot, gruen, blau = farbe
            self.farbe = farbe
            try:
                self.bus.write_byte_data(ADRESSE_FARBE, 0, 0)
                self.bus.write_byte_data(ADRESSE_FARBE, 1, 0)
                self.bus.write_byte_data(ADRESSE_FARBE, 0x08, 0xaa)
                self.bus.write_byte_data(ADRESSE_FARBE, 4, rot)
                self.bus.write_byte_data(ADRESSE_FARBE, 3, gruen)
                self.bus.write_byte_data(ADRESSE_FARBE, 2, blau)
            except OSError:
                pass    # neuere Displays haben eine andere Farbadresse: dann nur Text
        if text != self.text:
            self._befehl(0x01)              # Anzeige löschen
            time.sleep(0.05)
            self._befehl(0x08 | 0x04)       # Anzeige an, kein Cursor
            self._befehl(0x28)              # zwei Zeilen
            time.sleep(0.05)
            for nummer, zeile in enumerate(text.split("\n")[:2]):
                if nummer == 1:
                    self._befehl(0xc0)      # Sprung in die zweite Zeile
                for zeichen in zeile[:16]:
                    code = ord(zeichen) if ord(zeichen) < 128 else ord("?")
                    self.bus.write_byte_data(ADRESSE_TEXT, 0x40, code)
            self.text = text

    def aus(self):
        self.zeige("", (0, 0, 0))

    def _befehl(self, befehl):
        self.bus.write_byte_data(ADRESSE_TEXT, 0x80, befehl)
