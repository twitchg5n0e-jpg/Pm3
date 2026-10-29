# Pm3 – Prüfstand: Handy-Kamera → Raspberry Pi (Full HD per USB-Kabel, Android und iPhone)

Das Handy öffnet eine Seite vom Raspberry Pi im Browser. Die Seite nimmt die Kamera in 1920×1080 auf, zeigt
aber **kein Kamerabild**, sondern nur den **Testverlauf**. Das Video geht per USB-Kabel an den Pi und wird dort
im Ordner `aufnahmen/` gespeichert.

Gleichzeitig geht ein **Live-Bild** (1920×1080, 15 Bilder/s, ca. 0,2 s Verzögerung) per WebRTC an ein
Python-Programm auf dem Pi. Dort bekommt die Funktion `verarbeite()` in `auswertung.py` jedes Bild als
OpenCV-Bild; was sie zurückgibt, erscheint auf dem Handy unter **Auswertung**.

Die Verbindung läuft über **USB-Tethering** (Android) bzw. **Persönlicher Hotspot per Kabel** (iPhone).
Mobile Daten werden dabei nicht verbraucht, das Handy und der Pi reden nur miteinander.

## 1. Raspberry Pi einrichten (einmalig)

Raspberry Pi 4 oder 5 mit **64-Bit** Raspberry Pi OS. Das Repository auf den Pi klonen, dann darin:

```bash
sudo apt install -y python3-venv python3-aiohttp python3-numpy python3-opencv openssl avahi-daemon usbmuxd
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

Das Skript zeigt die Adressen an, unter denen das Handy den Pi erreicht. Es läuft weiter und passt sich
automatisch an, wenn das Handy neu eingesteckt wird und eine andere Adresse vergibt.

Beim ersten Start entsteht der Ordner `zertifikat/`. **Nicht weitergeben**, er enthält den geheimen Schlüssel.

## 2. Handy anschließen

**iPhone:** Einstellungen → **Persönlicher Hotspot** → „Zugriff für andere erlauben“ an. Dann per Kabel an den Pi
stecken und „Diesem Computer vertrauen?“ mit **Vertrauen** bestätigen.

**Android:** Per Kabel an den Pi stecken, dann Einstellungen → Netzwerk & Internet → Hotspot & Tethering →
**USB-Tethering** an.

## 3. Zertifikat installieren (einmalig pro Handy)

Im Browser (iPhone: Safari, Android: Chrome) die Adresse aus `start.sh` mit **http://** und Port **8080** öffnen,
z. B. `http://raspberrypi.local:8080`. Die Seite führt Schritt für Schritt durch die Installation.

## 4. Aufnehmen

Auf der Einrichtungsseite **„Zur Kamera-Seite“** tippen (oder direkt `https://raspberrypi.local:8443`),
dann **Start** und die Kamera einmal erlauben.

Tipp: Die Seite auf den Startbildschirm legen (iPhone: Teilen → Zum Home-Bildschirm, Android: Chrome-Menü →
Zum Startbildschirm hinzufügen), dann läuft sie im Vollbild.

Wichtig: Die Seite muss im Vordergrund bleiben. Geht der Bildschirm aus oder wechselt man die App, pausiert die
Kamera (steht dann im Testverlauf). Deshalb:

- **iPhone:** Einstellungen → Anzeige & Helligkeit → Automatische Sperre → **Nie**.
- **Android:** Display → Bildschirm-Timeout auf den höchsten Wert.

## Die Videos

Jede Aufnahme landet als eigene Datei in `aufnahmen/`: Android liefert `.webm`, das iPhone `.mp4`.
VLC spielt beide direkt ab. Für andere Programme eine `.webm` einmal umwandeln (verlustfrei, dauert Sekunden):

```bash
ffmpeg -i aufnahmen/DATEI.webm -c copy DATEI.mp4
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

In `auswertung.py` die Funktion `verarbeite(bild)` anpassen. `bild` ist ein numpy-Array (BGR, 1920×1080),
also direkt mit OpenCV nutzbar (`import cv2`). Rückgabe ist ein Text für das Handy oder `None`.
Ist die Auswertung langsamer als die Kamera, bekommt sie immer das neueste Bild; dazwischen wird ausgelassen.
Nach Änderungen `start.sh` neu starten.

## Einstellungen

Oben im `<script>` von `index.html`:

- Aufnahme: `WIDTH`, `HEIGHT`, `FPS`, `BITRATE` (Standard 1920×1080, 30 Bilder/s, 8 Mbit/s)
- Live-Bild: `LIVE_HEIGHT`, `LIVE_FPS`, `LIVE_BITRATE` (Standard 1080, 15 Bilder/s, 8 Mbit/s). Die Auflösung
  bleibt immer voll; wird es eng, sinkt nur die Bildrate.
