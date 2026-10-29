# Pm3 – Prüfstand

Zug-/Druck-Prüfstand mit Raspberry Pi 4. Ein C++-Hauptprogramm steuert Schrittmotor, Endschalter und Wägezelle
über eine Zustandsmaschine. Das Handy des Anwenders ist Bedienoberfläche und Kamera zugleich: Es zeigt Taster,
Live-Werte und den Testverlauf, nimmt die Kamera in 1920×1080 auf (ohne sie anzuzeigen) und schickt ein
Live-Bild an die Bildanalyse auf dem Pi.

## Aufbau

| Ordner | Inhalt |
| --- | --- |
| `steuerung/` | **Hauptprogramm in C++**: Zustandsmaschine, Motor (TMC2209), Endschalter, Wägezelle (HX711), Messdaten als CSV. Einstellungen in `steuerung/pruefstand.conf` |
| `webserver/` | Python-Webserver: liefert die Handy-Seite aus, speichert das Video, verbindet Handy, Steuerung und Bildanalyse |
| `web/` | Handy-Seiten: Bedienoberfläche (`index.html`) und Zertifikat-Einrichtung (`einrichten.html`) |
| `bildanalyse/` | Auswertung des Live-Bilds (`auswertung.py`) |
| `start.sh` | Baut und startet alles |
| `daten/` | entsteht beim Betrieb: `messdaten/` (CSV) und `aufnahmen/` (Videos) |

```
Handy ──HTTPS/WebSocket──► webserver/server.py ──TCP 127.0.0.1:7000──► steuerung/ (C++)
  │  Taster, Live-Werte        │                                          ├─ Motor (TMC2209)
  │  Video + Live-Bild ───────►├─► bildanalyse/auswertung.py ──optik──►   ├─ Endschalter
  │                            └─► daten/aufnahmen/                       ├─ Wägezelle (HX711)
                                                                          └─► daten/messdaten/*.csv
```

### Zustandsmaschine (`steuerung/src/zustandsmaschine.cpp`)

```
UNREFERENZIERT ──Referenz──► REFERENZFAHRT ──Endschalter──► POSITIONIEREN (1 mm freifahren) ──► BEREIT
BEREIT ──Start──► PRUEFUNG ──Maximalkraft / Maximalweg / Bruch / Stopp──► ENDE ──Quittieren──► BEREIT
BEREIT ──◀ 1 mm / 1 mm ▶──► POSITIONIEREN ──► BEREIT
jeder Zustand ──Kraftgrenze / Endschalter / NOT-HALT──► FEHLER ──Quittieren──► UNREFERENZIERT
```

Jede Prüfung schreibt eine CSV-Datei nach `daten/messdaten/` mit Zeit, Weg, Kraft und dem Ergebnis der
Bildanalyse (Spalte `optik`), dazu die Prüfparameter und das Ergebnis als Kommentarzeilen.

Befehle, die die Steuerung versteht (die Taster auf dem Handy schicken genau diese):
`referenz`, `start`, `stopp`, `quittieren`, `nothalt`, `tara`, `fahren <mm>`, `kalibrieren <N>`,
`set modus zug|druck`, `set geschwindigkeit <mm/min>`, `set maxkraft <N>`, `set maxweg <mm>`, `set bruch <%>`.

Die Verbindung läuft über **USB-Tethering** (Android) bzw. **Persönlicher Hotspot per Kabel** (iPhone).
Mobile Daten werden dabei nicht verbraucht, das Handy und der Pi reden nur miteinander.

## 1. Raspberry Pi einrichten (einmalig)

Raspberry Pi 4 oder 5 mit **64-Bit** Raspberry Pi OS. Das Repository auf den Pi klonen, dann darin:

```bash
sudo apt install -y cmake g++ python3-venv python3-aiohttp python3-numpy python3-opencv openssl avahi-daemon usbmuxd
```

```bash
python3 -m venv --system-site-packages venv
```

```bash
venv/bin/pip install aiortc
```

`usbmuxd` braucht nur das iPhone, `avahi-daemon` sorgt dafür, dass der Pi als `raspberrypi.local` erreichbar ist.

Starten:

```bash
./start.sh
```

Das Skript baut beim ersten Mal das C++-Hauptprogramm und startet dann Steuerung und Webserver. Es zeigt die
Adressen an, unter denen das Handy den Pi erreicht. Es läuft weiter und passt sich
automatisch an, wenn das Handy neu eingesteckt wird und eine andere Adresse vergibt.

Beim ersten Start entsteht der Ordner `zertifikat/`. **Nicht weitergeben**, er enthält den geheimen Schlüssel.

**Ohne Hardware ausprobieren:** `SIM=1 ./start.sh` startet die Steuerung mit einem simulierten Prüfstand
(Probe reißt beim Zug bei ca. 400 N). Damit lässt sich der ganze Ablauf auf dem Handy testen.

### Verkabelung (Standard in `steuerung/pruefstand.conf`)

| Teil | Anschluss | Pi 4 (BCM) |
| --- | --- | --- |
| TMC2209 | STEP / DIR / EN | GPIO 20 / 21 / 16 |
| TMC2209 | VIO / GND | 3,3 V / GND |
| TMC2209 | VM | 24 V über Sicherung, Elko 100 µF / 35 V direkt am Treiber |
| Motor AS1020 (M12) | Pin 1 / 2 / 3 / 4 | TMC2209 A1 / A2 / B1 / B2 |
| Endschalter | gegen GND | GPIO 26 (interner Pull-up) |
| HX711 | DOUT / SCK | GPIO 5 / 6 |

