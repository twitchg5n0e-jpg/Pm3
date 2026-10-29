#include "motor.hpp"

#include "hardware.hpp"

Motor::Motor(Hardware& hardware, double beschleunigungSchritteS2)
    : hardware_(hardware), beschleunigung_(beschleunigungSchritteS2) {
    // TODO: Thread mit lauf() starten
}

Motor::~Motor() {
    // TODO: Thread beenden, Motor stromlos schalten
}

void Motor::geschwindigkeit(double schritteProS) {
    (void)schritteProS;
    // TODO: Zielgeschwindigkeit setzen
}

void Motor::sofortHalt() {
    // TODO: Ziel und Ist sofort auf 0
}

void Motor::freigeben(bool an) { hardware_.motorFreigeben(an); }

long Motor::position() const { return position_; }

void Motor::positionSetzen(long schritte) { position_ = schritte; }

bool Motor::steht() const {
    // TODO: Ist-Geschwindigkeit == 0
    return true;
}

void Motor::lauf() {
    // TODO: Schleife:
    //       - Ist-Geschwindigkeit mit der Beschleunigung Richtung Ziel aendern (Rampe)
    //       - bei Richtungswechsel DIR umschalten
    //       - hardware_.schritt(), Position zaehlen
    //       - bis zum naechsten Schritt warten (1 / Geschwindigkeit)
}
