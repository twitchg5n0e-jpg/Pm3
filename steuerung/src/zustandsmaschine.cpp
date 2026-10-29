#include "zustandsmaschine.hpp"

#include "konfiguration.hpp"
#include "messprotokoll.hpp"
#include "motor.hpp"
#include "usb_export.hpp"

const char* zustandName(Zustand zustand) {
    switch (zustand) {
        case Zustand::Unreferenziert: return "UNREFERENZIERT";
        case Zustand::Referenzfahrt: return "REFERENZFAHRT";
        case Zustand::Bereit: return "BEREIT";
        case Zustand::Positionieren: return "POSITIONIEREN";
        case Zustand::Pruefung: return "PRUEFUNG";
        case Zustand::Ende: return "ENDE";
        case Zustand::Fehler: return "FEHLER";
    }
    return "?";
}

Zustandsmaschine::Zustandsmaschine(Motor& motor, Messprotokoll& protokoll, UsbExport& usb,
                                   const Konfiguration& konfig, Melden melden)
    : motor_(motor), protokoll_(protokoll), usb_(usb), melden_(std::move(melden)) {
    (void)konfig;
    // TODO: Werte aus der Konfiguration lesen (Verfahrweg, Geschwindigkeiten, Kraftgrenze, ...)
}

std::string Zustandsmaschine::befehl(const std::string& name, const std::string& argument) {
    (void)argument;
    // TODO: je nach Befehl und aktuellem Zustand wechseln oder ablehnen:
    //   referenz   -> REFERENZFAHRT          (aus UNREFERENZIERT, BEREIT, ENDE)
    //   start      -> PRUEFUNG               (aus BEREIT, ENDE; nur wenn referenziert)
    //   stopp      -> anhalten               (REFERENZFAHRT, POSITIONIEREN, PRUEFUNG)
    //   fahren <mm>-> POSITIONIEREN          (aus BEREIT, ENDE)
    //   quittieren -> BEREIT bzw. UNREFERENZIERT (aus ENDE bzw. FEHLER)
    //   nothalt    -> FEHLER                 (immer)
    //   export     -> alle Messdateien auf den USB-Stick
    //   set <name> <wert> -> Pruefparameter aendern (nicht waehrend PRUEFUNG)
    return "noch nicht umgesetzt: " + name;
}

void Zustandsmaschine::schritt(const Messwerte& m) {
    (void)m;
    // TODO: in jedem Zustand: Kraftgrenze ueberschritten -> FEHLER
    switch (zustand_) {
        case Zustand::Referenzfahrt:
            // TODO: Endschalter erreicht -> Nullpunkt setzen, freifahren (POSITIONIEREN)
            break;
        case Zustand::Positionieren:
            // TODO: mit Bremskurve zum Ziel fahren, am Ziel -> BEREIT
            break;
        case Zustand::Pruefung:
            // TODO: Messwert ins Protokoll schreiben, Spitzenkraft merken,
            //       Maximalkraft / Maximalweg / Bruch -> ENDE, Endschalter -> FEHLER
            break;
        case Zustand::Unreferenziert:
        case Zustand::Bereit:
        case Zustand::Ende:
        case Zustand::Fehler:
            break;
    }
}

void Zustandsmaschine::wechseln(Zustand neu) {
    zustand_ = neu;
    // TODO: beim Eintritt in den Zustand: Motor starten/anhalten, Protokoll oeffnen/schliessen
    melden_(std::string("Zustand: ") + zustandName(neu));
}

void Zustandsmaschine::fehler(const std::string& grund) {
    // TODO: Motor sofort anhalten und stromlos, Grund melden
    ergebnis_ = "Fehler: " + grund;
    wechseln(Zustand::Fehler);
}

void Zustandsmaschine::beenden(const std::string& grund) {
    // TODO: Ergebnis mit Spitzenkraft und Weg bilden, Protokoll schliessen, Datei auf den USB-Stick kopieren
    ergebnis_ = grund;
    wechseln(Zustand::Ende);
}
