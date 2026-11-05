// =============================================================================
// probe.hpp – Daten der eingespannten Probe
// =============================================================================
// Die Werte kommen vom Handy (Befehle "set ..." vor dem Test, siehe pruefstand.cpp).
#pragma once

#include <string>

#include "config.hpp"

struct Probe {
    std::string name = "test";                        // set name    – Testname, wird Dateiname
    double laenge = config::PROBE_LAENGE_MM;          // set probe   – L in mm
    double breite = config::PROBE_BREITE_MM;          //             – b in mm
    double dicke = config::PROBE_DICKE_MM;            //             – d in mm
    double maxWeg = config::PROBE_MAX_WEG_MM;         // set maxweg  – Abbruch bei diesem Weg (mm)
    std::string modus = "zug";                        // set modus   – "zug" (spaeter evtl. "druck")
    std::string farbe = "schwarz";                    // set farbe   – fuer die Bildauswertung

    double querschnitt() const { return breite * dicke; }               // A in mm²
    double dehnungProzent(double weg) const { return weg / laenge * 100; }
    double spannungMPa(double kraft) const { return kraft / querschnitt(); }   // N/mm² = MPa
};
