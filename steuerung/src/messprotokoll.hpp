#pragma once

#include <string>

// Schreibt die Messwerte einer Pruefung als CSV-Datei (Trennzeichen ;) in den Datenordner.
class Messprotokoll {
public:
    explicit Messprotokoll(std::string ordner);

    // Beginnt eine neue Datei; kopf wird als Kommentarzeilen (#) vorangestellt. Gibt den Dateinamen zurueck.
    std::string starten(const std::string& kopf);
    void zeile(double zeitS, double wegMm, double kraftN, const std::string& optik);
    // Schliesst die Datei und gibt ihren Pfad zurueck.
    std::string beenden(const std::string& ergebnis);
    bool offen() const;

private:
    std::string ordner_;
    // TODO: offene Datei
};
