// =============================================================================
// webserver.hpp – Webserver fuer die Handy-Seite (mit der Bibliothek Mongoose)
// =============================================================================
//
//   HTTP  (config::HTTP_PORT)   Handy-Seite und /ca.crt (CA-Zertifikat zum Installieren)
//   HTTPS (config::HTTPS_PORT)  Handy-Seite; nur ueber HTTPS gibt das Handy die Kamera frei
//
//   WebSocket /steuerung   Handy -> Pruefstand: Befehle als Text  -> beiBefehl()
//                          Pruefstand -> Handy: JSON              <- anAlle()
//   WebSocket /stream      Video-Teile vom Handy, gespeichert in config::ORDNER_AUFNAHMEN
//
// Der Webserver kennt die Zustandsmaschine nicht; er ruft nur die beiden Callbacks auf.
#pragma once

#include <functional>
#include <map>
#include <string>

#include "mongoose.h"

class Webserver {
public:
    std::function<void(const std::string&)> beiBefehl;   // Befehl vom Handy erhalten
    std::function<void()> beiNeuemHandy;                 // Handy hat sich verbunden

    Webserver();
    ~Webserver();

    bool start();                           // Ports oeffnen; false, wenn HTTP nicht geht
    void poll(int ms);                      // Netzwerk bearbeiten, wartet hoechstens ms
    void anAlle(const std::string& json);   // an alle Handys auf /steuerung

private:
    // Art einer WebSocket-Verbindung, gespeichert in mg_connection::data[0]
    static constexpr char ART_STEUERUNG = 'S';
    static constexpr char ART_VIDEO = 'V';

    // Ein Video. Kann ueber mehrere Verbindungen kommen (WLAN-Abbruch), daher nach Sitzung.
    struct Aufnahme {
        std::string datei;
        unsigned long letzteNr = 0;   // Nummer des letzten gespeicherten Teils
        unsigned long bytes = 0;
    };

    static void ereignis(mg_connection* c, int ev, void* evData);   // alle Mongoose-Ereignisse
    void anfrage(mg_connection* c, mg_http_message* hm);            // HTTP-Anfrage verteilen
    void videoOeffnen(mg_connection* c, mg_http_message* hm);
    void videoTeil(mg_connection* c, mg_str daten);

    mg_mgr mgr_{};
    std::string zertifikat_, schluessel_;               // PEM-Text fuer TLS
    bool https_ = false;
    std::map<unsigned long, std::string> videoSitzung_; // Verbindungs-ID -> Sitzung
    std::map<std::string, Aufnahme> aufnahmen_;         // Sitzung -> Aufnahme
};
