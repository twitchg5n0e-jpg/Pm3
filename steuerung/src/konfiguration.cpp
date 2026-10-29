#include "konfiguration.hpp"

#include <fstream>

namespace {

std::string trimmen(const std::string& s) {
    const auto anfang = s.find_first_not_of(" \t\r");
    if (anfang == std::string::npos) return "";
    const auto ende = s.find_last_not_of(" \t\r");
    return s.substr(anfang, ende - anfang + 1);
}

}  // namespace

bool Konfiguration::laden(const std::string& pfad) {
    std::ifstream datei(pfad);
    if (!datei) return false;
    std::string zeile;
    while (std::getline(datei, zeile)) {
        zeile = zeile.substr(0, zeile.find('#'));
        const auto gleich = zeile.find('=');
        if (gleich == std::string::npos) continue;
        const auto schluessel = trimmen(zeile.substr(0, gleich));
        if (!schluessel.empty()) werte_[schluessel] = trimmen(zeile.substr(gleich + 1));
    }
    return true;
}

double Konfiguration::zahl(const std::string& schluessel, double standard) const {
    const auto it = werte_.find(schluessel);
    if (it == werte_.end()) return standard;
    try {
        return std::stod(it->second);
    } catch (const std::exception&) {
        return standard;
    }
}

int Konfiguration::ganzzahl(const std::string& schluessel, int standard) const {
    return static_cast<int>(zahl(schluessel, standard));
}

std::string Konfiguration::text(const std::string& schluessel, const std::string& standard) const {
    const auto it = werte_.find(schluessel);
    return it == werte_.end() ? standard : it->second;
}

double Konfiguration::schritteProMm() const {
    return zahl("motor_schritte", 200) * zahl("mikroschritte", 8) * zahl("untersetzung", 3) /
           zahl("spindelsteigung_mm", 2);
}
