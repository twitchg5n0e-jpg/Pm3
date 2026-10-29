#pragma once

#include <atomic>

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

    long position() const;
    void positionSetzen(long schritte);
    bool steht() const;

private:
    void lauf();  // Thread: Rampe rechnen, Schritte ausgeben, Position zaehlen

    Hardware& hardware_;
    double beschleunigung_;
    std::atomic<long> position_{0};
    // TODO: Ziel- und Ist-Geschwindigkeit, Halt-Flag, Thread
};
