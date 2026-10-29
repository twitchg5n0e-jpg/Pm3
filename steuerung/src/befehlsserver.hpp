#pragma once

#include <functional>
#include <string>

// TCP-Server nur fuer den Pi selbst (127.0.0.1). Der Webserver verbindet sich hierher, schickt Befehle
// als Textzeilen und bekommt Status und Ereignisse als JSON-Zeilen zurueck.
class Befehlsserver {
public:
    using Empfang = std::function<void(const std::string& zeile)>;

    Befehlsserver(int port, Empfang empfang);
    ~Befehlsserver();
    Befehlsserver(const Befehlsserver&) = delete;
    Befehlsserver& operator=(const Befehlsserver&) = delete;

    // Nimmt neue Verbindungen an und verarbeitet eingegangene Zeilen; wartet hoechstens wartezeitMs.
    void abarbeiten(int wartezeitMs);
    void senden(const std::string& zeile);  // an alle verbundenen Clients

private:
    int lauscher_;
    Empfang empfang_;
    // TODO: Liste der verbundenen Clients mit Empfangspuffer
};
