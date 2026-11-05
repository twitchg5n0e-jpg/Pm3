// =============================================================================
// pruefstand.hpp – Zustandsmaschine des Pruefstands
// =============================================================================
//
//   BEREIT ──kamera──> KAMERA ──start──> PRUEFUNG ──(Bruch/max. Weg/stopp)──> ENDE
//     ^                  │                                                    │
//     └────zurueck───────┘                                                    │
//     └───────────────────────────────quittieren──────────────────────────────┘
//   (FEHLER wird wie ENDE mit "quittieren" verlassen)
//
// Befehle vom Handy (Text ueber WebSocket /steuerung, gesendet von static/index.html):
//   set name <n> | set probe <L> <b> <d> | set modus zug | set maxweg <mm> | set farbe <f>
//   kamera | zurueck | nullen | start | stopp | export | quittieren
//
// Antworten ans Handy (JSON, an alle verbundenen Handys):
//   {"zustand":"PRUEFUNG","kraft":12.3,"weg":1.25}   Zustand, waehrend der Pruefung mit Messwerten
//   {"ereignis":"..."}                                Meldung (erscheint in der Browser-Konsole)
//   {"ergebnis":"..."}                                Zusammenfassung am Ende
#pragma once

#include <chrono>
#include <fstream>
#include <sstream>
#include <string>

#include "messung.hpp"
#include "probe.hpp"
#include "webserver.hpp"

enum class Zustand { BEREIT, KAMERA, PRUEFUNG, ENDE, FEHLER };

const char* zustandName(Zustand z);   // so wie die Handy-Seite ihn erwartet, z.B. "BEREIT"

class Pruefstand {
public:
    explicit Pruefstand(Webserver& web) : web_(web) {}

    void befehl(const std::string& zeile);   // einen Befehl vom Handy ausfuehren
    void takt();                             // regelmaessig aufrufen: misst waehrend PRUEFUNG
    void sendeZustand();                     // aktuellen Zustand an alle Handys

private:
    void setze(std::istringstream& rest);    // "set ..." auswerten
    void wechsle(Zustand neu);
    void pruefungStart();
    void pruefungEnde(const std::string& grund);
    void exportUsb();
    void sendeMesswert(double kraft, double weg);
    void melde(const std::string& text);

    Webserver& web_;
    Zustand zustand_ = Zustand::BEREIT;
    Probe probe_;
    Messung messung_;

    // Laufender Test
    std::ofstream csv_;
    std::string csvDatei_;          // letzte CSV, fuer "export"
    double maxKraft_ = 0;           // N, fuer Bruch-Erkennung und Ergebnis
    std::chrono::steady_clock::time_point naechsteMessung_;
};
