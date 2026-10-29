#!/usr/bin/env bash
# Startet den Pruefstand: das C++-Hauptprogramm (steuerung/) und den Webserver (webserver/).
# Mit SIM=1 ./start.sh laeuft die Steuerung ohne Hardware in der Simulation.
set -euo pipefail
cd "$(dirname "$0")"

# TODO: beim ersten Start eigene Zertifizierungsstelle in zertifikat/ erzeugen (openssl)

# TODO: Hauptprogramm bauen:
#   cmake -S steuerung -B steuerung/build && cmake --build steuerung/build

# TODO: Hauptprogramm starten:
#   steuerung/build/pruefstand --konfig steuerung/pruefstand.conf --daten daten/messdaten ${SIM:+--sim} &

# TODO: Schleife: wenn sich die IP-Adressen aendern (Handy neu eingesteckt), Server-Zertifikat neu
#   ausstellen und webserver/server.py neu starten; Adressen fuer das Handy anzeigen
