"""Liest Termine aus einem Kalender im ICS-Format (Google, Uni, Nextcloud ...).

Unterstützt einzelne Termine, ganztägige Termine und einfache Serien
(täglich, wöchentlich, monatlich am selben Tag, jährlich). Ausgefallenere
Serien wie "jeder zweite Dienstag im Monat" werden nur einmal angezeigt.
"""

import calendar
import datetime

import config
from netz import hole

WOCHENTAGE_ICS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def lade():
    """Gibt die Liste der kommenden Termine zurück."""
    quelle = config.KALENDER_URL
    if quelle.startswith("webcal://"):
        quelle = "https://" + quelle[len("webcal://"):]
    if quelle.startswith("http://") or quelle.startswith("https://"):
        text = hole(quelle, timeout=20).decode("utf-8", "replace")
    else:
        with open(quelle, encoding="utf-8") as datei:
            text = datei.read()
    return kommende(lies_termine(text), datetime.datetime.now(),
                    config.KALENDER_TAGE, config.KALENDER_ANZAHL)


# ---------- Datei lesen ----------

def _zeilen(text):
    """Lange Zeilen sind in ICS-Dateien umbrochen. Hier werden sie wieder zusammengesetzt."""
    zeilen = []
    for zeile in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if zeile[:1] in (" ", "\t") and zeilen:
            zeilen[-1] += zeile[1:]
        else:
            zeilen.append(zeile)
    return zeilen


def _zeit(wert):
    """'20261116T140000Z' oder '20261116' -> (Zeitpunkt in Ortszeit, ganztägig?)"""
    wert = wert.strip()
    if len(wert) == 8:
        return datetime.datetime.strptime(wert, "%Y%m%d"), True
    zeit = datetime.datetime.strptime(wert[:15], "%Y%m%dT%H%M%S")
    if wert.endswith("Z"):      # Weltzeit in Ortszeit umrechnen
        zeit = datetime.datetime.fromtimestamp(calendar.timegm(zeit.timetuple()))
    return zeit, False


def _klartext(wert):
    return (wert.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\").strip())


def lies_termine(text):
    termine = []
    aktuell = None
    for zeile in _zeilen(text):
        if zeile == "BEGIN:VEVENT":
            aktuell = {"titel": "(ohne Titel)", "start": None, "ganztags": False,
                       "regel": None, "ausnahmen": set()}
        elif zeile == "END:VEVENT":
            if aktuell and aktuell["start"]:
                termine.append(aktuell)
            aktuell = None
        elif aktuell is not None and ":" in zeile:
            kopf, wert = zeile.split(":", 1)
            name = kopf.split(";")[0].upper()
            try:
                if name == "SUMMARY":
                    aktuell["titel"] = _klartext(wert) or aktuell["titel"]
                elif name == "DTSTART":
                    aktuell["start"], aktuell["ganztags"] = _zeit(wert)
                elif name == "RRULE":
                    aktuell["regel"] = dict(
                        teil.split("=", 1) for teil in wert.upper().split(";") if "=" in teil)
                elif name == "EXDATE":
                    for einzeln in wert.split(","):
                        aktuell["ausnahmen"].add(_zeit(einzeln)[0].date())
            except ValueError:
                pass    # unlesbare Zeile überspringen
    return termine


# ---------- Serien auflösen ----------

def _passt(termin, tag):
    """Findet die Serie des Termins an diesem Tag statt?"""
    regel = termin["regel"]
    start = termin["start"].date()
    schritt = int(regel.get("INTERVAL", "1") or 1)
    art = regel.get("FREQ")
    if art == "DAILY":
        return (tag - start).days % schritt == 0
    if art == "WEEKLY":
        tage = regel.get("BYDAY", WOCHENTAGE_ICS[start.weekday()]).split(",")
        if WOCHENTAGE_ICS[tag.weekday()] not in tage:
            return False
        montag_start = start - datetime.timedelta(days=start.weekday())
        montag_tag = tag - datetime.timedelta(days=tag.weekday())
        return ((montag_tag - montag_start).days // 7) % schritt == 0
    if art == "MONTHLY" and "BYDAY" not in regel:
        monate = (tag.year - start.year) * 12 + tag.month - start.month
        return tag.day == start.day and monate % schritt == 0
    if art == "YEARLY":
        return (tag.month, tag.day) == (start.month, start.day) and (tag.year - start.year) % schritt == 0
    return False


def _vorkommen(termin, von, bis):
    """Alle Tage zwischen von und bis, an denen der Termin stattfindet."""
    start = termin["start"].date()
    regel = termin["regel"]
    if not regel or regel.get("FREQ") not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY") \
            or (regel.get("FREQ") == "MONTHLY" and "BYDAY" in regel):
        return [start] if von <= start <= bis else []

    ende = bis
    if regel.get("UNTIL"):
        try:
            ende = min(bis, datetime.datetime.strptime(regel["UNTIL"][:8], "%Y%m%d").date())
        except ValueError:
            pass
    hoechstens = int(regel["COUNT"]) if regel.get("COUNT", "").isdigit() else None

    # Ohne COUNT reicht es, ab heute zu suchen. Mit COUNT muss von Anfang an gezählt werden.
    tag = start if hoechstens else max(start, von)
    gezaehlt = 0
    tage = []
    while tag <= ende:
        if _passt(termin, tag):
            gezaehlt += 1
            if hoechstens and gezaehlt > hoechstens:
                break
            if tag >= von and tag not in termin["ausnahmen"]:
                tage.append(tag)
        tag += datetime.timedelta(days=1)
    return tage


def kommende(termine, jetzt, tage, anzahl):
    """Die nächsten Termine als Liste von {"start", "ganztags", "titel"}, sortiert."""
    heute = jetzt.date()
    bis = heute + datetime.timedelta(days=tage)
    liste = []
    for termin in termine:
        for tag in _vorkommen(termin, heute, bis):
            start = datetime.datetime.combine(tag, termin["start"].time())
            if termin["ganztags"] or start >= jetzt:
                liste.append({"start": start, "ganztags": termin["ganztags"],
                              "titel": termin["titel"]})
    liste.sort(key=lambda t: (t["start"].date(), not t["ganztags"], t["start"]))
    return liste[:anzahl]


def tag_text(termin, jetzt=None):
    """'Heute 14:00', 'Morgen', 'Mi 18.11. 09:00'"""
    jetzt = jetzt or datetime.datetime.now()
    start = termin["start"]
    abstand = (start.date() - jetzt.date()).days
    if abstand == 0:
        tag = "Heute"
    elif abstand == 1:
        tag = "Morgen"
    else:
        tag = "{} {}.{}.".format(WOCHENTAGE_KURZ[start.weekday()], start.day, start.month)
    if termin["ganztags"]:
        return tag
    return "{} {}".format(tag, start.strftime("%H:%M"))
