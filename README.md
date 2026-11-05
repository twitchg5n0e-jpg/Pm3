# Pm3 – Prüfstand: Web-App

Bedienoberfläche des Zug-/Druck-Prüfstands fürs Handy. Ein einziges C++-Programm enthält die
Zustandsmaschine und den Webserver ([Mongoose](https://github.com/cesanta/mongoose)).

```
src/
  main.cpp             Hauptschleife: Webserver + Zustandsmaschine
  config.hpp           alle Einstellwerte (Ports, Pfade, Messrate, Simulation) mit Herkunft
  pruefstand.hpp/.cpp  Zustandsmaschine BEREIT → KAMERA → PRUEFUNG → ENDE, CSV, USB-Export
  probe.hpp            Daten der Probe (kommen vom Handy)
  messung.hpp/.cpp     Kraft und Weg – noch SIMULIERT (TODO: Wägezelle, Motor)
  webserver.hpp/.cpp   HTTP/HTTPS, WebSocket /steuerung und /stream
lib/mongoose/          Webserver-Bibliothek (Version 7.23, GPLv2)
static/index.html      Handy-Seite
start.sh               erzeugt die Zertifikate, baut und startet
```

```sh
make run        # am PC: http://localhost:8080
./start.sh      # mit HTTPS fürs Handy: https://<IP>:8443
```

Ohne Prüfstand: `index.html?demo` simuliert alles im Browser.
Daten landen in `daten/messungen/` (CSV) und `daten/aufnahmen/` (Video).
