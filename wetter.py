"""Holt das Wetter für heute und morgen von open-meteo.com (kostenlos, ohne Konto)."""

import json
import urllib.parse

import config
from netz import hole

ADRESSE = "https://api.open-meteo.com/v1/forecast"

# Wettercodes nach WMO-Standard, wie open-meteo sie liefert
BESCHREIBUNG = {
    0: "klar", 1: "überwiegend klar", 2: "teils bewölkt", 3: "bedeckt",
    45: "Nebel", 48: "Reifnebel",
    51: "leichter Nieselregen", 53: "Nieselregen", 55: "starker Nieselregen",
    56: "gefrierender Nieselregen", 57: "gefrierender Nieselregen",
    61: "leichter Regen", 63: "Regen", 65: "starker Regen",
    66: "gefrierender Regen", 67: "gefrierender Regen",
    71: "leichter Schneefall", 73: "Schneefall", 75: "starker Schneefall",
    77: "Schneegriesel",
    80: "leichte Regenschauer", 81: "Regenschauer", 82: "heftige Regenschauer",
    85: "leichte Schneeschauer", 86: "Schneeschauer",
    95: "Gewitter", 96: "Gewitter mit Hagel", 97: "schweres Gewitter",
    99: "Gewitter mit Hagel",
}
REGEN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 97, 99}
SCHNEE_CODES = {71, 73, 75, 77, 85, 86}


def lade():
    """Gibt ein Wörterbuch mit dem Wetter von heute und morgen zurück."""
    parameter = urllib.parse.urlencode({
        "latitude": config.BREITENGRAD,
        "longitude": config.LAENGENGRAD,
        "current": "temperature_2m,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 2,
    })
    return werte_aus(json.loads(hole(ADRESSE + "?" + parameter).decode("utf-8")))


def werte_aus(daten):
    """Zieht die benötigten Werte aus der Antwort von open-meteo."""
    aktuell = daten["current"]
    tage = daten["daily"]

    def tag(nummer):
        regen = (tage.get("precipitation_probability_max") or [None, None])[nummer]
        code = (tage.get("weather_code") or [None, None])[nummer]
        return {
            "minimum": float(tage["temperature_2m_min"][nummer]),
            "maximum": float(tage["temperature_2m_max"][nummer]),
            "code": code,
            "text": BESCHREIBUNG.get(code, ""),
            "regen_prozent": regen,
        }

    heute = tag(0)
    wetter = {
        "temperatur": float(aktuell["temperature_2m"]),
        "code": aktuell["weather_code"],
        "text": BESCHREIBUNG.get(aktuell["weather_code"], "unbekannt"),
        "minimum": heute["minimum"],
        "maximum": heute["maximum"],
        "regen_prozent": heute["regen_prozent"],
        "tagescode": heute["code"],
        "morgen": tag(1) if len(tage["temperature_2m_max"]) > 1 else None,
    }
    return wetter


def kleidungstipp(wetter):
    """Macht aus dem Wetter von heute einen kurzen Tipp, was man anziehen sollte."""
    if not wetter:
        return ""
    warm = wetter["maximum"]
    if warm < 3:
        tipp = "Dicke Jacke, Mütze und Handschuhe"
    elif warm < 11:
        tipp = "Warme Jacke anziehen"
    elif warm < 17:
        tipp = "Leichte Jacke oder Pullover"
    elif warm < 25:
        tipp = "T-Shirt reicht"
    else:
        tipp = "Leichte Kleidung, es wird heiß"

    codes = {wetter.get("code"), wetter.get("tagescode")}
    regen = wetter.get("regen_prozent")
    if codes & SCHNEE_CODES:
        tipp += ", feste Schuhe für den Schnee"
    elif codes & REGEN_CODES or (regen is not None and regen >= 50):
        tipp += ", Regenschirm mitnehmen"
    return tipp
