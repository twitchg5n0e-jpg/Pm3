#include "messprotokoll.hpp"

Messprotokoll::Messprotokoll(std::string ordner) : ordner_(std::move(ordner)) {}

std::string Messprotokoll::starten(const std::string& kopf) {
    (void)kopf;
    // TODO: Ordner anlegen, Datei JJJJ-MM-TT_hh-mm-ss.csv oeffnen,
    //       Kopf als Kommentarzeilen (#) schreiben, dann die Spalten: zeit_s;weg_mm;kraft_n;optik
    return "";
}

void Messprotokoll::zeile(double zeitS, double wegMm, double kraftN, const std::string& optik) {
    (void)zeitS;
    (void)wegMm;
    (void)kraftN;
    (void)optik;
    // TODO: eine Zeile anhaengen
}

std::string Messprotokoll::beenden(const std::string& ergebnis) {
    (void)ergebnis;
    // TODO: Ergebnis als Kommentarzeile schreiben, Datei schliessen, Pfad zurueckgeben (fuer den USB-Export)
    return "";
}

bool Messprotokoll::offen() const {
    // TODO
    return false;
}
