// =============================================================================
// webserver.cpp – HTTP/HTTPS, WebSocket /steuerung und /stream
// =============================================================================
#include "webserver.hpp"

#include <cctype>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <sstream>

#include "config.hpp"

namespace fs = std::filesystem;

namespace {

std::string dateiLesen(const std::string& pfad) {
    std::ifstream f(pfad, std::ios::binary);
    std::stringstream s;
    s << f.rdbuf();
    return s.str();
}

// Wert aus der URL, z.B. "session" aus /stream?session=abc
std::string urlWert(mg_http_message* hm, const char* name) {
    char buf[200] = "";
    mg_http_get_var(&hm->query, name, buf, sizeof(buf));
    return buf;
}

// Nur Buchstaben, Ziffern, '_' und '-' in Dateinamen zulassen (verhindert z.B. "../")
std::string sichererName(const std::string& s) {
    std::string r;
    for (char ch : s)
        r += (std::isalnum(static_cast<unsigned char>(ch)) || ch == '_' || ch == '-') ? ch : '_';
    return r.empty() ? "aufnahme" : r;
}

bool ist(mg_http_message* hm, const char* pfad) { return mg_match(hm->uri, mg_str(pfad), nullptr); }

}  // namespace

// -----------------------------------------------------------------------------
// Start und Hauptschleife
// -----------------------------------------------------------------------------

Webserver::Webserver() { mg_mgr_init(&mgr_); }
Webserver::~Webserver() { mg_mgr_free(&mgr_); }

bool Webserver::start() {
    mg_log_set(MG_LL_ERROR);

    std::string url = "http://0.0.0.0:" + std::to_string(config::HTTP_PORT);
    if (!mg_http_listen(&mgr_, url.c_str(), ereignis, this)) {
        std::fprintf(stderr, "Webserver: Port %d nicht verfuegbar\n", config::HTTP_PORT);
        return false;
    }
    std::printf("Webserver: http://localhost:%d\n", config::HTTP_PORT);

    // HTTPS nur, wenn start.sh die Zertifikate erzeugt hat
    if (!fs::exists(config::DATEI_ZERTIFIKAT) || !fs::exists(config::DATEI_SCHLUESSEL)) {
        std::printf("Webserver: kein %s -> nur HTTP (Kamera nur auf localhost)\n", config::DATEI_ZERTIFIKAT);
        return true;
    }
    zertifikat_ = dateiLesen(config::DATEI_ZERTIFIKAT);
    schluessel_ = dateiLesen(config::DATEI_SCHLUESSEL);
    url = "https://0.0.0.0:" + std::to_string(config::HTTPS_PORT);
    https_ = mg_http_listen(&mgr_, url.c_str(), ereignis, this) != nullptr;
    if (https_) std::printf("Webserver: https://<IP>:%d (fuers Handy)\n", config::HTTPS_PORT);
    return true;
}

void Webserver::poll(int ms) { mg_mgr_poll(&mgr_, ms); }

void Webserver::anAlle(const std::string& json) {
    for (mg_connection* c = mgr_.conns; c != nullptr; c = c->next)
        if (c->is_websocket && c->data[0] == ART_STEUERUNG)
            mg_ws_send(c, json.data(), json.size(), WEBSOCKET_OP_TEXT);
}

// -----------------------------------------------------------------------------
// Ereignisse von Mongoose (fuer alle Verbindungen; fn_data zeigt auf den Webserver)
// -----------------------------------------------------------------------------

void Webserver::ereignis(mg_connection* c, int ev, void* evData) {
    auto* self = static_cast<Webserver*>(c->fn_data);

    if (ev == MG_EV_ACCEPT) {
        // Neue Verbindung auf dem HTTPS-Port: TLS einschalten
        if (self->https_ && c->loc.port == mg_htons(static_cast<uint16_t>(config::HTTPS_PORT))) {
            mg_tls_opts opts{};
            opts.cert = mg_str_n(self->zertifikat_.data(), self->zertifikat_.size());
            opts.key = mg_str_n(self->schluessel_.data(), self->schluessel_.size());
            mg_tls_init(c, &opts);
        }
    } else if (ev == MG_EV_HTTP_MSG) {
        self->anfrage(c, static_cast<mg_http_message*>(evData));
    } else if (ev == MG_EV_WS_MSG) {
        auto* wm = static_cast<mg_ws_message*>(evData);
        if (c->data[0] == ART_STEUERUNG && self->beiBefehl)
            self->beiBefehl(std::string(wm->data.buf, wm->data.len));
        else if (c->data[0] == ART_VIDEO)
            self->videoTeil(c, wm->data);
    } else if (ev == MG_EV_CLOSE) {
        self->videoSitzung_.erase(c->id);
    }
}

