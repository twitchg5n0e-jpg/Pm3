#pragma once

#include <map>
#include <string>

// Einstellungen aus einer Textdatei: eine Zeile "schluessel = wert", Kommentare mit #.
class Konfiguration {
public:
    // Liest die Datei und ueberschreibt bereits geladene Werte. false, wenn sie fehlt.
    bool laden(const std::string& pfad);

    double zahl(const std::string& schluessel, double standard) const;
    int ganzzahl(const std::string& schluessel, int standard) const;
    std::string text(const std::string& schluessel, const std::string& standard) const;

    // Motorschritte pro Millimeter Spindelweg, aus Motor, Mikroschritten, Untersetzung und Steigung.
    double schritteProMm() const;

private:
    std::map<std::string, std::string> werte_;
};
