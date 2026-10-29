# Pm3 – Prüfstand

Zug-/Druck-Prüfstand mit Raspberry Pi 4. Ein C++-Hauptprogramm steuert Schrittmotor, Endschalter und Wägezelle
über eine Zustandsmaschine. Das Handy des Anwenders ist Bedienoberfläche und Kamera zugleich. Die Messdaten
werden als CSV gespeichert und auf einen USB-Stick kopiert.

**Stand: Gerüst.** Die Dateien enthalten Struktur, Funktionen und Kommentare (`TODO`), aber noch keinen
fertigen Code. Das C++-Gerüst lässt sich bereits bauen.

## Aufbau

| Ordner / Datei | Inhalt |
| --- | --- |
| `steuerung/` | **Hauptprogramm in C++** |
| `steuerung/src/main.cpp` | Start, Hauptschleife |
| `steuerung/src/zustandsmaschine.*` | Ablauf des Prüfstands (siehe unten) |
| `steuerung/src/motor.*` | Schrittimpulse mit Rampe in eigenem Thread |
| `steuerung/src/hardware.hpp`, `hardware_pi.cpp` | TMC2209, Endschalter, HX711 am Pi |
| `steuerung/src/hardware_sim.cpp` | Simulation zum Testen ohne Hardware |
| `steuerung/src/gpio.*` | GPIO-Zugriff über `/dev/gpiochip0` |
| `steuerung/src/waegezelle.*` | Rohwert → Newton, Tara, Kalibrieren |
| `steuerung/src/messprotokoll.*` | Messdaten als CSV |
| `steuerung/src/usb_export.*` | CSV-Dateien auf den USB-Stick kopieren |
| `steuerung/src/befehlsserver.*` | Verbindung zum Webserver (TCP 127.0.0.1:7000) |
| `steuerung/src/konfiguration.*`, `pruefstand.conf` | Einstellungen (Mechanik, Pins, Grenzen) |
| `webserver/server.py` | Python-Webserver: Handy ↔ Steuerung ↔ Bildanalyse, Video speichern |
| `web/index.html` | Bedienoberfläche auf dem Handy |
| `web/einrichten.html` | Zertifikat auf dem Handy installieren |
| `bildanalyse/auswertung.py` | Auswertung des Live-Bilds (Länge in mm) |
| `start.sh` | baut und startet alles |

```
Handy ──HTTPS/WebSocket──► webserver/server.py ──TCP 127.0.0.1:7000──► steuerung/ (C++)
  │  Taster, Live-Werte        │                                          ├─ Motor (TMC2209)
  │  Video + Live-Bild ───────►├─► bildanalyse/auswertung.py ──optik──►   ├─ Endschalter
  │                            └─► daten/aufnahmen/                       ├─ Wägezelle (HX711)
                                                                          ├─► daten/messdaten/*.csv
                                                                          └─► USB-Stick
```

## Zustandsmaschine

```
UNREFERENZIERT ──Referenz──► REFERENZFAHRT ──Endschalter──► POSITIONIEREN (freifahren) ──► BEREIT
BEREIT ──Start──► PRUEFUNG ──Maximalkraft / Maximalweg / Bruch / Stopp──► ENDE ──Quittieren──► BEREIT
BEREIT ──fahren <mm>──► POSITIONIEREN ──► BEREIT
jeder Zustand ──Kraftgrenze / Endschalter / NOT-HALT──► FEHLER ──Quittieren──► UNREFERENZIERT
```

Befehle vom Handy an die Steuerung (eine Textzeile pro Befehl):
`referenz`, `start`, `stopp`, `quittieren`, `nothalt`, `tara`, `fahren <mm>`, `kalibrieren <N>`, `export`,
`set modus zug|druck`, `set geschwindigkeit <mm/min>`, `set maxkraft <N>`, `set maxweg <mm>`, `set bruch <%>`.

Antworten der Steuerung (eine JSON-Zeile): `{"typ":"status", ...}` alle 100 ms und `{"typ":"ereignis","text":...}`.

## Messdaten und USB-Export

Jede Prüfung wird als CSV in `daten/messdaten/` geschrieben (Trennzeichen `;`):

```
# Modus: Zug
# Geschwindigkeit: 5 mm/min
# ...
zeit_s;weg_mm;kraft_n;optik
0.012;0.0010;0.35;
...
# Ergebnis: Bruch erkannt, Spitzenkraft 397.4 N bei Weg 6.060 mm
```

Am Ende der Prüfung wird die Datei automatisch auf einen eingesteckten USB-Stick kopiert (Ordner
`pruefstand/` auf dem Stick). Der Taster **CSV auf USB-Stick** kopiert alle Messungen, die noch fehlen.
Raspberry Pi OS hängt Sticks unter `/media/<benutzer>/<name>` ein (`usb_ordner` in `pruefstand.conf`).

## Verkabelung (Standard in `steuerung/pruefstand.conf`)

| Teil | Anschluss | Pi 4 (BCM) |
| --- | --- | --- |
| TMC2209 | STEP / DIR / EN | GPIO 20 / 21 / 16 |
| TMC2209 | VIO / GND | 3,3 V / GND |
| TMC2209 | VM | 24 V über Sicherung, Elko 100 µF / 35 V direkt am Treiber |
| Motor Beckhoff AS1020 (M12) | Pin 1 / 2 / 3 / 4 | TMC2209 A1 / A2 / B1 / B2 |
| Endschalter | gegen GND | GPIO 26 (interner Pull-up) |
| HX711 | DOUT / SCK | GPIO 5 / 6 |

## Bauen

Auf dem Pi:

```bash
sudo apt install -y cmake g++ python3-venv python3-aiohttp python3-numpy python3-opencv openssl avahi-daemon usbmuxd
```

```bash
cmake -S steuerung -B steuerung/build && cmake --build steuerung/build
```