void Webserver::anfrage(mg_connection* c, mg_http_message* hm) {
    if (ist(hm, "/steuerung")) {
        mg_ws_upgrade(c, hm, nullptr);
        c->data[0] = ART_STEUERUNG;
        if (beiNeuemHandy) beiNeuemHandy();
    } else if (ist(hm, "/stream")) {
        if (config::DATEN_SPEICHERN) videoOeffnen(c, hm);
        else mg_http_reply(c, 403, "", "Aufnahme ausgeschaltet\n");
    } else if (ist(hm, "/csv")) {
        // /csv?name=<Testname>: CSV des Tests zum Herunterladen aufs Handy
        const std::string name = sichererName(urlWert(hm, "name"));
        const std::string datei = std::string(config::ORDNER_MESSUNGEN) + "/" + name + ".csv";
        if (!fs::exists(datei)) return mg_http_reply(c, 404, "", "Keine CSV fuer %s\n", name.c_str());
        const std::string kopf = "Content-Disposition: attachment; filename=\"" + name + ".csv\"\r\n"
                                 "Cache-Control: no-cache\r\n";
        mg_http_serve_opts opts{};
        opts.mime_types = "csv=text/csv";
        opts.extra_headers = kopf.c_str();
        mg_http_serve_file(c, hm, datei.c_str(), &opts);
    } else if (ist(hm, "/ca.crt")) {
        mg_http_serve_opts opts{};
        opts.mime_types = "crt=application/x-x509-ca-cert";   // damit das Handy es installiert
        mg_http_serve_file(c, hm, config::DATEI_CA, &opts);
    } else if (ist(hm, "/")) {
        // HTTPS: direkt zur Bedienseite. HTTP: zuerst die Verbinden-Seite, die prueft, ob das Handy
        // dem Zertifikat schon vertraut, und dann auf HTTPS weiterleitet (Kamera geht nur mit HTTPS).
        if (c->is_tls) mg_http_reply(c, 302, "Location: /index.html\r\n", "");
        else {
            const std::string ziel = "Location: /verbinden.html?https=" + std::to_string(config::HTTPS_PORT) + "\r\n";
            mg_http_reply(c, 302, ziel.c_str(), "");
        }
    } else {
        mg_http_serve_opts opts{};
        opts.root_dir = config::ORDNER_SEITEN;
        opts.extra_headers = "Cache-Control: no-cache\r\n";   // Aenderungen an index.html sofort sehen
        mg_http_serve_dir(c, hm, &opts);
    }
}

// -----------------------------------------------------------------------------
// Video vom Handy (siehe aufnahmeStart() und sendeTeil() in static/index.html)
// -----------------------------------------------------------------------------

// /stream?session=<name>&ext=webm|mp4&bereich=x,y,b,h&farbe=schwarz|weiss
void Webserver::videoOeffnen(mg_connection* c, mg_http_message* hm) {
    const std::string sitzung = sichererName(urlWert(hm, "session"));
    const std::string ordner = config::ORDNER_AUFNAHMEN;

    Aufnahme& a = aufnahmen_[sitzung];
    if (a.datei.empty()) {   // erste Verbindung dieser Aufnahme
        fs::create_directories(ordner);
        a.datei = ordner + "/" + sitzung + (urlWert(hm, "ext") == "mp4" ? ".mp4" : ".webm");
        // Bildbereich und Farbe der Probe fuer die spaetere Auswertung daneben speichern
        std::ofstream info(ordner + "/" + sitzung + ".txt");
        info << "bereich=" << urlWert(hm, "bereich") << "\n"
             << "farbe=" << urlWert(hm, "farbe") << "\n";
        std::printf("Aufnahme: %s\n", a.datei.c_str());
    }
    mg_ws_upgrade(c, hm, nullptr);
    c->data[0] = ART_VIDEO;
    videoSitzung_[c->id] = sitzung;
}

// Ein Teil: 4 Byte Teilnummer (big endian, ab 1), danach die Videodaten.
// Antwort {"seq":<letzte gespeicherte Nummer>,"total":<Bytes>}: das Handy loescht dann alles
// bis seq aus seiner Warteschlange. Nach einem Abbruch schickt es Teile doppelt -> verwerfen.
void Webserver::videoTeil(mg_connection* c, mg_str daten) {
    auto it = videoSitzung_.find(c->id);
    if (it == videoSitzung_.end() || daten.len < 4) return;
    Aufnahme& a = aufnahmen_[it->second];

    const auto* b = reinterpret_cast<const unsigned char*>(daten.buf);
    const unsigned long nr = (static_cast<unsigned long>(b[0]) << 24) | (static_cast<unsigned long>(b[1]) << 16) |
                             (static_cast<unsigned long>(b[2]) << 8) | static_cast<unsigned long>(b[3]);

    if (nr == a.letzteNr + 1) {
        std::ofstream f(a.datei, std::ios::binary | std::ios::app);
        f.write(daten.buf + 4, static_cast<std::streamsize>(daten.len - 4));
        a.letzteNr = nr;
        a.bytes += static_cast<unsigned long>(daten.len - 4);
    }
    mg_ws_printf(c, WEBSOCKET_OP_TEXT, "{%m:%lu,%m:%lu}", MG_ESC("seq"), a.letzteNr, MG_ESC("total"), a.bytes);
}
