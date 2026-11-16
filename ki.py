"""Beantwortet freie Fragen mit einem KI-Sprachmodell (Claude von Anthropic).

Wird nur benutzt, wenn der Spiegel einen Befehl nicht kennt UND in der Datei
config_geheim.py ein Schlüssel steht. Jede Frage geht dann ins Internet und
kostet einen kleinen Betrag. Ohne Schlüssel bleibt alles auf dem Pi.
"""

import json

import config
from netz import hole

ADRESSE = "https://api.anthropic.com/v1/messages"
ANWEISUNG = ("Du bist die Stimme eines Smart Mirrors im Flur. Antworte auf Deutsch "
             "in höchstens zwei kurzen Sätzen. Die Antwort wird vorgelesen, benutze "
             "deshalb keine Listen, Sonderzeichen oder Formatierung.")


def schluessel():
    return getattr(config, "KI_SCHLUESSEL", "") or ""


def verfuegbar():
    return bool(config.KI_AKTIV and schluessel())


def frage(text):
    """Schickt die Frage an die KI und gibt die Antwort als Text zurück."""
    anfrage = json.dumps({
        "model": config.KI_MODELL,
        "max_tokens": 200,
        "system": ANWEISUNG,
        "messages": [{"role": "user", "content": text}],
    }).encode("utf-8")
    kopf = {
        "x-api-key": schluessel(),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    antwort = json.loads(hole(ADRESSE, kopf=kopf, daten=anfrage, timeout=30).decode("utf-8"))
    teile = [block.get("text", "") for block in antwort.get("content", [])
             if block.get("type") == "text"]
    return " ".join(" ".join(teile).split()) or "Dazu fällt mir nichts ein."
