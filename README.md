# Smart Mirror für Raspberry Pi mit GrovePi+

Ein Spiegel, der Uhrzeit, Wetter, Termine, Abfahrten und Nachrichten anzeigt, sich einschaltet, wenn jemand davorsteht, und auf Sprachbefehle wie „Spiegel, Timer fünf Minuten“ reagiert.

Das Programm läuft auch **ohne Pi** auf deinem eigenen Rechner. Dann startet automatisch ein Simulationsmodus mit ausgedachten Sensorwerten, sodass du Anzeige und Befehle vorab testen kannst.

## Was das Programm kann

| Funktion | Was du dafür brauchst |
|---|---|
| Uhrzeit und Datum | nichts |
| Wetter heute und morgen, Kleidungstipp | Internet |
| Raumtemperatur, Luftfeuchtigkeit, Hinweis „Bitte lüften“ | Temperatur-/Feuchtesensor (blau) |
| Temperaturverlauf der letzten 24 Stunden als Kurve | Temperatur-/Feuchtesensor |
| Anzeige nur an, wenn jemand davorsteht | Ultraschallsensor |
| Ansicht wechseln (alles / große Uhr / Raumklima) | Taster |
| Helligkeit der Schrift einstellen | Drehregler |
| Timer und Wecker mit Piepton | Summer |
| Raumklima auf dem kleinen Display, Farbe je nach Temperatur | LCD-Display |
| „Spiegel, Licht an“ | LED oder Relais |
| Anzeigen, dass der Spiegel zuhört | zweite LED |
| Countdown bis zu einem Datum, Spruch des Tages | nichts |
| Schlagzeilen der Tagesschau | Internet |
| Abfahrten von Bus und Bahn (Berlin/Brandenburg) | Internet |
| Termine aus deinem Kalender | Internet und Kalenderadresse |
| Sprachbefehle | USB-Mikrofon und Lautsprecher (nicht im Set) |
| Freie Fragen mit KI beantworten | Internet und ein kostenpflichtiger Schlüssel |
| Musik abspielen | Lautsprecher und MP3-Dateien |

Alles, wofür etwas fehlt, blendet der Spiegel einfach aus. Im Terminal steht dann, woran es liegt.

## 1. Verkabeln

Stecke die Module bei **ausgeschaltetem** Pi an diese Buchsen der blauen GrovePi-Platine:

| Buchse | Modul |
|---|---|
| **D2** | Temperatur-/Feuchtesensor (blau) |
| **D3** | Taster |
| **D4** | Ultraschallsensor |
| **D5** | LED (Status: leuchtet, wenn der Spiegel zuhört) |
| **D6** | zweite LED oder Relais („Licht“) |
| **D7** | Summer |
| **A0** | Drehregler |
| **I2C** (egal welche) | LCD-Display |

Du musst nicht alles anschließen. Fehlt ein Modul, trägst du in `config.py` bei seinem Port `None` ein, zum Beispiel `PORT_DREHREGLER = None`. Beim LCD heißt die Einstellung `LCD_AKTIV = False`. Das ist beim Drehregler wichtig: Ist er eingetragen, aber nicht eingesteckt, flackert die Helligkeit der Schrift.

Der Ultraschallsensor braucht freie Sicht nach vorn. Hinter dem Spiegelglas funktioniert er nicht, also später am Rahmen befestigen.

## 2. Code zu GitHub hochladen (am eigenen Rechner)

