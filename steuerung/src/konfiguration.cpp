#include "konfiguration.hpp"

bool Konfiguration::laden(const std::string& pfad) {
    (void)pfad;
    // TODO: Datei zeilenweise lesen, Kommentare ab # entfernen, "schluessel = wert" in werte_ speichern
    return false;
}

double Konfiguration::zahl(const std::string& schluessel, double standard) const {
    (void)schluessel;
    // TODO: Wert suchen und in eine Zahl umwandeln, sonst standard
    return standard;
}

int Konfiguration::ganzzahl(const std::string& schluessel, int standard) const {
    (void)schluessel;
    // TODO: wie zahl(), aber als Ganzzahl
    return standard;
}

std::string Konfiguration::text(const std::string& schluessel, const std::string& standard) const {
    (void)schluessel;
    // TODO: Wert suchen, sonst standard
    return standard;
}

double Konfiguration::schritteProMm() const {
    // TODO: motor_schritte * mikroschritte * untersetzung / spindelsteigung_mm
    return 0.0;
}
