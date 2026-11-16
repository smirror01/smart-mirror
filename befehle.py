"""Versteht gesprochene Befehle und baut die Antwort.

Die Spracherkennung liefert den Satz als kleingeschriebenen Text ohne
Satzzeichen, z. B. "wie warm ist es". Hier wird nach Schlüsselwörtern
gesucht. Eigene Befehle kannst du in antworte() ergänzen.

Zum Ausprobieren ohne Mikrofon:  python3 befehle.py
"""

import datetime
import random
import time

import abfahrten
import config
import kalender
import sprueche
import wetter
import zeitgeber

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

WITZE = [
    "Was macht ein Pirat am Computer? Er drückt die Enter-Taste.",
    "Warum können Geister so schlecht lügen? Weil man durch sie hindurchsehen kann.",
    "Ich wollte dir einen Spiegelwitz erzählen, aber der fällt immer auf mich zurück.",
    "Was sagt ein großer Stift zum kleinen Stift? Wachs mal, Stift.",
]

HILFE = ("Frag mich nach Uhrzeit, Datum, Wetter, Temperatur, Terminen, Nachrichten "
         "oder der nächsten Bahn. Ich kann einen Timer oder Wecker stellen, "
         "das Licht und die Musik schalten und einen Witz erzählen.")

UNBEKANNT = "Das habe ich nicht verstanden. Sag Hilfe, um zu hören, was ich kann."
KEIN_WERT = "Der Sensor liefert gerade keinen Wert."


# ---------- kleine Helfer, die auch die Anzeige benutzt ----------

def zahl(wert):
    """21.0 -> '21', 21.5 -> '21,5' (deutsche Schreibweise)."""
    gerundet = round(wert, 1)
    if gerundet == int(gerundet):
        return str(int(gerundet))
    return str(gerundet).replace(".", ",")


def datum_text(jetzt=None):
    jetzt = jetzt or datetime.datetime.now()
    return "{}, {}. {} {}".format(WOCHENTAGE[jetzt.weekday()], jetzt.day,
                                  MONATE[jetzt.month - 1], jetzt.year)


def gruss(jetzt=None):
    stunde = (jetzt or datetime.datetime.now()).hour
    if 5 <= stunde < 11:
        return "Guten Morgen!"
    if 11 <= stunde < 18:
        return "Guten Tag!"
    if 18 <= stunde < 23:
        return "Guten Abend!"
    return "Gute Nacht!"


def countdowns(heute=None):
    """Die Countdowns aus config.py als Sätze, der nächste zuerst."""
    heute = heute or datetime.date.today()
    liste = []
    for name, datum in config.COUNTDOWNS:
        try:
            tage = (datetime.datetime.strptime(datum, "%Y-%m-%d").date() - heute).days
        except ValueError:
            print("[Countdown] Datum '{}' bitte als Jahr-Monat-Tag schreiben.".format(datum))
            continue
        if tage >= 0:
            liste.append((tage, name))
    saetze = []
    for tage, name in sorted(liste):
        if tage == 0:
            saetze.append("Heute ist {}".format(name))
        elif tage == 1:
            saetze.append("Morgen ist {}".format(name))
        else:
            saetze.append("Noch {} Tage bis {}".format(tage, name))
    return saetze


def lueften_noetig(zustand):
    return zustand.feuchte is not None and zustand.feuchte >= config.LUEFTEN_AB_PROZENT


def _enthaelt(text, *teile):
    """True, wenn einer der Teile irgendwo im Text vorkommt."""
    return any(teil in text for teil in teile)


# ---------- die eigentliche Befehlserkennung ----------

