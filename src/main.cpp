// =============================================================================
// main.cpp – Hauptprogramm des Pruefstands
// =============================================================================
// Startet den Webserver fuer die Handy-Seite und verbindet ihn mit der Zustandsmaschine.
// Danach laeuft eine einzige Schleife: Netzwerk bearbeiten, dann messen (falls Test laeuft).
//
//   make run      ->  http://localhost:8080
//   ./start.sh    ->  zusaetzlich HTTPS fuers Handy
#include <cstdio>

#include "config.hpp"
#include "pruefstand.hpp"
#include "webserver.hpp"

int main() {
    std::setvbuf(stdout, nullptr, _IOLBF, 0);   // Ausgabe sofort zeigen, auch in eine Datei/Log

    Webserver web;
    Pruefstand stand(web);

    // Webserver -> Zustandsmaschine
    web.beiBefehl = [&](const std::string& zeile) { stand.befehl(zeile); };
    web.beiNeuemHandy = [&] { stand.sendeZustand(); };   // neues Handy sieht sofort den Zustand

    if (!web.start()) return 1;

    while (true) {
        web.poll(config::POLL_MS);
        stand.takt();
    }
}
