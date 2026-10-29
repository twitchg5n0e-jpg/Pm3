#include "messprotokoll.hpp"

#include <cstdio>
#include <ctime>
#include <filesystem>
#include <sstream>

Messprotokoll::Messprotokoll(std::string ordner) : ordner_(std::move(ordner)) {}

std::string Messprotokoll::starten(const std::string& kopf) {
    if (datei_.is_open()) datei_.close();
    std::filesystem::create_directories(ordner_);

    char name[32];
    const std::time_t jetzt = std::time(nullptr);
    std::strftime(name, sizeof(name), "%Y-%m-%d_%H-%M-%S.csv", std::localtime(&jetzt));
    const std::string pfad = ordner_ + "/" + name;

    datei_.open(pfad);
    std::istringstream zeilen(kopf);
    for (std::string z; std::getline(zeilen, z);) datei_ << "# " << z << '\n';
    datei_ << "zeit_s;weg_mm;kraft_n;optik\n";
    return name;
}

void Messprotokoll::zeile(double zeitS, double wegMm, double kraftN, const std::string& optik) {
    if (!datei_.is_open()) return;
    char puffer[96];
    std::snprintf(puffer, sizeof(puffer), "%.3f;%.4f;%.2f;", zeitS, wegMm, kraftN);
    datei_ << puffer << optik << '\n';
}

void Messprotokoll::beenden(const std::string& ergebnis) {
    if (!datei_.is_open()) return;
    datei_ << "# Ergebnis: " << ergebnis << '\n';
    datei_.close();
}
