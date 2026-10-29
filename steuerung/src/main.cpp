// Hauptprogramm des Pruefstands: steuert Motor, Endschalter und Waegezelle ueber eine Zustandsmaschine,
// schreibt die Messwerte als CSV und nimmt Befehle vom Webserver entgegen.
//
//   pruefstand [--konfig pruefstand.conf] [--daten daten/messdaten] [--sim]

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

#include "befehlsserver.hpp"
#include "hardware.hpp"
#include "konfiguration.hpp"
#include "messprotokoll.hpp"
#include "motor.hpp"
#include "waegezelle.hpp"
#include "zustandsmaschine.hpp"

namespace {

std::atomic<bool> laufen{true};

void beenden(int) { laufen = false; }

std::string jsonText(const std::string& text) {
    std::string aus = "\"";
    for (const char c : text) {
        if (c == '"' || c == '\\') aus += '\\';
        if (static_cast<unsigned char>(c) >= 0x20) aus += c;
    }
    return aus + '"';
}

std::string statusJson(const Zustandsmaschine& sm, const Waegezelle& waage) {
    const auto& p = sm.parameter();
    char zahlen[320];
    std::snprintf(zahlen, sizeof(zahlen),
                  "\"kraft\":%.2f,\"position\":%.4f,\"weg\":%.4f,\"spitze\":%.2f,\"geschwindigkeit\":%g,"
                  "\"maxkraft\":%g,\"maxweg\":%g,\"bruch\":%g",
                  waage.kraft(), sm.positionMm(), sm.zustand() == Zustand::Pruefung ? sm.wegMm() : 0.0,
                  sm.spitzenkraftN(), p.geschwindigkeitMmMin, p.maxKraftN, p.maxWegMm, p.bruchProzent);
    return std::string("{\"typ\":\"status\",\"zustand\":\"") + zustandName(sm.zustand()) +
           "\",\"referenziert\":" + (sm.referenziert() ? "true" : "false") +
           ",\"modus\":" + (p.zug ? "\"zug\"" : "\"druck\"") + "," + zahlen +
           ",\"ergebnis\":" + jsonText(sm.ergebnis()) + ",\"datei\":" + jsonText(sm.datei()) + "}";
}

std::string trimmen(const std::string& s) {
    const auto anfang = s.find_first_not_of(" \t");
    return anfang == std::string::npos ? "" : s.substr(anfang, s.find_last_not_of(" \t") - anfang + 1);
}

}  // namespace

int main(int argc, char** argv) {
    std::string konfigPfad = "pruefstand.conf", datenOrdner = "daten/messdaten";
    bool simulation = false;
    for (int i = 1; i < argc; ++i) {
        const std::string arg = argv[i];
        if (arg == "--sim") simulation = true;
        else if (arg == "--konfig" && i + 1 < argc) konfigPfad = argv[++i];
        else if (arg == "--daten" && i + 1 < argc) datenOrdner = argv[++i];
        else {
            std::cerr << "Aufruf: pruefstand [--konfig datei] [--daten ordner] [--sim]\n";
            return 2;
        }
    }

    Konfiguration konfig;
    if (!konfig.laden(konfigPfad)) {
        std::cerr << "Konfiguration " << konfigPfad << " nicht gefunden\n";
        return 1;
    }
    const auto slash = konfigPfad.find_last_of('/');
    const std::string kalibrierPfad =
        (slash == std::string::npos ? "" : konfigPfad.substr(0, slash + 1)) + "kalibrierung.conf";
    konfig.laden(kalibrierPfad);  // optional, ueberschreibt waegezelle_faktor

    std::signal(SIGINT, beenden);
    std::signal(SIGTERM, beenden);

    try {
        auto hardware = simulation ? erstelleSimulation(konfig) : erstellePiHardware(konfig);
        const double schritteProMm = konfig.schritteProMm();
        Motor motor(*hardware, konfig.zahl("beschleunigung_mm_s2", 5) * schritteProMm);
        Waegezelle waage(konfig.zahl("waegezelle_faktor", 0.0001), konfig.ganzzahl("waegezelle_mittelwert", 4));
        Messprotokoll protokoll(datenOrdner);

        Befehlsserver* server = nullptr;
        auto melden = [&](const std::string& text) {
            std::cout << text << std::endl;
            if (server) server->senden("{\"typ\":\"ereignis\",\"text\":" + jsonText(text) + "}");
        };
        Zustandsmaschine sm(motor, protokoll, konfig, melden);

        auto befehl = [&](const std::string& zeile) {
            std::istringstream ein(zeile);
            std::string name, argument;
            ein >> name;
            std::getline(ein, argument);
            argument = trimmen(argument);

            std::string ablehnung;
            if (name == "optik") {
                sm.optikSetzen(argument);  // Ergebnis der Bildanalyse, landet in der CSV-Datei
                return;
            } else if (name == "tara") {
                if (sm.zustand() == Zustand::Pruefung) ablehnung = "nicht waehrend einer Pruefung";
                else {
                    waage.tara();
                    melden("Tara gesetzt");
                }
            } else if (name == "kalibrieren") {
                double kraft = 0.0;
                try {
                    kraft = std::stod(argument);
                } catch (const std::exception&) {
                    ablehnung = "bekannte Kraft in N angeben, z.B. kalibrieren 98.1";
                }
                if (ablehnung.empty() && !waage.kalibrieren(kraft)) ablehnung = "keine Last messbar, zuerst tara ohne Last";
                if (ablehnung.empty()) {
                    std::ofstream(kalibrierPfad) << "waegezelle_faktor = " << waage.faktor() << '\n';
                    melden("Kalibriert, Faktor " + std::to_string(waage.faktor()) + " gespeichert");
                }
            } else {
                ablehnung = sm.befehl(name, argument);
            }
            if (!ablehnung.empty()) melden("Abgelehnt: " + zeile + " (" + ablehnung + ")");
        };

        Befehlsserver befehlsserver(konfig.ganzzahl("port", 7000), befehl);
        server = &befehlsserver;
        melden(simulation ? "Steuerung gestartet (Simulation)" : "Steuerung gestartet");

        auto naechsterStatus = std::chrono::steady_clock::now();
        while (laufen) {
            befehlsserver.abarbeiten(1);
            const auto roh = hardware->waegezelleLesen();
            if (roh) waage.neuerWert(*roh);
            sm.schritt({waage.kraft(), roh.has_value(), hardware->endschalter()});

            const auto jetzt = std::chrono::steady_clock::now();
            if (jetzt >= naechsterStatus) {
                befehlsserver.senden(statusJson(sm, waage));
                naechsterStatus = jetzt + std::chrono::milliseconds(100);
            }
        }
        sm.befehl("stopp", "");
        server = nullptr;
    } catch (const std::exception& e) {
        std::cerr << "Fehler: " << e.what() << '\n';
        return 1;
    }
    return 0;
}
