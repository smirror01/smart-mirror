"""Holt Schlagzeilen aus einem RSS-Feed (Standard: tagesschau.de)."""

import xml.etree.ElementTree as ET

import config
from netz import hole


def lade():
    """Gibt eine Liste mit den neuesten Schlagzeilen zurück."""
    return schlagzeilen_aus(hole(config.NACHRICHTEN_URL))


def schlagzeilen_aus(xml_daten):
    wurzel = ET.fromstring(xml_daten)
    titel = []
    for eintrag in wurzel.iter("item"):
        text = (eintrag.findtext("title") or "").strip()
        if text and text not in titel:
            titel.append(" ".join(text.split()))
        if len(titel) >= config.NACHRICHTEN_ANZAHL:
            break
    return titel
