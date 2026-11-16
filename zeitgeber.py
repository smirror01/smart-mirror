"""Versteht gesprochene Zeitangaben für Timer und Wecker.

Die Spracherkennung liefert Zahlen als Wörter ("fünf minuten",
"sieben uhr dreißig"). Hier werden daraus Sekunden oder eine Uhrzeit.
"""

EINER = {
    "null": 0, "ein": 1, "eine": 1, "einen": 1, "einer": 1, "eins": 1, "zwei": 2, "zwo": 2,
    "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
    "zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15,
    "sechzehn": 16, "siebzehn": 17, "achtzehn": 18, "neunzehn": 19,
}
ZEHNER = {
    "zwanzig": 20, "dreißig": 30, "dreissig": 30, "vierzig": 40, "fünfzig": 50,
    "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90,
}
ARTIKEL = {"ein", "eine", "einen", "einer"}
EINHEITEN = {
    "sekunde": 1, "sekunden": 1, "minute": 60, "minuten": 60, "stunde": 3600, "stunden": 3600,
}
BRUCH = {"halbe": 0.5, "halben": 0.5, "anderthalb": 1.5, "eineinhalb": 1.5}


def wort_zu_zahl(wort):
    """'fünf' -> 5, 'fünfundzwanzig' -> 25, '12' -> 12, sonst None."""
    if wort.isdigit():
        return int(wort)
    if wort in EINER:
        return EINER[wort]
    if wort in ZEHNER:
        return ZEHNER[wort]
    if wort in ("hundert", "einhundert"):
        return 100
    for zehner, wert in ZEHNER.items():
        ende = "und" + zehner
        if wort.endswith(ende) and EINER.get(wort[:-len(ende)], 99) < 10:
            return EINER[wort[:-len(ende)]] + wert
    return None


def _zerlege(text):
    """Macht aus dem Satz eine Liste aus Wörtern und Zahlen.

    Zahlen werden zu (Zahl, war_Artikel). Auch getrennt gesprochene Zahlen
    wie "fünf und zwanzig" werden zusammengesetzt.
    """
    woerter = text.lower().replace(":", " ").replace(",", " ").split()
    teile = []
    stelle = 0
    while stelle < len(woerter):
        wort = woerter[stelle]
        if (stelle + 2 < len(woerter) and woerter[stelle + 1] == "und"
                and EINER.get(wort, 99) < 10 and woerter[stelle + 2] in ZEHNER):
            teile.append((EINER[wort] + ZEHNER[woerter[stelle + 2]], False))
            stelle += 3
            continue
        if wort in BRUCH:
            teile.append((BRUCH[wort], False))
        else:
            zahl = wort_zu_zahl(wort)
            teile.append(wort if zahl is None else (zahl, wort in ARTIKEL))
        stelle += 1
    return teile


def lies_dauer(text):
    """'timer fünf minuten' -> 300 Sekunden. None, wenn keine Dauer vorkommt."""
    text = text.lower()
    if "dreiviertelstunde" in text:
        return 2700
    if "viertelstunde" in text or "viertel stunde" in text:
        return 900
    teile = _zerlege(text)
    sekunden = 0
    gefunden = False
    stelle = 0
    while stelle < len(teile):
        teil = teile[stelle]
        danach = teile[stelle + 1] if stelle + 1 < len(teile) else None
        if isinstance(teil, tuple) and danach in EINHEITEN:
            einheit = EINHEITEN[danach]
            sekunden += teil[0] * einheit
            gefunden = True
            stelle += 2
            # "zwei minuten dreißig" -> die 30 sind Sekunden
            rest = teile[stelle] if stelle < len(teile) else None
            nach_rest = teile[stelle + 1] if stelle + 1 < len(teile) else None
            if isinstance(rest, tuple) and nach_rest not in EINHEITEN and einheit > 1:
                sekunden += rest[0] * einheit // 60
                stelle += 1
            continue
        stelle += 1
    if gefunden:
        return int(sekunden) or None
    # Keine Einheit genannt: die letzte Zahl gilt als Minuten ("timer fünf")
    zahlen = [teil[0] for teil in teile if isinstance(teil, tuple) and not teil[1]]
    if zahlen and zahlen[-1] >= 1:
        return int(zahlen[-1] * 60)
    return None


def lies_uhrzeit(text):
    """'wecker auf sieben uhr dreißig' -> '07:30'. None, wenn keine Uhrzeit vorkommt."""
    teile = _zerlege(text)

    def zahl(stelle):
        if 0 <= stelle < len(teile) and isinstance(teile[stelle], tuple):
            wert = teile[stelle][0]
            if wert == int(wert):
                return int(wert)
        return None

    stunde = minute = None
    if "uhr" in teile:
        ort = teile.index("uhr")
        stunde, minute = zahl(ort - 1), zahl(ort + 1) or 0
    elif "halb" in teile:                                   # halb acht -> 7:30
        folgende = zahl(teile.index("halb") + 1)
        if folgende is not None:
            stunde, minute = (folgende - 1) % 24, 30
    elif "viertel" in teile:                                # viertel nach/vor acht
        ort = teile.index("viertel")
        richtung = teile[ort + 1] if ort + 1 < len(teile) else None
        folgende = zahl(ort + 2)
        if folgende is not None and richtung == "nach":
            stunde, minute = folgende, 15
        elif folgende is not None and richtung == "vor":
            stunde, minute = (folgende - 1) % 24, 45
    else:                                                   # "sieben dreißig" oder "um sieben"
        zahlen = [t[0] for t in teile if isinstance(t, tuple) and not t[1] and t[0] == int(t[0])]
        if zahlen:
            stunde = int(zahlen[0])
            minute = int(zahlen[1]) if len(zahlen) > 1 else 0

    if stunde is None or not (0 <= stunde <= 23 and 0 <= minute <= 59):
        return None
    return "{:02d}:{:02d}".format(stunde, minute)


def dauer_text(sekunden):
    """330 -> '5 Minuten 30 Sekunden' (zum Vorlesen)."""
    sekunden = int(round(sekunden))
    stunden, rest = divmod(sekunden, 3600)
    minuten, sek = divmod(rest, 60)
    teile = []
    if stunden:
        teile.append("{} {}".format(stunden, "Stunde" if stunden == 1 else "Stunden"))
    if minuten:
        teile.append("{} {}".format(minuten, "Minute" if minuten == 1 else "Minuten"))
    if sek or not teile:
        teile.append("{} {}".format(sek, "Sekunde" if sek == 1 else "Sekunden"))
    return " ".join(teile)


def rest_anzeige(sekunden):
    """272 -> '04:32' (für die Anzeige)."""
    sekunden = max(0, int(sekunden + 0.999))
    stunden, rest = divmod(sekunden, 3600)
    minuten, sek = divmod(rest, 60)
    if stunden:
        return "{}:{:02d}:{:02d}".format(stunden, minuten, sek)
    return "{:02d}:{:02d}".format(minuten, sek)


def uhrzeit_text(uhrzeit):
    """'07:30' -> '7 Uhr 30' (zum Vorlesen)."""
    stunde, minute = int(uhrzeit[:2]), int(uhrzeit[3:])
    return "{} Uhr {}".format(stunde, minute) if minute else "{} Uhr".format(stunde)