Den Motorstrom am TMC2209 auf ca. 0,8–1,0 A einstellen. Läuft der Motor falsch herum, `richtung_umkehren = 1`
setzen.

### Wägezelle kalibrieren (einmalig)

Ohne Last **Tara** drücken, dann ein bekanntes Gewicht anhängen und den Befehl `kalibrieren <Kraft in N>`
schicken (z. B. 10 kg = `kalibrieren 98.1`). Der Faktor wird in `steuerung/kalibrierung.conf` gespeichert.
Einen Taster dafür gibt es noch nicht; bis dahin z. B. auf dem Pi: `echo "kalibrieren 98.1" | nc -q1 127.0.0.1 7000`.

## 2. Handy anschließen

**iPhone:** Einstellungen → **Persönlicher Hotspot** → „Zugriff für andere erlauben“ an. Dann per Kabel an den Pi
stecken und „Diesem Computer vertrauen?“ mit **Vertrauen** bestätigen.

**Android:** Per Kabel an den Pi stecken, dann Einstellungen → Netzwerk & Internet → Hotspot & Tethering →
**USB-Tethering** an.

## 3. Zertifikat installieren (einmalig pro Handy)

Im Browser (iPhone: Safari, Android: Chrome) die Adresse aus `start.sh` mit **http://** und Port **8080** öffnen,
z. B. `http://raspberrypi.local:8080`. Die Seite führt Schritt für Schritt durch die Installation.

## 4. Prüfen

Auf der Einrichtungsseite **„Zur Kamera-Seite“** tippen (oder direkt `https://raspberrypi.local:8443`).
Dann **Referenz** (fährt auf den Endschalter), **Tara**, unter **Prüfparameter** die Werte eintragen und mit
**Parameter ✓** übernehmen, dann **▶ Start**. Die Kamera startet mit; beim ersten Mal die Kamera erlauben.

Tipp: Die Seite auf den Startbildschirm legen (iPhone: Teilen → Zum Home-Bildschirm, Android: Chrome-Menü →
Zum Startbildschirm hinzufügen), dann läuft sie im Vollbild.

Wichtig: Die Seite muss im Vordergrund bleiben. Geht der Bildschirm aus oder wechselt man die App, pausiert die
Kamera (steht dann im Testverlauf). Deshalb:

- **iPhone:** Einstellungen → Anzeige & Helligkeit → Automatische Sperre → **Nie**.
- **Android:** Display → Bildschirm-Timeout auf den höchsten Wert.

## Die Videos

Jede Aufnahme landet als eigene Datei in `daten/aufnahmen/`: Android liefert `.webm`, das iPhone `.mp4`.
VLC spielt beide direkt ab. Für andere Programme eine `.webm` einmal umwandeln (verlustfrei, dauert Sekunden):

```bash
ffmpeg -i daten/aufnahmen/DATEI.webm -c copy DATEI.mp4
```

Die `.teil`-Dateien daneben merken sich, welche Teile schon gespeichert sind; sie können nach der Aufnahme weg.
Reißt das Kabel kurz ab, puffert die Seite das Video und schickt es nach, sobald die Verbindung wieder da ist.

## Wenn etwas nicht geht

| Problem | Lösung |
|---|---|
| `raspberrypi.local` wird nicht gefunden (manche Android-Handys) | Die IP-Adresse aus `start.sh` nehmen |
| „Verbindung nicht privat“ / Kamera nicht erlaubt | Zertifikat (Schritt 3) installieren, beim iPhone auch das Vertrauen einschalten |
| Hotspot- bzw. Tethering-Menü fehlt | Vom Mobilfunkanbieter gesperrt, dann geht nur WLAN |
| Pi findet das Handy nicht | Datenkabel statt Ladekabel nehmen |

## Eigene Auswertung

In `bildanalyse/auswertung.py` die Funktion `verarbeite(bild)` anpassen. `bild` ist ein numpy-Array (BGR, 1920×1080),
also direkt mit OpenCV nutzbar (`import cv2`). Rückgabe ist ein Text für das Handy oder `None`; er landet auch in der
Spalte `optik` der Messdatei.
Ist die Auswertung langsamer als die Kamera, bekommt sie immer das neueste Bild; dazwischen wird ausgelassen.
Nach Änderungen `start.sh` neu starten.

## Einstellungen

Steuerung (Mechanik, Geschwindigkeiten, Kraftgrenze, GPIO-Pins): `steuerung/pruefstand.conf`.

Kamera, oben im `<script>` von `web/index.html`:

- Aufnahme: `WIDTH`, `HEIGHT`, `FPS`, `BITRATE` (Standard 1920×1080, 30 Bilder/s, 8 Mbit/s)
- Live-Bild: `LIVE_HEIGHT`, `LIVE_FPS`, `LIVE_BITRATE` (Standard 1080, 15 Bilder/s, 8 Mbit/s). Die Auflösung
  bleibt immer voll; wird es eng, sinkt nur die Bildrate.
