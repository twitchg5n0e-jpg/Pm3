#!/usr/bin/env python3
"""Webserver des Pruefstands: verbindet die Handy-Seite (web/) mit der Steuerung (steuerung/) und der
Bildanalyse (bildanalyse/).

HTTPS (Port 8443): Bedienoberflaeche. Browser geben die Kamera nur ueber HTTPS frei.
                   /stream     speichert den Full-HD-Video-Stream des Handys
                   /offer      Live-Bild per WebRTC, Bild fuer Bild an auswertung.verarbeite()
                   /steuerung  Befehle an das C++-Hauptprogramm, Status und Ereignisse zurueck
HTTP  (Port 8080): Einrichtungsseite, auf der das Handy einmalig das Zertifikat herunterlaedt.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "bildanalyse"))
import auswertung  # noqa: E402,F401


async def index(request):
    """Liefert web/index.html aus."""
    # TODO


async def setup_page(request):
    """Liefert web/einrichten.html aus."""
    # TODO


async def ca_cert(request):
    """Liefert das CA-Zertifikat zum Installieren auf dem Handy."""
    # TODO


async def stream(request):
    """WebSocket: nimmt die Video-Teile des Handys an und haengt sie an die Datei in daten/aufnahmen/.
    Jedes Teil hat eine Nummer; doppelte Teile nach einem Verbindungsabbruch verwerfen."""
    # TODO


class Steuerung:
    """Verbindung zum C++-Hauptprogramm (TCP 127.0.0.1:7000): Befehle hin, Status und Ereignisse
    (JSON-Zeilen) an alle verbundenen Handys."""

    def __init__(self, port):
        self.port = port
        # TODO: Verbindung, Liste der Handys, letzter Status

    async def lauf(self):
        """Verbindet sich mit der Steuerung (bei Abbruch alle 2 s neu) und verteilt jede Zeile."""
        # TODO

    def senden(self, befehl):
        """Schickt einen Befehl als Textzeile an die Steuerung."""
        # TODO


async def steuerung_ws(request):
    """WebSocket fuer die Taster und Live-Werte auf dem Handy."""
    # TODO


async def offer(request):
    """WebRTC-Verbindung fuer das Live-Bild aufbauen."""
    # TODO


async def live(track, channel, steuerung):
    """Gibt immer das neueste Bild an auswertung.verarbeite(). Ergebnis ans Handy (Datenkanal) und
    als "optik <text>" an die Steuerung."""
    # TODO


async def serve(args):
    """HTTPS- und HTTP-Server starten, Verbindung zur Steuerung starten."""
    # TODO


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--https-port", type=int, default=8443)
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--cert", required=True, help="Server-Zertifikat (von start.sh erzeugt)")
    parser.add_argument("--key", required=True, help="Schluessel zum Server-Zertifikat")
    parser.add_argument("--ca", required=True, help="CA-Zertifikat, das das Handy installiert")
    parser.add_argument("--out", default=str(ROOT / "daten" / "aufnahmen"), help="Ordner fuer die Videos")
    parser.add_argument("--steuerung-port", type=int, default=7000, help="Port des C++-Hauptprogramms")
    args = parser.parse_args()  # noqa: F841
    # TODO: asyncio.run(serve(args))


if __name__ == "__main__":
    main()
