# Pm3 – Prüfstand: Web-App

Bedienoberfläche des Zug-/Druck-Prüfstands fürs Handy. Ein einziges C++-Programm enthält die
Zustandsmaschine und den Webserver ([Mongoose](https://github.com/cesanta/mongoose)).

```
src/
  main.cpp             Hauptschleife: Webserver + Zustandsmaschine
  config.hpp           alle Einstellwerte (Ports, Pfade, Messrate, Bruch, Probe) mit Herkunft
  pruefstand.hpp/.cpp  Zustandsmaschine BEREIT → KAMERA → PRUEFUNG → ENDE, CSV, USB-Export
  probe.hpp            Daten der Probe (kommen vom Handy)
  messung.hpp/.cpp     Kraft und Weg – noch SIMULIERT (TODO: Wägezelle, Motor)
  webserver.hpp/.cpp   HTTP/HTTPS, WebSocket /steuerung und /stream, /ca.crt
lib/mongoose/          Webserver-Bibliothek (Version 7.23, GPLv2)
static/index.html      Handy-Seite
zertifikat/            HTTPS-Zertifikate, von start.sh erzeugt (siehe zertifikat/README.md)
Makefile               baut ./pruefstand
start.sh               erzeugt die Zertifikate, baut und startet
```

Benötigt: `g++`, `make`, `openssl` (nur für `start.sh`).

```sh
make run        # am PC: http://localhost:8080
./start.sh      # mit HTTPS fürs Handy: https://<IP>:8443
make clean      # löscht build/ und ./pruefstand
```

Handy einmalig einrichten: `http://<IP>:8080/ca.crt` laden und dem Zertifikat vertrauen
(Details in [start.sh](start.sh) und [zertifikat/README.md](zertifikat/README.md)). Nur über HTTPS
gibt der Browser die Kamera frei.

Ohne Prüfstand: `index.html?demo` simuliert alles im Browser.

Daten speichern ist zurzeit **ausgeschaltet** (`DATEN_SPEICHERN = false` in
[src/config.hpp](src/config.hpp), gleicher Schalter oben in `static/index.html`). Eingeschaltet
landen sie in `daten/messungen/` (CSV) und `daten/aufnahmen/` (Video) und werden auf einen
USB-Stick exportiert.
