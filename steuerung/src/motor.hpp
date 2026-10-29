#pragma once

#include <atomic>
#include <thread>

class Hardware;

// Erzeugt die Schrittimpulse in einem eigenen Thread und faehrt die Geschwindigkeit mit einer Rampe an.
// Geschwindigkeiten in Schritten pro Sekunde, positiv = vom Endschalter weg.
class Motor {
public:
    Motor(Hardware& hardware, double beschleunigungSchritteS2);
    ~Motor();

    void geschwindigkeit(double schritteProS);  // Ziel, 0 = mit Rampe anhalten
    void sofortHalt();                          // ohne Rampe, z.B. bei einem Fehler
    void freigeben(bool an);

    long position() const { return position_; }
    void positionSetzen(long schritte) { position_ = schritte; }
    bool steht() const { return ist_ == 0.0; }

private:
    void lauf();

    Hardware& hardware_;
    const double beschleunigung_;
    std::atomic<double> ziel_{0.0}, ist_{0.0};
    std::atomic<long> position_{0};
    std::atomic<bool> halt_{false}, laeuft_{true};
    std::thread thread_;
};
