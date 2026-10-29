#include "waegezelle.hpp"

#include <algorithm>
#include <cmath>

Waegezelle::Waegezelle(double faktor, int mittelwertAnzahl)
    : faktor_(faktor), anzahl_(static_cast<std::size_t>(std::max(1, mittelwertAnzahl))) {}

void Waegezelle::neuerWert(int32_t roh) {
    werte_.push_back(roh);
    if (werte_.size() > anzahl_) werte_.pop_front();
}

double Waegezelle::mittelwert() const {
    if (werte_.empty()) return nullpunkt_;
    double summe = 0.0;
    for (const auto w : werte_) summe += w;
    return summe / werte_.size();
}

double Waegezelle::kraft() const { return (mittelwert() - nullpunkt_) * faktor_; }

void Waegezelle::tara() { nullpunkt_ = mittelwert(); }

bool Waegezelle::kalibrieren(double bekannteKraft) {
    const double differenz = mittelwert() - nullpunkt_;
    if (std::abs(differenz) < 1.0) return false;
    faktor_ = bekannteKraft / differenz;
    return true;
}