1. Auf [github.com](https://github.com) ein neues, **öffentliches** Repository anlegen, zum Beispiel `smart-mirror`. Kein README anhaken, das bringt dieses Projekt schon mit.
2. Die ZIP-Datei entpacken, im Ordner `smart-mirror` ein Terminal öffnen und eingeben (`DEINNAME` ersetzen):

```bash
git init
git add .
git commit -m "Erste Version"
git branch -M main
git remote add origin https://github.com/DEINNAME/smart-mirror.git
git push -u origin main
```

Vorher kannst du das Programm am eigenen Rechner ausprobieren:

```bash
python3 spiegel.py --fenster
```

## 3. Auf den Pi holen und starten

Im Terminal des Pi:

```bash
cd ~
git clone https://github.com/DEINNAME/smart-mirror.git
cd smart-mirror
python3 spiegel.py
```

Nach späteren Änderungen reicht auf dem Pi `git pull` im Ordner `smart-mirror`.

Ein Kursgerät benutzen auch andere. Melde dich darauf nicht mit deinem GitHub-Konto an. Bei einem öffentlichen Repository ist das zum Herunterladen auch nicht nötig.

Zum ersten Test ohne Vollbild: `python3 spiegel.py --fenster`

## 4. Bedienen

| Aktion | Wirkung |
|---|---|
| Vor den Spiegel treten | Anzeige geht an, nach 30 Sekunden ohne Person wieder aus |
| Taster drücken | nächste Ansicht (alles → große Uhr → Raumklima mit Kurve) |
| Taster drücken, während es piept | Timer oder Wecker beenden |
| Drehregler drehen | Schrift heller oder dunkler |
| Taste **Esc** | Programm beenden |
| **Leertaste** | wirkt wie der Taster |
| Taste **T** | Befehl eintippen statt sprechen (gut zum Testen) |
| Taste **F11** | Vollbild an/aus |
| Taste **A** | nur in der Simulation: „jemand steht davor“ an/aus |

Im Terminal beendet auch **Strg+C** das Programm.

## 5. Die Funktionen einstellen

Alles steht in `config.py`, jeweils mit Erklärung.

**Wetter:** `ORT_NAME`, `BREITENGRAD` und `LAENGENGRAD` auf deinen Ort setzen. Die Koordinaten stehen zum Beispiel im Wikipedia-Artikel deiner Stadt.

**Abfahrten:** Bei `HALTESTELLE` den Namen deiner Haltestelle eintragen, so wie er in der BVG-App steht. Das funktioniert nur in Berlin und Brandenburg. Mit `HALTESTELLE = ""` schaltest du es ab. Die Daten kommen von einer inoffiziellen Schnittstelle, die Freiwillige betreiben. Ist sie nicht erreichbar, fehlen die Abfahrten, bis sie wieder läuft.

**Countdown:** In `COUNTDOWNS` Name und Datum eintragen, zum Beispiel `("Prüfung", "2027-02-15")`. Angezeigt werden die nächsten zwei.

**Spruch des Tages:** Die Liste steht in `sprueche.py` und lässt sich beliebig ändern.

**Lüften-Hinweis:** `LUEFTEN_AB_PROZENT` legt fest, ab welcher Luftfeuchtigkeit „Bitte lüften“ erscheint.

**Wecker:** Entweder per Sprache stellen oder fest eintragen, zum Beispiel `WECKER = "07:30"`. Er klingelt dann jeden Tag um diese Zeit. Ein per Sprache gestellter Wecker gilt, bis das Programm neu startet.

**Nachrichten:** `NACHRICHTEN_URL` kann auf jeden anderen RSS-Feed zeigen.

**Kalender:** Du brauchst die Adresse deines Kalenders im ICS-Format.

1. Im Google Kalender: Einstellungen → links deinen Kalender wählen → „Privatadresse im iCal-Format“ kopieren. Andere Kalender (Uni, Nextcloud, Outlook) bieten etwas Ähnliches unter „Kalender abonnieren“ oder „ICS-Link“ an.
2. Die Datei `config_geheim_beispiel.py` kopieren, die Kopie `config_geheim.py` nennen und dort die Adresse bei `KALENDER_URL` eintragen.

Wer diese Adresse kennt, kann deine Termine lesen. Deshalb steht sie in `config_geheim.py`, die nicht zu GitHub hochgeladen wird. Auf den Pi bringst du die Datei per USB-Stick. Einzelne, ganztägige und einfache Serientermine (täglich, wöchentlich, monatlich, jährlich) werden angezeigt. Ausgefallene Serien wie „jeder zweite Dienstag im Monat“ erscheinen nur am ersten Termin.

## 6. Sprachsteuerung einrichten (optional)

Ohne diesen Schritt läuft der Spiegel ganz normal, nur ohne Sprache. Befehle kannst du trotzdem mit der Taste **T** eintippen.

**Du brauchst zusätzlich:** ein USB-Mikrofon (oder eine USB-Webcam mit Mikrofon) und einen Lautsprecher an der Klinkenbuchse des Pi oder Lautsprecher im Monitor. Das Grove-Mikrofon aus dem Set misst nur Lautstärke und kann keine Sprache aufnehmen.

**Einmalig auf dem Pi installieren** (braucht Internet):

```bash
sudo apt install espeak-ng
pip3 install vosk
cd ~/smart-mirror
wget https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip
unzip vosk-model-small-de-0.15.zip
mv vosk-model-small-de-0.15 modell
```

- Meldet `pip3` den Fehler „externally-managed-environment“, nimm `pip3 install --break-system-packages vosk`.
- Gibt es `espeak-ng` nicht, nimm `sudo apt install espeak`. Das Programm findet beide.
- Das Sprachmodell ist 45 MB groß und wird nicht zu GitHub hochgeladen.

**Mikrofon und Lautsprecher testen:**

```bash
arecord -l                      # zeigt die Mikrofone an
arecord -d 3 test.wav           # 3 Sekunden aufnehmen
aplay test.wav                  # abspielen
espeak-ng -v de "Hallo"         # Sprachausgabe testen
```

Bleibt die Aufnahme stumm, merke dir aus `arecord -l` die Kartennummer des USB-Mikrofons (zum Beispiel „Karte 1“) und trage in `config.py` ein: `MIKROFON = "plughw:1,0"`. Ob der Ton über HDMI oder Klinke kommt, stellst du mit `sudo raspi-config` unter „System Options“ → „Audio“ ein.

**So sprichst du mit dem Spiegel:** Der Satz muss das Wort „Spiegel“ enthalten, danach kommt der Befehl. Du kannst auch nur „Spiegel“ sagen, kurz warten und dann den Befehl sprechen. Solange er zuhört, leuchtet die Status-LED.

| Sag zum Beispiel | Wirkung |
|---|---|
| „Spiegel, wie spät ist es?“ / „welcher Tag ist heute?“ | Uhrzeit, Datum |
| „Spiegel, wie ist das Wetter?“ / „wie wird das Wetter morgen?“ | Wetter draußen |
| „Spiegel, was soll ich anziehen?“ | Kleidungstipp |
| „Spiegel, wie warm ist es?“ / „soll ich lüften?“ | Raumklima vom Sensor |
| „Spiegel, Timer fünf Minuten“ / „Timer stopp“ / „wie lange noch?“ | Timer |
| „Spiegel, Wecker auf sieben Uhr dreißig“ / „Wecker aus“ | Wecker |
| „Spiegel, stopp“ | beendet das Piepen |
| „Spiegel, was steht an?“ | nächste Termine |
| „Spiegel, was gibt es Neues?“ | drei Schlagzeilen |
| „Spiegel, wann fährt die nächste Bahn?“ | nächste Abfahrten |
| „Spiegel, wie lange noch bis Weihnachten?“ | Countdown |
| „Spiegel, Licht an“ / „Licht aus“ | schaltet D6 |
| „Spiegel, Musik an“ / „Musik aus“ | Musik |
| „Spiegel, Ansicht wechseln“ | nächste Ansicht |
| „Spiegel, Spruch des Tages“ / „erzähl einen Witz“ | Spruch, Witz |
| „Spiegel, Hilfe“ | zählt auf, was er kann |

Beim Timer versteht er auch „eine halbe Stunde“, „zwei Minuten dreißig“ oder „anderthalb Stunden“. Beim Wecker auch „halb acht“ und „Viertel vor sieben“.

Die Erkennung läuft komplett auf dem Pi, es wird nichts ins Internet geschickt. Sprich deutlich und nicht zu weit vom Mikrofon entfernt.

**Befehle ohne Mikrofon testen:** `python3 befehle.py` starten und die Sätze eintippen. Oder im laufenden Spiegel die Taste **T** drücken.

## 7. Musik (optional)

Lege MP3-Dateien in den Ordner `musik`. Mit „Spiegel, Musik an“ werden sie in zufälliger Reihenfolge gespielt. Für ein Internetradio trägst du in `config.py` bei `RADIO_URL` die Adresse eines MP3-Streams ein.

Auf dem Pi muss ein Abspielprogramm installiert sein, zum Beispiel mit `sudo apt install mpg123`. Solange Musik läuft, versteht das Mikrofon Sprachbefehle schlechter. Dann hilft der Taster oder die Taste **T**.

## 8. Freie Fragen mit KI (optional)

Normalerweise kennt der Spiegel nur die festen Befehle aus der Tabelle. Mit einem KI-Schlüssel beantwortet er auch alles andere, zum Beispiel „Spiegel, wie hoch ist der Mount Everest?“.

1. Auf [platform.claude.com](https://platform.claude.com/settings/keys) ein Konto anlegen, Guthaben aufladen und einen Schlüssel (API Key) erzeugen.
2. `config_geheim_beispiel.py` kopieren, die Kopie `config_geheim.py` nennen und den Schlüssel bei `KI_SCHLUESSEL` eintragen.
3. Die Datei per USB-Stick auf den Pi bringen.

Das solltest du wissen:

- Jede Frage, die der Spiegel nicht selbst beantworten kann, wird dann ins Internet geschickt und kostet einen kleinen Betrag. Die festen Befehle bleiben auf dem Pi und kosten nichts.
- Der Schlüssel ist wie ein Passwort mit Geld dahinter. Er darf nur in `config_geheim.py` stehen, nie in einer Datei, die zu GitHub hochgeladen wird. Auf einem Gerät, das auch andere benutzen, lösch die Datei nach dem Vorführen wieder.
- Mit `KI_AKTIV = False` in `config.py` schaltest du die KI ab, auch wenn ein Schlüssel vorhanden ist.

## 9. Eigene Sprachbefehle ergänzen

In `befehle.py` in der Funktion `antworte()` einen Block vor dem Abschnitt „Plaudern“ einfügen:

```python
    if _enthaelt(text, "mensa", "essen"):
        return "Heute gibt es Nudeln.", None
```

Der Text kommt immer kleingeschrieben und ohne Satzzeichen an.

## 10. Automatisch beim Hochfahren starten

Nur einrichten, wenn du das auf dem Kursgerät darfst. Datei `~/.config/autostart/spiegel.desktop` anlegen (den Ordner vorher mit `mkdir -p ~/.config/autostart` erzeugen):

```ini
[Desktop Entry]
Type=Application
Name=Smart Mirror
Exec=python3 /home/pi/smart-mirror/spiegel.py
```

Rückgängig machen: die Datei wieder löschen. Damit der Bildschirm nicht von selbst dunkel wird: `sudo raspi-config` → „Display Options“ → „Screen Blanking“ ausschalten.

## 11. Den Spiegel bauen

Für die Hardware brauchst du einen Spionspiegel (Acrylglas ist günstiger und bruchsicher), der vor dem Bildschirm sitzt, und einen Rahmen. Überall, wo der Bildschirm schwarz ist, sieht man nur das Spiegelbild. Die weiße Schrift scheint durch. Mit dem Drehregler passt du die Helligkeit an das Glas an.

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| `No module named 'tkinter'` | `sudo apt install python3-tk` |
| Im Terminal steht „Simulationsmodus“, obwohl du am Pi bist | Die GrovePi-Bibliothek fehlt oder I2C ist aus. Mit `sudo i2cdetect -y 1` prüfen, ob `04` erscheint. In der Meldung steht der genaue Grund. |
| Temperatur fehlt | Der Sensor braucht nach dem Start bis zu 15 Sekunden. Sonst Port prüfen. Bei einem weißen Sensor `DHT_TYP = 1` setzen. |
| Die Kurve ist leer | Sie bekommt alle 5 Minuten einen Messwert und füllt sich mit der Zeit. |
| Anzeige geht nie aus oder nie an | `ANWESENHEIT_CM` anpassen. Steht etwas dauerhaft vor dem Sensor? Zum Test `PORT_ULTRASCHALL = None`, dann bleibt die Anzeige immer an. |
| LCD bleibt dunkel | Steckt es an einer I2C-Buchse? `sudo i2cdetect -y 1` muss `3e` und `62` zeigen. Zeigt es eine andere Farbadresse, hast du eine neuere Display-Version, dann kommt nur der Text ohne Farbe. |
| Summer piept dauerhaft oder gar nicht | Port prüfen (`PORT_SUMMER`). Der Taster beendet das Piepen. |
| Kein Wetter, keine Nachrichten, keine Abfahrten | Der Pi braucht Internet. Im Terminal steht der Grund. |
| Falsche Haltestelle | Im Terminal steht nach dem Start, welche Haltestelle gefunden wurde. Den Namen in `config.py` genauer schreiben. |
| Uhrzeit ist falsch | Der Pi hat keine eigene Uhr mit Batterie. Er holt die Zeit aus dem Internet, sobald er online ist. |
| Spiegel reagiert nicht auf Sprache | Im Terminal muss „Ich höre zu“ stehen. Sonst steht dort, was fehlt. Mikrofon mit `arecord` testen (siehe oben). |
| Er versteht das Falsche | Näher ans Mikrofon, deutlich sprechen. Das Terminal zeigt bei jedem Befehl, was verstanden wurde. |
| `git pull` meldet lokale Änderungen | `git reset --hard` und dann `git pull`. Achtung, Änderungen auf dem Pi gehen dabei verloren. |

## Die Dateien

| Datei | Aufgabe |
|---|---|
| `spiegel.py` | Hauptprogramm: Anzeige und Ablauf |
| `config.py` | alle Einstellungen |
| `config_geheim_beispiel.py` | Vorlage für KI-Schlüssel und private Kalenderadresse |
| `sensoren.py` | liest die Grove-Module, schaltet LEDs, Relais, Summer |
| `lcd.py` | steuert das kleine LCD-Display |
| `befehle.py` | versteht die Befehle und baut die Antworten |
| `zeitgeber.py` | macht aus „fünf Minuten“ und „halb acht“ Zahlen |
| `sprache.py` | Spracherkennung und Sprachausgabe |
| `wetter.py` | Wetter und Kleidungstipp |
| `nachrichten.py` | Schlagzeilen |
| `abfahrten.py` | Bus und Bahn |
| `kalender.py` | Termine |
| `sprueche.py` | Sprüche des Tages |
| `ki.py` | freie Fragen mit KI |
| `musik.py` | Musik abspielen |
| `netz.py` | lädt Daten aus dem Internet |

Das Programm braucht Python 3.5 oder neuer (`python3 --version`).