def antworte(text, zustand):
    """Gibt (Antwort, Aktion) zurück.

    Aktion ist None oder ein Paar (Name, Wert), das spiegel.py ausführt:
    ("licht", True/False), ("ansicht", None), ("timer", Sekunden), ("timer_stopp", None),
    ("wecker", "07:30"), ("wecker_aus", None), ("musik", True/False),
    ("stopp", None), ("ki", Frage)
    """
    text = text.lower().strip()
    woerter = text.split()
    jetzt = datetime.datetime.now()
    aus_gesagt = "aus" in woerter or _enthaelt(text, "ausschalten", "ausmachen", "stopp", "stop",
                                               "abbrechen", "lösch", "beende")

    # Klingelt gerade etwas? Dann beendet fast jedes Wort das Klingeln.
    if zustand.klingelt and (aus_gesagt or _enthaelt(text, "ruhe", "danke", "still", "okay")):
        return "Okay.", ("stopp", None)

    if _enthaelt(text, "hilfe", "was kannst du"):
        return HILFE, None

    # ---- Timer ----
    timer_laeuft = zustand.timer_ende is not None
    if "timer" in text or (timer_laeuft and "wie lange" in text and "bis" not in woerter):
        if aus_gesagt:
            return ("Timer gestoppt." if timer_laeuft else "Es läuft kein Timer."), ("timer_stopp", None)
        dauer = zeitgeber.lies_dauer(text)
        if dauer:
            return "Timer auf {} gestellt.".format(zeitgeber.dauer_text(dauer)), ("timer", dauer)
        if timer_laeuft:
            rest = max(0, zustand.timer_ende - time.time())
            return "Der Timer läuft noch {}.".format(zeitgeber.dauer_text(rest)), None
        return "Wie lange? Sag zum Beispiel: Timer fünf Minuten.", None

    # ---- Wecker ----
    if _enthaelt(text, "wecker", "weck mich", "wecke mich"):
        if aus_gesagt:
            return "Wecker ist aus.", ("wecker_aus", None)
        uhrzeit = zeitgeber.lies_uhrzeit(text)
        if uhrzeit:
            return ("Wecker auf {} gestellt.".format(zeitgeber.uhrzeit_text(uhrzeit)),
                    ("wecker", uhrzeit))
        if zustand.wecker:
            return "Der Wecker steht auf {}.".format(zeitgeber.uhrzeit_text(zustand.wecker)), None
        return "Es ist kein Wecker gestellt. Sag zum Beispiel: Wecker auf sieben Uhr dreißig.", None

    # ---- Musik ----
    if _enthaelt(text, "musik", "radio"):
        if aus_gesagt:
            return "Musik ist aus.", ("musik", False)
        return "Musik läuft.", ("musik", True)   # spiegel.py ersetzt den Satz, falls es nicht klappt

    # ---- Licht ----
    if _enthaelt(text, "licht", "lampe"):
        if config.PORT_LICHT is None:
            return "Es ist kein Licht angeschlossen.", None
        an = "an" in woerter or "ein" in woerter or _enthaelt(text, "anschalten", "einschalten", "anmachen")
        if not an and not aus_gesagt:      # nur "Licht" gesagt: umschalten
            an = not zustand.licht
        if an and not aus_gesagt:
            return "Licht ist an.", ("licht", True)
        return "Licht ist aus.", ("licht", False)

    if _enthaelt(text, "ansicht", "wechsel", "umschalten"):
        return "Ansicht gewechselt.", ("ansicht", None)

    # ---- Wetter und Kleidung ----
    if _enthaelt(text, "anziehen", "jacke", "schirm", "kleidung"):
        tipp = wetter.kleidungstipp(zustand.wetter)
        return (tipp + "." if tipp else "Ich habe gerade keine Wetterdaten."), None

    wetterfrage = _enthaelt(text, "wetter", "draußen", "draussen", "regen", "regnet", "schnee", "schneit")
    if wetterfrage and "morgen" in woerter and not _enthaelt(text, "guten morgen", "heute morgen"):
        morgen = zustand.wetter and zustand.wetter.get("morgen")
        if not morgen:
            return "Ich habe gerade keine Vorhersage für morgen.", None
        satz = "Morgen in {} zwischen {} und {} Grad".format(
            config.ORT_NAME, zahl(morgen["minimum"]), zahl(morgen["maximum"]))
        if morgen["text"]:
            satz += ", " + morgen["text"]
        return satz + ".", None

    if wetterfrage:
        daten = zustand.wetter
        if not daten:
            return "Ich habe gerade keine Wetterdaten.", None
        return ("In {} sind es {} Grad, {}. Heute zwischen {} und {} Grad.".format(
            config.ORT_NAME, zahl(daten["temperatur"]), daten["text"],
            zahl(daten["minimum"]), zahl(daten["maximum"])), None)

    # ---- Raumklima ----
    if _enthaelt(text, "feucht", "lüften"):
        if zustand.feuchte is None:
            return KEIN_WERT, None
        satz = "Die Luftfeuchtigkeit beträgt {} Prozent.".format(zahl(zustand.feuchte))
        if lueften_noetig(zustand):
            satz += " Du solltest lüften."
        elif "lüften" in text:
            satz += " Lüften ist nicht nötig."
        return satz, None

    if _enthaelt(text, "warm", "kalt", "temperatur", "grad"):
        if zustand.temperatur is None:
            return KEIN_WERT, None
        return "Im Raum sind es {} Grad.".format(zahl(zustand.temperatur)), None

    if _enthaelt(text, "abstand", "entfernung", "entfernt"):
        if zustand.abstand is None:
            return KEIN_WERT, None
        return "Du stehst {} Zentimeter entfernt.".format(zustand.abstand), None

    # ---- Termine ----
    if _enthaelt(text, "termin", "kalender", "steht an", "steht heute", "was habe ich"):
        if not config.KALENDER_URL:
            return "Es ist kein Kalender eingerichtet.", None
        if zustand.termine is None:
            return "Ich kann den Kalender gerade nicht lesen.", None
        if not zustand.termine:
            return "In den nächsten Tagen steht nichts an.", None
        saetze = []
        for termin in zustand.termine[:3]:
            start = termin["start"]
            abstand = (start.date() - jetzt.date()).days
            wann = ("Heute" if abstand == 0 else "Morgen" if abstand == 1
                    else "Am " + WOCHENTAGE[start.weekday()])
            if not termin["ganztags"]:
                wann += " um " + zeitgeber.uhrzeit_text(start.strftime("%H:%M"))
            saetze.append("{}: {}.".format(wann, termin["titel"]))
        return " ".join(saetze), None

    # ---- Nachrichten ----
    if _enthaelt(text, "nachricht", "neues", "schlagzeile", "news"):
        if not zustand.nachrichten:
            return "Ich habe gerade keine Nachrichten.", None
        return " ".join(titel.rstrip(".!?") + "." for titel in zustand.nachrichten[:3]), None

    # ---- Bus und Bahn ----
    if _enthaelt(text, "abfahrt", "fährt", "haltestelle") or any(
            wort in woerter for wort in ("bahn", "bus", "zug", "tram")):
        fahrten = abfahrten.naechste(zustand.abfahrten, 2, jetzt)
        if not fahrten:
            return "Ich habe gerade keine Abfahrten.", None
        saetze = []
        for linie, ziel, minuten in fahrten:
            wann = "jetzt" if minuten == 0 else "in {} {}".format(
                minuten, "Minute" if minuten == 1 else "Minuten")
            saetze.append("{} Richtung {} {}".format(linie, ziel, wann))
        return " und ".join(saetze) + ".", None

    # ---- Countdown und Spruch ----
    if _enthaelt(text, "countdown", "wie viele tage", "wie lange noch", "tage bis"):
        saetze = countdowns(jetzt.date())
        if not saetze:
            return "Es ist kein Countdown eingetragen.", None
        return ". ".join(saetze[:2]) + ".", None

    if _enthaelt(text, "spruch", "zitat", "weisheit"):
        return sprueche.spruch_des_tages(jetzt.date()), None

    # ---- Uhrzeit und Datum ----
    if _enthaelt(text, "spät", "uhr"):
        if jetzt.minute == 0:
            return "Es ist {} Uhr.".format(jetzt.hour), None
        return "Es ist {} Uhr {}.".format(jetzt.hour, jetzt.minute), None

    if _enthaelt(text, "datum", "wochentag", "welcher tag", "welchen tag", "wievielte"):
        return "Heute ist {}, der {}. {}.".format(
            WOCHENTAGE[jetzt.weekday()], jetzt.day, MONATE[jetzt.month - 1]), None

    # ---- Plaudern ----
    if _enthaelt(text, "witz"):
        return random.choice(WITZE), None

    if _enthaelt(text, "danke"):
        return "Gern geschehen.", None

    if _enthaelt(text, "wie geht"):
        return "Mir geht es blendend. Ich sehe ja auch gut aus.", None

    if _enthaelt(text, "hallo", "guten morgen", "guten tag", "guten abend") or "hi" in woerter:
        return gruss(jetzt), None

    # Nichts erkannt: spiegel.py fragt die KI, falls sie eingerichtet ist
    return UNBEKANNT, ("ki", text)


if __name__ == "__main__":
    # Testmodus: Befehle eintippen statt sprechen
    from sensoren import Zustand

    test = Zustand()
    test.temperatur, test.feuchte, test.abstand = 21.5, 45.0, 60
    test.wetter = {"temperatur": 8.3, "text": "bedeckt", "code": 3, "tagescode": 61,
                   "minimum": 4.0, "maximum": 9.6, "regen_prozent": 70,
                   "morgen": {"minimum": 2.0, "maximum": 7.5, "text": "leichter Regen",
                              "code": 61, "regen_prozent": 80}}
    test.nachrichten = ["Beispiel-Schlagzeile eins", "Beispiel-Schlagzeile zwei"]
    print("Befehl eintippen (leere Zeile beendet):")
    while True:
        try:
            eingabe = input("> ")
        except EOFError:
            break
        if not eingabe.strip():
            break
        antwort, aktion = antworte(eingabe, test)
        if aktion and aktion[0] == "timer":
            test.timer_ende = time.time() + aktion[1]
        elif aktion and aktion[0] == "wecker":
            test.wecker = aktion[1]
        print(antwort + ("   [Aktion: {}]".format(aktion[0]) if aktion else ""))
