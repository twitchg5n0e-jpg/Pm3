// Hauptprogramm des Pruefstands: steuert Motor, Endschalter und Waegezelle ueber eine Zustandsmaschine,
// schreibt die Messwerte als CSV, kopiert sie auf einen USB-Stick und nimmt Befehle vom Webserver entgegen.
//
//   pruefstand [--konfig pruefstand.conf] [--daten daten/messdaten] [--sim]

#include "befehlsserver.hpp"
#include "hardware.hpp"
#include "konfiguration.hpp"
#include "messprotokoll.hpp"
#include "motor.hpp"
#include "usb_export.hpp"
#include "waegezelle.hpp"
#include "zustandsmaschine.hpp"

int main(int argc, char** argv) {
    (void)argc;
    (void)argv;

    // TODO: Argumente lesen (--konfig, --daten, --sim)
    // TODO: Konfiguration laden (pruefstand.conf, danach kalibrierung.conf)
    // TODO: Hardware erstellen: erstellePiHardware() oder erstelleSimulation()
    // TODO: Motor, Waegezelle, Messprotokoll, UsbExport und Zustandsmaschine anlegen
    // TODO: Befehlsserver starten; empfangene Befehle an die Zustandsmaschine weitergeben
    //       (tara, kalibrieren und optik hier direkt behandeln)

    // TODO: Hauptschleife, bis SIGINT/SIGTERM kommt:
    //       - Befehle abarbeiten
    //       - Waegezelle lesen
    //       - Zustandsmaschine einen Schritt weiterschalten
    //       - alle 100 ms den Status als JSON an den Webserver senden

    // TODO: beim Beenden den Motor anhalten und stromlos schalten
    return 0;
}
