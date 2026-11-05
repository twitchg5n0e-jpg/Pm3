// =============================================================================
// messung.hpp – Kraft und Weg der Probe
// =============================================================================
// Schnittstelle zur Hardware (siehe messung.cpp).
// TODO: Kraft von der Waegezelle lesen, Weg vom Motor (Schritte -> mm).
#pragma once

#include "probe.hpp"

class Messung {
public:
    void nullen();                       // Kraft und Weg auf 0 setzen (Probe ist eingespannt)
    void schritt(const Probe& probe);    // Motor faehrt um einen Messschritt weiter
    void stopp();                        // Motor sofort anhalten

    double weg() const { return weg_; }  // mm seit nullen()
    double kraft(const Probe& probe) const;   // N

private:
    double weg_ = 0;
};
