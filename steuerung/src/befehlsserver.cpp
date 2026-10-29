#include "befehlsserver.hpp"

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <system_error>

Befehlsserver::Befehlsserver(int port, Empfang empfang)
    : lauscher_(::socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0)), empfang_(std::move(empfang)) {
    if (lauscher_ < 0) throw std::system_error(errno, std::generic_category(), "socket");
    const int ja = 1;
    ::setsockopt(lauscher_, SOL_SOCKET, SO_REUSEADDR, &ja, sizeof(ja));

    sockaddr_in adresse{};
    adresse.sin_family = AF_INET;
    adresse.sin_port = htons(static_cast<uint16_t>(port));
    adresse.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (::bind(lauscher_, reinterpret_cast<sockaddr*>(&adresse), sizeof(adresse)) < 0 || ::listen(lauscher_, 4) < 0)
        throw std::system_error(errno, std::generic_category(), "Port " + std::to_string(port));
}

Befehlsserver::~Befehlsserver() {
    for (auto& c : clients_) ::close(c.fd);
    ::close(lauscher_);
}

void Befehlsserver::abarbeiten(int wartezeitMs) {
    std::vector<pollfd> fds{{lauscher_, POLLIN, 0}};
    for (const auto& c : clients_) fds.push_back({c.fd, POLLIN, 0});
    if (::poll(fds.data(), fds.size(), wartezeitMs) <= 0) return;

    if (fds[0].revents & POLLIN) {
        const int fd = ::accept4(lauscher_, nullptr, nullptr, SOCK_NONBLOCK | SOCK_CLOEXEC);
        if (fd >= 0) clients_.push_back({fd, {}});
    }

    // Rueckwaerts, damit geschlossene Clients die Indizes der uebrigen nicht verschieben.
    for (std::size_t i = fds.size() - 1; i >= 1; --i) {
        if (!(fds[i].revents & (POLLIN | POLLHUP | POLLERR))) continue;
        const std::size_t index = i - 1;
        char daten[1024];
        const ssize_t n = ::recv(clients_[index].fd, daten, sizeof(daten), 0);
        if (n <= 0) {
            schliessen(index);
            continue;
        }
        auto& puffer = clients_[index].puffer;
        puffer.append(daten, static_cast<std::size_t>(n));
        for (auto ende = puffer.find('\n'); ende != std::string::npos; ende = puffer.find('\n')) {
            std::string zeile = puffer.substr(0, ende);
            puffer.erase(0, ende + 1);
            if (!zeile.empty() && zeile.back() == '\r') zeile.pop_back();
            if (!zeile.empty()) empfang_(zeile);
        }
        if (puffer.size() > 4096) schliessen(index);  // keine Zeile, nur Muell
    }
}

void Befehlsserver::senden(const std::string& zeile) {
    const std::string daten = zeile + '\n';
    for (std::size_t i = clients_.size(); i-- > 0;) {
        // Ein langsamer Client verpasst lieber eine Statuszeile, als die Steuerung aufzuhalten.
        if (::send(clients_[i].fd, daten.data(), daten.size(), MSG_NOSIGNAL) < 0 && errno != EAGAIN)
            schliessen(i);
    }
}

void Befehlsserver::schliessen(std::size_t index) {
    ::close(clients_[index].fd);
    clients_.erase(clients_.begin() + static_cast<long>(index));
}
