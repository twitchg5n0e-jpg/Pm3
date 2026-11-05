// =============================================================================
// pruefstand.cpp – Zustandsmaschine: Befehle, Messablauf, CSV, USB-Export
// =============================================================================
#include "pruefstand.hpp"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <sstream>

namespace fs = std::filesystem;

const char* zustandName(Zustand z) {
    switch (z) {
        case Zustand::BEREIT:   return "BEREIT";
        case Zustand::KAMERA:   return "KAMERA";
        case Zustand::PRUEFUNG: return "PRUEFUNG";
        case Zustand::ENDE:     return "ENDE";
        case Zustand::FEHLER:   return "FEHLER";
    }
    return "?";
}

// -----------------------------------------------------------------------------
// Befehle
// -----------------------------------------------------------------------------

void Pruefstand::befehl(const std::string& zeile) {
    std::printf("<- %s\n", zeile.c_str());
    std::istringstream in(zeile);
    std::string cmd;
    in >> cmd;

    // Diese beiden Befehle gelten in jedem Zustand
    if (cmd == "set") return setze(in);
    if (cmd == "stopp") {   // Not-Halt: Motor immer sofort anhalten
        messung_.stopp();
        if (zustand_ == Zustand::PRUEFUNG) pruefungEnde("Abgebrochen");
        return;
    }

    // Uebergaenge: nur die Befehle, die im aktuellen Zustand erlaubt sind
    switch (zustand_) {
        case Zustand::BEREIT:
            if (cmd == "kamera") wechsle(Zustand::KAMERA);
            break;
        case Zustand::KAMERA:
            if (cmd == "zurueck") wechsle(Zustand::BEREIT);
            else if (cmd == "nullen") messung_.nullen();
            else if (cmd == "start") pruefungStart();
            break;
        case Zustand::PRUEFUNG:
            break;   // nur "stopp" (oben)
        case Zustand::ENDE:
        case Zustand::FEHLER:
            if (cmd == "quittieren") wechsle(Zustand::BEREIT);
            else if (cmd == "export") exportUsb();
            break;
    }
}

// "set <was> <werte>": Probendaten, die das Handy vor "kamera" schickt
void Pruefstand::setze(std::istringstream& in) {
    if (zustand_ == Zustand::PRUEFUNG) return melde("Waehrend der Pruefung nicht moeglich");
    std::string was;
    in >> was;
    if (was == "name") {
        in >> probe_.name;
        // Wird Dateiname: nur Buchstaben, Ziffern, '-' und '_' (verhindert z.B. "../")
        for (char& ch : probe_.name)
            if (!std::isalnum(static_cast<unsigned char>(ch)) && ch != '-') ch = '_';
    } else if (was == "probe") {
        in >> probe_.laenge >> probe_.breite >> probe_.dicke;
    } else if (was == "maxweg") {
        in >> probe_.maxWeg;
    } else if (was == "modus") {
        in >> probe_.modus;
    } else if (was == "farbe") {
        in >> probe_.farbe;
    }
}

void Pruefstand::wechsle(Zustand neu) {
    std::printf("   %s -> %s\n", zustandName(zustand_), zustandName(neu));
    zustand_ = neu;
    sendeZustand();
}

// -----------------------------------------------------------------------------
// Messablauf
// -----------------------------------------------------------------------------

void Pruefstand::pruefungStart() {
    // CSV: eine Kopfzeile mit den Probendaten, dann ein Messpunkt pro Zeile
    csvDatei_.clear();
    if (config::DATEN_SPEICHERN) {
        fs::create_directories(config::ORDNER_MESSUNGEN);
        csvDatei_ = std::string(config::ORDNER_MESSUNGEN) + "/" + probe_.name + ".csv";
        csv_.open(csvDatei_);
        csv_ << "# L=" << probe_.laenge << " b=" << probe_.breite << " d=" << probe_.dicke
             << " modus=" << probe_.modus << " farbe=" << probe_.farbe << "\n"
             << "weg_mm;kraft_N;dehnung_prozent;spannung_MPa\n";
    }

    maxKraft_ = 0;
    messung_.nullen();
    naechsteMessung_ = std::chrono::steady_clock::now();
    wechsle(Zustand::PRUEFUNG);
    sendeMesswert(0, 0);   // Startpunkt fuer das Diagramm
}

void Pruefstand::takt() {
    if (zustand_ != Zustand::PRUEFUNG) return;
    if (std::chrono::steady_clock::now() < naechsteMessung_) return;
    naechsteMessung_ += std::chrono::milliseconds(config::MESS_INTERVALL_MS);

    messung_.schritt(probe_);
    const double kraft = messung_.kraft(probe_);
    const double weg = messung_.weg();
    maxKraft_ = std::max(maxKraft_, kraft);

    if (csv_.is_open())
        csv_ << weg << ';' << kraft << ';' << probe_.dehnungProzent(weg) << ';' << probe_.spannungMPa(kraft) << '\n';
    sendeMesswert(kraft, weg);

    // Abbruch-Bedingungen
    const double dehnung = weg / probe_.laenge;
    if (weg >= probe_.maxWeg)
        pruefungEnde("Max. Weg erreicht");
    else if (dehnung > config::BRUCH_AB_DEHNUNG && kraft < maxKraft_ * config::BRUCH_KRAFT_ANTEIL)
        pruefungEnde("Bruch erkannt");
}

void Pruefstand::pruefungEnde(const std::string& grund) {
    messung_.stopp();
    csv_.close();
    wechsle(Zustand::ENDE);

    char json[256];
    std::snprintf(json, sizeof(json), "{\"ergebnis\":\"%s · Max. Kraft %.1f N · Max. Spannung %.2f MPa\"}",
                  grund.c_str(), maxKraft_, probe_.spannungMPa(maxKraft_));
    web_.anAlle(json);
    if (!csvDatei_.empty()) melde("CSV gespeichert: " + csvDatei_);
}

// CSV des letzten Tests auf den ersten eingesteckten USB-Stick kopieren
void Pruefstand::exportUsb() {
    if (csvDatei_.empty()) return melde("Export ist ausgeschaltet (config::DATEN_SPEICHERN)");
    const char* user = std::getenv("USER");
    for (const char* basis : config::USB_ORDNER) {
        std::error_code ec;
        for (const auto& stick : fs::directory_iterator(std::string(basis) + (user ? user : ""), ec)) {
            fs::copy_file(csvDatei_, stick.path() / fs::path(csvDatei_).filename(),
                          fs::copy_options::overwrite_existing, ec);
            return melde(ec ? "Export fehlgeschlagen: " + ec.message()
                            : "Auf USB kopiert: " + stick.path().string());
        }
    }
    melde("Kein USB-Stick gefunden");
}

// -----------------------------------------------------------------------------
// Nachrichten ans Handy
// -----------------------------------------------------------------------------

void Pruefstand::sendeZustand() {
    web_.anAlle(std::string("{\"zustand\":\"") + zustandName(zustand_) + "\"}");
}

void Pruefstand::sendeMesswert(double kraft, double weg) {
    char json[128];
    std::snprintf(json, sizeof(json), "{\"zustand\":\"%s\",\"kraft\":%.3f,\"weg\":%.4f}",
                  zustandName(zustand_), kraft, weg);
    web_.anAlle(json);
}

void Pruefstand::melde(const std::string& text) {
    std::printf("   %s\n", text.c_str());
    std::string json = "{\"ereignis\":\"";
    for (char ch : text) json += (ch == '"' || ch == '\\') ? '\'' : ch;   // JSON nicht kaputt machen
    web_.anAlle(json + "\"}");
}
