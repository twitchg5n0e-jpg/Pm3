#pragma once

#include <string>

// Kopiert die CSV-Dateien der Messungen auf einen eingesteckten USB-Stick.
// Raspberry Pi OS haengt Sticks automatisch unter /media/<benutzer>/<name> ein.
class UsbExport {
public:
    explicit UsbExport(std::string suchordner);  // z.B. "/media"

    // Pfad des ersten eingesteckten Sticks, leer wenn keiner da ist.
    std::string stickFinden() const;

    // Kopiert eine Messdatei in den Ordner "pruefstand" auf dem Stick. false, wenn kein Stick da ist.
    bool kopieren(const std::string& datei) const;

    // Kopiert alle Messdateien, die noch nicht auf dem Stick sind. Gibt die Anzahl zurueck.
    int alleKopieren(const std::string& datenOrdner) const;

private:
    std::string suchordner_;
};
