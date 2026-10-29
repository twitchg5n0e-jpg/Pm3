#include "befehlsserver.hpp"

Befehlsserver::Befehlsserver(int port, Empfang empfang) : lauscher_(-1), empfang_(std::move(empfang)) {
    (void)port;
    // TODO: TCP-Socket auf 127.0.0.1:port oeffnen (nur lokal erreichbar), nicht blockierend
}

Befehlsserver::~Befehlsserver() {
    // TODO: alle Verbindungen und den Socket schliessen
}

void Befehlsserver::abarbeiten(int wartezeitMs) {
    (void)wartezeitMs;
    // TODO: mit poll() warten, neue Verbindungen annehmen, Daten lesen,
    //       jede vollstaendige Zeile an empfang_ geben
}

void Befehlsserver::senden(const std::string& zeile) {
    (void)zeile;
    // TODO: Zeile + '\n' an alle verbundenen Clients schicken
}
