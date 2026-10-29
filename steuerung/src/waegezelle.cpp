#include "waegezelle.hpp"

Waegezelle::Waegezelle(double faktor, int mittelwertAnzahl) : faktor_(faktor) {
    (void)mittelwertAnzahl;
    // TODO: Anzahl fuer den gleitenden Mittelwert merken
}

void Waegezelle::neuerWert(int32_t roh) {
    (void)roh;
    // TODO: Wert anhaengen, aeltesten verwerfen
}

double Waegezelle::kraft() const {
    // TODO: (Mittelwert - Nullpunkt) * Faktor
    return 0.0;
}

void Waegezelle::tara() {
    // TODO: Nullpunkt = aktueller Mittelwert
}

bool Waegezelle::kalibrieren(double bekannteKraft) {
    (void)bekannteKraft;
    // TODO: Faktor = bekannte Kraft / (Mittelwert - Nullpunkt)
    return false;
}
