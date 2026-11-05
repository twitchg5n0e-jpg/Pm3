// =============================================================================
// messung.cpp – Kraft und Weg der Probe
// =============================================================================
// Hardware ist noch nicht angeschlossen: Kraft und Weg bleiben bei 0.
#include "messung.hpp"

void Messung::nullen() { weg_ = 0; }

void Messung::schritt(const Probe& /*probe*/) {
    // TODO: Motor ansteuern und echten Weg lesen (weg_ in mm)
}

void Messung::stopp() {
    // TODO: Motor anhalten
}

double Messung::kraft(const Probe& /*probe*/) const {
    // TODO: Waegezelle lesen (N)
    return 0;
}
