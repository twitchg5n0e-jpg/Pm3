#include "motor.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>

#include "hardware.hpp"

namespace {

// Bis zu dieser Geschwindigkeit startet und stoppt ein Schrittmotor ohne Rampe.
constexpr double kStartSchritteS = 200.0;

}  // namespace

Motor::Motor(Hardware& hardware, double beschleunigungSchritteS2)
    : hardware_(hardware), beschleunigung_(beschleunigungSchritteS2), thread_(&Motor::lauf, this) {}

Motor::~Motor() {
    laeuft_ = false;
    thread_.join();
    hardware_.motorFreigeben(false);
}

void Motor::geschwindigkeit(double schritteProS) { ziel_ = schritteProS; }

void Motor::sofortHalt() {
    ziel_ = 0.0;
    halt_ = true;
}

void Motor::freigeben(bool an) { hardware_.motorFreigeben(an); }

void Motor::lauf() {
    using Uhr = std::chrono::steady_clock;
    auto naechster = Uhr::now();
    bool vorwaerts = true;
    hardware_.richtung(true);

    while (laeuft_) {
        if (halt_.exchange(false)) ist_ = 0.0;
        double v = ist_;
        const double z = ziel_;

        if (v == 0.0) {
            if (z == 0.0) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
                naechster = Uhr::now();
                continue;
            }
            v = std::copysign(std::min(std::abs(z), kStartSchritteS), z);
        } else {
            // Rampe: pro Schritt (Dauer 1/|v|) aendert sich die Geschwindigkeit um a/|v|.
            const double dv = beschleunigung_ / std::abs(v);
            v = z > v ? std::min(z, v + dv) : std::max(z, v - dv);
            const bool richtungswechsel = std::signbit(z) != std::signbit(v);
            if (std::abs(v) < kStartSchritteS && (z == 0.0 || richtungswechsel)) {
                ist_ = 0.0;
                continue;
            }
        }
        ist_ = v;

        const bool vw = v > 0;
        if (vw != vorwaerts) {
            hardware_.richtung(vw);
            vorwaerts = vw;
            std::this_thread::sleep_for(std::chrono::microseconds(5));
        }
        hardware_.schritt();
        position_ += vw ? 1 : -1;

        naechster += std::chrono::nanoseconds(static_cast<long>(1e9 / std::abs(v)));
        const auto jetzt = Uhr::now();
        if (naechster < jetzt - std::chrono::milliseconds(5)) naechster = jetzt;  // nicht endlos aufholen
        std::this_thread::sleep_until(naechster);
    }
}
