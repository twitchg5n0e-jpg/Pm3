#pragma once

#include <fstream>
#include <string>

// Schreibt die Messwerte einer Pruefung als CSV-Datei (Trennzeichen ;) in den Datenordner.
class Messprotokoll {
public:
    explicit Messprotokoll(std::string ordner);

    // Beginnt eine neue Datei; kopf wird als Kommentarzeilen (#) vorangestellt. Gibt den Dateinamen zurueck.
    std::string starten(const std::string& kopf);
    void zeile(double zeitS, double wegMm, double kraftN, const std::string& optik);
    void beenden(const std::string& ergebnis);
    bool offen() const { return datei_.is_open(); }

private:
    std::string ordner_;
    std::ofstream datei_;
};
