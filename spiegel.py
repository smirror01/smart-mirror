#!/usr/bin/env python3
"""Smart Mirror für Raspberry Pi mit GrovePi+.

Starten:            python3 spiegel.py
Im Fenster testen:  python3 spiegel.py --fenster

Tasten:  Esc = beenden, Leertaste = wie der Taster, T = Befehl eintippen,
         F11 = Vollbild an/aus, A = Anwesenheit umschalten (nur Simulation)
"""

import argparse
import datetime
import queue
import signal
import subprocess
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import simpledialog

import abfahrten
import befehle
import config
import kalender
import ki
import nachrichten
import sensoren
import sprueche
import wetter
import zeitgeber
from musik import Musik
from netz import Abruf
from sprache import Sprecher, Zuhoerer

ANSICHTEN = ["voll", "uhr", "klima"]   # Reihenfolge beim Drücken des Tasters


class Spiegel:
    def __init__(self, vollbild):
        self.zustand = sensoren.Zustand()
        self.ereignisse = queue.Queue()
        self.sensoren = sensoren.Sensoren(self.zustand, self.ereignisse)
        self.sprecher = Sprecher()
        self.musik = Musik()

        self.ansicht = 0
        self.aktiv = None           # None = noch nichts angezeigt
        self.geweckt = time.time()  # letzter Tastendruck oder Sprachbefehl
        self.meldung_bis = 0
        self.hoert_bis = 0
        self.led_an = False
        self.helligkeit = None
        self.klingelt_seit = 0
        self.wecker_geklingelt = None   # (Datum, Uhrzeit) des letzten Weckens
        self.laufzeile_nr = -1
        self.laufzeile_wechsel = 0
        self.kurve_stand = None

        self.root = tk.Tk()
        self.root.title("Smart Mirror")
        self.root.configure(bg="black")
        self.vollbild = vollbild
        if vollbild:
            self.root.attributes("-fullscreen", True)
            self.root.config(cursor="none")
            self.hoehe = self.root.winfo_screenheight()
            self.breite = self.root.winfo_screenwidth()
        else:
            self.breite, self.hoehe = 1024, 600
            self.root.geometry("{}x{}".format(self.breite, self.hoehe))
        self._baue_oberflaeche()

        self.root.bind("<Escape>", lambda e: self.beenden())
        self.root.bind("<space>", lambda e: self.ereignisse.put(("taster", None)))
        self.root.bind("<F11>", lambda e: self._vollbild_umschalten())
        for taste in ("t", "T"):
            self.root.bind(taste, lambda e: self._befehl_eintippen())
        for taste in ("a", "A"):
            self.root.bind(taste, lambda e: self._sim_anwesenheit())
        self.root.protocol("WM_DELETE_WINDOW", self.beenden)
        signal.signal(signal.SIGINT, lambda *a: self.beenden())   # Strg+C im Terminal

        self._starte_hintergrund()
        self.root.after(100, self._takt)

    def _starte_hintergrund(self):
        """Startet alles, was neben der Anzeige läuft."""
        z = self.zustand
        self.sensoren.start()
        if config.WETTER_AKTIV:
            Abruf("Wetter", wetter.lade, lambda d: setattr(z, "wetter", d), 900, 7200).start()
        if config.NACHRICHTEN_AKTIV:
            Abruf("Nachrichten", nachrichten.lade,
                  lambda d: setattr(z, "nachrichten", d), 900, 7200).start()
        if config.HALTESTELLE:
            Abruf("Abfahrten", abfahrten.lade, lambda d: setattr(z, "abfahrten", d), 60, 300).start()
        if config.KALENDER_URL:
            Abruf("Kalender", kalender.lade, lambda d: setattr(z, "termine", d), 600, 7200).start()
        if config.SPRACHE_AKTIV:
            Zuhoerer(self.ereignisse, self.sprecher).start()

    # ---------- Aufbau der Anzeige ----------

    def _baue_oberflaeche(self):
        hoehe, breite = self.hoehe, self.breite

        def schrift(anteil):
            return tkfont.Font(family=config.SCHRIFTART, size=-max(10, int(hoehe * anteil)))

        self.texte = []   # (Label, Helligkeitsfaktor) für die Schriftfarbe

        def label(eltern, schriftart, faktor=1.0, **optionen):
            neu = tk.Label(eltern, bg="black", fg="white", font=schriftart, **optionen)
            self.texte.append((neu, faktor))
            return neu

        rand = int(hoehe * 0.05)
        klein = schrift(0.032)

        # Unten in der Mitte: Laufzeile (Spruch, Schlagzeilen) und Meldungen des Assistenten
        unten = tk.Frame(self.root, bg="black")
        unten.pack(side="bottom", fill="x", pady=(0, rand))
        self.l_laufzeile = label(unten, klein, 0.55, wraplength=int(breite * 0.85), justify="center")
        self.l_laufzeile.pack()
        self.l_gehoert = label(unten, schrift(0.028), 0.55)
        self.l_gehoert.pack(pady=(int(hoehe * 0.015), 0))
        self.l_meldung = label(unten, schrift(0.045), wraplength=int(breite * 0.85), justify="center")
        self.l_meldung.pack()

        # Ansicht "voll": links Uhr, Countdown, Timer, Termine. Rechts Wetter, Raum, Abfahrten.
        voll = tk.Frame(self.root, bg="black")
        links = tk.Frame(voll, bg="black")
        links.pack(side="left", anchor="n", padx=rand, pady=(rand, 0))
        zeile = tk.Frame(links, bg="black")
        zeile.pack(anchor="w")
        self.l_zeit = label(zeile, schrift(0.17))
        self.l_zeit.pack(side="left")
        self.l_sekunden = label(zeile, schrift(0.06), 0.55)
        self.l_sekunden.pack(side="left", anchor="n", pady=int(hoehe * 0.03))
        self.l_datum = label(links, schrift(0.04), 0.7)
        self.l_datum.pack(anchor="w")
        self.l_merkzettel = label(links, klein, 0.85, justify="left")
        self.l_merkzettel.pack(anchor="w", pady=(int(hoehe * 0.025), 0))
        self.l_termine = label(links, klein, 0.7, justify="left")
        self.l_termine.pack(anchor="w", pady=(int(hoehe * 0.025), 0))

        rechts = tk.Frame(voll, bg="black")
        rechts.pack(side="right", anchor="n", padx=rand, pady=(rand, 0))
        self.l_wetter_grad = label(rechts, schrift(0.11))
        self.l_wetter_grad.pack(anchor="e")
        self.l_wetter = label(rechts, klein, 0.7, justify="right")
        self.l_wetter.pack(anchor="e")
        self.l_raum = label(rechts, klein, 0.85, justify="right")
        self.l_raum.pack(anchor="e", pady=(int(hoehe * 0.025), 0))
        self.l_abfahrten = label(rechts, klein, 0.7, justify="right")
        self.l_abfahrten.pack(anchor="e", pady=(int(hoehe * 0.025), 0))

        # Ansicht "uhr": nur eine große Uhr in der Mitte
        uhr = tk.Frame(self.root, bg="black")
        mitte = tk.Frame(uhr, bg="black")
        mitte.place(relx=0.5, rely=0.45, anchor="center")
        self.l_zeit_gross = label(mitte, schrift(0.32))
        self.l_zeit_gross.pack()
        self.l_datum_gross = label(mitte, schrift(0.05), 0.7)
        self.l_datum_gross.pack()

        # Ansicht "klima": Raumklima groß und Temperaturverlauf der letzten 24 Stunden
        klima = tk.Frame(self.root, bg="black")
        self.l_klima_titel = label(klima, schrift(0.04), 0.7, text="Raumklima")
        self.l_klima_titel.pack(pady=(rand, 0))
        self.l_klima_wert = label(klima, schrift(0.12))
        self.l_klima_wert.pack()
        self.l_klima_hinweis = label(klima, klein, 0.85)
        self.l_klima_hinweis.pack()
        self.kurve = tk.Canvas(klima, bg="black", highlightthickness=0,
                               width=int(breite * 0.8), height=int(hoehe * 0.34))
        self.kurve.pack(pady=(int(hoehe * 0.02), 0))
        self.kurve_schrift = klein

        self.rahmen = {"voll": voll, "uhr": uhr, "klima": klima}

    # ---------- Hauptschleife ----------

    def _takt(self):
        """Wird fünfmal pro Sekunde aufgerufen."""
        jetzt = time.time()
        self._verarbeite_ereignisse()
        self._pruefe_timer_und_wecker(jetzt)

        aktiv = self._ist_aktiv(jetzt)
        if aktiv != self.aktiv:
            self._schalte_anzeige(aktiv)

        if self.led_an and jetzt > self.hoert_bis:
            self._zuhoeren_ende()
        if self.meldung_bis and jetzt > self.meldung_bis:
            self._meldung("", "")

        if aktiv:
            self._aktualisiere_texte(jetzt)
            self._aktualisiere_helligkeit()
            if ANSICHTEN[self.ansicht] == "klima":
                self._zeichne_kurve()
        self.root.after(200, self._takt)

    def _ist_aktiv(self, jetzt):
        if config.PORT_ULTRASCHALL is None or self.zustand.klingelt:
            return True
        letzte_regung = max(self.zustand.zuletzt_gesehen, self.geweckt)
        return jetzt - letzte_regung < config.AUSSCHALTEN_NACH_S

    def _zeige_ansicht(self):
        for rahmen in self.rahmen.values():
            rahmen.pack_forget()
        if self.aktiv:
            self.rahmen[ANSICHTEN[self.ansicht]].pack(fill="both", expand=True)
            self.kurve_stand = None     # Kurve beim nächsten Takt neu zeichnen

    def _schalte_anzeige(self, aktiv):
        """Schaltet zwischen sichtbarer Anzeige und schwarzem Spiegel um."""
        erster_start = self.aktiv is None
        self.aktiv = aktiv
        self._zeige_ansicht()
        if aktiv:
            if not self.meldung_bis:
                self._meldung("", befehle.gruss(), dauer=5)
                if config.BEGRUESSUNG_SPRECHEN and not erster_start:
                    self.sprecher.sage(befehle.gruss())
        else:
            self._meldung("", "")
            self.l_laufzeile.config(text="")
        if config.MONITOR_AUSSCHALTEN:
            try:
                subprocess.call(["vcgencmd", "display_power", "1" if aktiv else "0"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass

    # ---------- Inhalte ----------

    def _aktualisiere_texte(self, jetzt_s):
        z = self.zustand
        jetzt = datetime.datetime.now()
        zeit = jetzt.strftime("%H:%M")
        datum = befehle.datum_text(jetzt)
        self.l_zeit.config(text=zeit)
        self.l_sekunden.config(text=jetzt.strftime("%S"))
        self.l_datum.config(text=datum)
        self.l_zeit_gross.config(text=zeit)
        self.l_datum_gross.config(text=datum)

        # Merkzettel links: Countdowns, Timer, Wecker, Musik
        zeilen = befehle.countdowns(jetzt.date())[:2]
        if z.timer_ende:
            zeilen.append("Timer  {}".format(zeitgeber.rest_anzeige(z.timer_ende - jetzt_s)))
        if z.wecker:
            zeilen.append("Wecker  {}".format(z.wecker))
        z.musik = self.musik.laeuft()
        if z.musik:
            zeilen.append("♪ Musik läuft")
        self.l_merkzettel.config(text="\n".join(zeilen))

        # Termine links
        if z.termine:
            zeilen = ["Termine"] + ["{}  {}".format(kalender.tag_text(t, jetzt), self._kurz(t["titel"], 26))
                                    for t in z.termine]
            self.l_termine.config(text="\n".join(zeilen))
        else:
            self.l_termine.config(text="")

        # Wetter rechts
        w = z.wetter
        if w:
            self.l_wetter_grad.config(text="{}°".format(int(round(w["temperatur"]))))
            zeilen = ["{} · {}".format(config.ORT_NAME, w["text"]),
                      "↓ {}°   ↑ {}°".format(int(round(w["minimum"])), int(round(w["maximum"])))]
            if w.get("morgen"):
                m = w["morgen"]
                zeilen.append("Morgen {}° bis {}°{}".format(
                    int(round(m["minimum"])), int(round(m["maximum"])),
                    ", " + m["text"] if m["text"] else ""))
            tipp = wetter.kleidungstipp(w)
            if tipp:                        # Tipp und Zusatz in eigene Zeilen
                zeilen += [teil[0].upper() + teil[1:] for teil in tipp.split(", ")]
            self.l_wetter.config(text="\n".join(zeilen))
        else:
            self.l_wetter_grad.config(text="")
            self.l_wetter.config(text="")

        # Raumklima rechts und in der Klima-Ansicht
        if z.temperatur is not None:
            klima = "{} °C  ·  {} %".format(befehle.zahl(z.temperatur), befehle.zahl(z.feuchte))
            hinweis = "Bitte lüften" if befehle.lueften_noetig(z) else ""
            self.l_raum.config(text="Raum  " + klima + ("\n" + hinweis if hinweis else ""))
            self.l_klima_wert.config(text=klima)
            self.l_klima_hinweis.config(text=hinweis or "Luftfeuchtigkeit in Ordnung")
        else:
            self.l_raum.config(text="")
            self.l_klima_wert.config(text="– °C")
            self.l_klima_hinweis.config(text="Der Sensor liefert noch keinen Wert")

        # Abfahrten rechts
        fahrten = abfahrten.naechste(z.abfahrten, config.ABFAHRTEN_ANZAHL, jetzt)
        if fahrten:
            zeilen = [self._kurz(z.abfahrten["haltestelle"].replace(" (Berlin)", ""), 34)]
            for linie, ziel, minuten in fahrten:
                zeilen.append("{}  {}  ·  {}".format(
                    linie, ziel, "jetzt" if minuten == 0 else "{} min".format(minuten)))
            self.l_abfahrten.config(text="\n".join(zeilen))
        else:
            self.l_abfahrten.config(text="")

        # Laufzeile unten: Spruch des Tages und Schlagzeilen im Wechsel
        if jetzt_s >= self.laufzeile_wechsel:
            eintraege = ["„{}“".format(sprueche.spruch_des_tages(jetzt.date()).rstrip("."))]
            eintraege += [self._kurz(titel, 110) for titel in (z.nachrichten or [])]
            self.laufzeile_nr = (self.laufzeile_nr + 1) % len(eintraege)
            self.l_laufzeile.config(text=eintraege[self.laufzeile_nr])
            self.laufzeile_wechsel = jetzt_s + config.LAUFZEILE_WECHSEL_S

    @staticmethod
    def _kurz(text, laenge):
        return text if len(text) <= laenge else text[:laenge - 1] + "…"

    def _grau(self, faktor):
        wert = max(0, min(255, int(255 * (self.helligkeit or 1.0) * faktor)))
        return "#{0:02x}{0:02x}{0:02x}".format(wert)

    def _aktualisiere_helligkeit(self):
        if self.zustand.helligkeit == self.helligkeit:
            return
        self.helligkeit = self.zustand.helligkeit
        for l, faktor in self.texte:
            l.config(fg=self._grau(faktor))
        self.kurve_stand = None

    def _zeichne_kurve(self):
        """Temperaturverlauf der letzten 24 Stunden als Linie."""
        verlauf = self.zustand.verlauf
        stand = (len(verlauf), verlauf[-1][0] if verlauf else 0)
        if stand == self.kurve_stand:
            return      # nichts Neues, nicht neu zeichnen
        self.kurve_stand = stand
        k = self.kurve
        k.delete("all")
        breite, hoehe = int(k["width"]), int(k["height"])
        schrift, hell, dunkel = self.kurve_schrift, self._grau(1.0), self._grau(0.45)
        if len(verlauf) < 2:
            k.create_text(breite // 2, hoehe // 2, fill=dunkel, font=schrift,
                          text="Der Verlauf füllt sich mit der Zeit (ein Messwert alle 5 Minuten).")
            return
        werte = [t for _, t in verlauf]
        tief, hoch = min(werte), max(werte)
        if hoch - tief < 2:                     # mindestens 2 Grad Spanne zeigen
            mitte = (hoch + tief) / 2
            tief, hoch = mitte - 1, mitte + 1
        links, rechts, oben, unten = int(breite * 0.09), breite - 4, 8, hoehe - int(hoehe * 0.16)
        start, ende = verlauf[0][0], verlauf[-1][0]
        dauer = max(1.0, ende - start)
        punkte = []
        for zeitpunkt, temperatur in verlauf:
            punkte.append(links + (zeitpunkt - start) / dauer * (rechts - links))
            punkte.append(unten - (temperatur - tief) / (hoch - tief) * (unten - oben))
        for wert, y in ((hoch, oben), (tief, unten)):
            k.create_line(links, y, rechts, y, fill=dunkel, dash=(2, 6))
            k.create_text(links - 8, y, anchor="e", fill=dunkel, font=schrift,
                          text="{}°".format(befehle.zahl(wert)))
        k.create_line(*punkte, fill=hell, width=max(2, hoehe // 90), smooth=True)
        minuten = int(round((time.time() - start) / 60))
        k.create_text(links, hoehe, anchor="sw", fill=dunkel, font=schrift,
                      text="vor {} Std.".format(int(round(minuten / 60.0))) if minuten >= 90
                      else "vor {} min".format(minuten))
        k.create_text(rechts, hoehe, anchor="se", fill=dunkel, font=schrift, text="jetzt")

    # ---------- Timer und Wecker ----------

    def _pruefe_timer_und_wecker(self, jetzt):
        z = self.zustand
        if z.timer_ende and jetzt >= z.timer_ende:
            z.timer_ende = None
            self._klingeln("Timer", "Der Timer ist abgelaufen.")
        if z.wecker:
            heute = (datetime.date.today(), z.wecker)
            if time.strftime("%H:%M") == z.wecker and self.wecker_geklingelt != heute:
                self.wecker_geklingelt = heute
                self._klingeln("Wecker", "Guten Morgen! Es ist {}.".format(
                    zeitgeber.uhrzeit_text(z.wecker)))
        if z.klingelt:
            self.geweckt = jetzt
            self._meldung("", "{} – zum Beenden Taster drücken".format(z.klingelt), dauer=2)
            if jetzt - self.klingelt_seit > config.KLINGEL_DAUER_S:
                self._klingeln_ende()

    def _klingeln(self, grund, satz):
        self.zustand.klingelt = grund       # der Summer piept, solange das gesetzt ist
        self.klingelt_seit = time.time()
        self.sprecher.sage(satz)

    def _klingeln_ende(self):
        self.zustand.klingelt = None
        self._meldung("", "")

    # ---------- Ereignisse von Taster und Sprache ----------

    def _verarbeite_ereignisse(self):
        while True:
            try:
                art, wert = self.ereignisse.get_nowait()
            except queue.Empty:
                return
            war_aktiv = self._ist_aktiv(time.time())
            self.geweckt = time.time()
            if art == "taster":
                if self.zustand.klingelt:
                    self._klingeln_ende()
                elif war_aktiv:     # ein Druck auf den dunklen Spiegel weckt ihn nur auf
                    self._naechste_ansicht()
            elif art == "hoert_zu":
                self.hoert_bis = time.time() + 10
                self.led_an = True
                self.sensoren.status_led(True)
                self._meldung("", "Ich höre zu …", dauer=10)
            elif art == "abbruch":
                self._zuhoeren_ende()
                self._meldung("", "")
            elif art == "befehl":
                self._zuhoeren_ende()
                self._fuehre_aus(wert)
            elif art == "ki_antwort":
                frage, antwort = wert
                self._antworte(frage, antwort)

    def _fuehre_aus(self, text):
        z = self.zustand
        antwort, aktion = befehle.antworte(text, z)
        name, wert = aktion or (None, None)
        if name == "ki":
            if ki.verfuegbar():
                self._meldung("„{}“".format(text), "Ich überlege …", dauer=40)
                threading.Thread(target=self._frage_ki, args=(text,), daemon=True).start()
                return
        elif name == "licht":
            self.sensoren.licht(wert)
        elif name == "ansicht":
            self._naechste_ansicht()
        elif name == "timer":
            z.timer_ende = time.time() + wert
        elif name == "timer_stopp":
            z.timer_ende = None
            if z.klingelt == "Timer":
                self._klingeln_ende()
        elif name == "wecker":
            z.wecker = wert
            self.wecker_geklingelt = None
        elif name == "wecker_aus":
            z.wecker = None
            if z.klingelt == "Wecker":
                self._klingeln_ende()
        elif name == "musik":
            if wert:
                antwort = self.musik.an()
            else:
                self.musik.aus()
        elif name == "stopp":
            self._klingeln_ende()
        self._antworte(text, antwort)

    def _frage_ki(self, text):
        """Läuft im Hintergrund, damit die Anzeige nicht stehen bleibt."""
        try:
            antwort = ki.frage(text)
        except Exception as fehler:
            print("[KI] Anfrage fehlgeschlagen: {}".format(fehler))
            antwort = "Die KI ist gerade nicht erreichbar."
        self.ereignisse.put(("ki_antwort", (text, antwort)))

    def _antworte(self, frage, antwort):
        print("[Befehl] {}  ->  {}".format(frage, antwort))
        self._meldung("„{}“".format(frage), antwort,
                      dauer=max(config.MELDUNG_DAUER_S, len(antwort) // 12))
        self.sprecher.sage(antwort)

    def _naechste_ansicht(self):
        self.ansicht = (self.ansicht + 1) % len(ANSICHTEN)
        self._zeige_ansicht()

    def _zuhoeren_ende(self):
        if self.led_an:
            self.led_an = False
            self.sensoren.status_led(False)

    def _meldung(self, gehoert, text, dauer=None):
        self.l_gehoert.config(text=gehoert)
        self.l_meldung.config(text=text)
        if text:
            self.meldung_bis = time.time() + (dauer or config.MELDUNG_DAUER_S)
        else:
            self.meldung_bis = 0

    # ---------- Tasten ----------

    def _befehl_eintippen(self):
        text = simpledialog.askstring("Befehl", "Was möchtest du fragen?", parent=self.root)
        if text:
            self.ereignisse.put(("befehl", text))

    def _sim_anwesenheit(self):
        if sensoren.SIMULATION:
            self.sensoren.sim_anwesend = not self.sensoren.sim_anwesend
            print("[Simulation] Jemand steht davor: {}".format(self.sensoren.sim_anwesend))

    def _vollbild_umschalten(self):
        self.vollbild = not self.vollbild
        self.root.attributes("-fullscreen", self.vollbild)
        self.root.config(cursor="none" if self.vollbild else "")

    def beenden(self):
        self.musik.aus()
        self.sensoren.aufraeumen()
        self.root.destroy()

    def starte(self):
        self.root.mainloop()


if __name__ == "__main__":
    eingabe = argparse.ArgumentParser(description="Smart Mirror")
    eingabe.add_argument("--fenster", action="store_true",
                         help="im Fenster statt im Vollbild starten")
    optionen = eingabe.parse_args()
    Spiegel(vollbild=config.VOLLBILD and not optionen.fenster).starte()
