"""Nächste Abfahrten von Bus und Bahn an einer Haltestelle in Berlin/Brandenburg.

Benutzt die kostenlose, inoffizielle Schnittstelle v6.bvg.transport.rest.
Sie wird von Freiwilligen betrieben und ist manchmal nicht erreichbar.
Dann blendet der Spiegel die Abfahrten einfach aus.
"""

import datetime
import json
import urllib.parse

import config
from netz import hole

BASIS = "https://v6.bvg.transport.rest"
_haltestelle = None     # (Nummer, Name), wird beim ersten Abruf gesucht


def _suche_haltestelle():
    parameter = urllib.parse.urlencode({
        "query": config.HALTESTELLE, "results": 1, "poi": "false", "addresses": "false"})
    treffer = json.loads(hole(BASIS + "/locations?" + parameter).decode("utf-8"))
    if not treffer:
        raise ValueError("Haltestelle '{}' nicht gefunden".format(config.HALTESTELLE))
    print("[Abfahrten] Haltestelle: {}".format(treffer[0]["name"]))
    return treffer[0]["id"], treffer[0]["name"]


def lade():
    """Gibt {"haltestelle": Name, "fahrten": [...]} zurück."""
    global _haltestelle
    if _haltestelle is None:
        _haltestelle = _suche_haltestelle()
    nummer, name = _haltestelle
    adresse = "{}/stops/{}/departures?results=12&duration=60".format(BASIS, nummer)
    return {"haltestelle": name,
            "fahrten": fahrten_aus(json.loads(hole(adresse).decode("utf-8")))}


def fahrten_aus(daten):
    # Je nach Version kommt eine Liste oder ein Wörterbuch mit dem Schlüssel "departures"
    liste = daten.get("departures", []) if isinstance(daten, dict) else daten
    fahrten = []
    for eintrag in liste:
        wann = eintrag.get("when") or eintrag.get("plannedWhen")
        if not wann:
            continue    # Fahrt fällt aus
        # "2026-11-16T12:20:00+01:00" -> Ortszeit, die Zeitzone am Ende wird nicht gebraucht
        zeit = datetime.datetime.strptime(wann[:19], "%Y-%m-%dT%H:%M:%S")
        fahrten.append({
            "linie": (eintrag.get("line") or {}).get("name") or "?",
            "ziel": _kuerze(eintrag.get("direction") or ""),
            "zeit": zeit,
        })
    fahrten.sort(key=lambda fahrt: fahrt["zeit"])
    return fahrten


def _kuerze(ziel):
    for vorsatz in ("S+U ", "S ", "U "):
        if ziel.startswith(vorsatz):
            ziel = ziel[len(vorsatz):]
    ziel = ziel.replace(" (Berlin)", "")
    return ziel if len(ziel) <= 24 else ziel[:23] + "…"


def naechste(abfahrten, anzahl, jetzt=None):
    """Gibt die nächsten Fahrten als Liste von (Linie, Ziel, Minuten) zurück."""
    if not abfahrten:
        return []
    jetzt = jetzt or datetime.datetime.now()
    ergebnis = []
    for fahrt in abfahrten["fahrten"]:
        minuten = int((fahrt["zeit"] - jetzt).total_seconds() // 60)
        if minuten >= 0:
            ergebnis.append((fahrt["linie"], fahrt["ziel"], minuten))
        if len(ergebnis) >= anzahl:
            break
    return ergebnis
