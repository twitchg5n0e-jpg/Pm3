#pragma once

#include <cstdint>

// Rechnet die Rohwerte des HX711 in Newton um: gleitender Mittelwert, Nullpunkt (Tara) und Faktor.
class Waegezelle {
public:
    Waegezelle(double faktor, int mittelwertAnzahl);

    void neuerWert(int32_t roh);
    double kraft() const;  // in N

    void tara();
    // Bestimmt den Faktor aus einer bekannten Last in N. false, wenn kein Unterschied zum Nullpunkt messbar.
    bool kalibrieren(double bekannteKraft);
    double faktor() const { return faktor_; }

private:
    double faktor_;
    // TODO: Nullpunkt, letzte Rohwerte fuer den Mittelwert
};
