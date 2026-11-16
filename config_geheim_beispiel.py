"""Vorlage für geheime Werte.

So benutzt du sie:
1. Diese Datei kopieren und die Kopie config_geheim.py nennen.
2. Die Werte unten eintragen.

config_geheim.py wird NICHT zu GitHub hochgeladen (steht in .gitignore).
Bring sie per USB-Stick auf den Pi. Was hier steht, ersetzt die Werte aus config.py.
"""

# Schlüssel für die KI-Antworten (bekommst du auf https://platform.claude.com/settings/keys).
# Leer lassen = keine KI, der Spiegel beantwortet dann nur die festen Befehle.
KI_SCHLUESSEL = ""

# Private Adresse deines Kalenders im ICS-Format. Wer sie kennt, kann deine Termine lesen,
# deshalb gehört sie hierher und nicht in config.py. Zum Benutzen das # entfernen.
# KALENDER_URL = "https://calendar.google.com/calendar/ical/.../basic.ics"
