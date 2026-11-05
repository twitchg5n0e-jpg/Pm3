#!/usr/bin/env bash
# Startet den Webserver der Web-App (server.py).
# Das C++-Hauptprogramm (Steuerung) laeuft separat und muss auf --steuerung-port erreichbar sein.
set -euo pipefail
cd "$(dirname "$0")"

# TODO: beim ersten Start eigene Zertifizierungsstelle in zertifikat/ erzeugen (openssl)

# TODO: Schleife: wenn sich die IP-Adressen aendern (Handy neu eingesteckt), Server-Zertifikat neu
#   ausstellen und server.py neu starten; Adressen fuer das Handy anzeigen
