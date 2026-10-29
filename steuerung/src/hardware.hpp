#pragma once

#include <cstdint>
#include <memory>
#include <optional>

class Konfiguration;

// Alles, was die Steuerung von der Hardware braucht. Es gibt eine Umsetzung fuer den Raspberry Pi
// (TMC2209, Endschalter, HX711) und eine Simulation zum Testen ohne Pruefstand.
// schritt() und richtung() ruft der Motor-Thread auf, alles andere der Haupt-Thread.
class Hardware {
public:
    virtual ~Hardware() = default;

    virtual void motorFreigeben(bool an) = 0;
    virtual void richtung(bool vomEndschalterWeg) = 0;
    virtual void schritt() = 0;
    virtual bool endschalter() = 0;  // true = betaetigt

    // Rohwert der Waegezelle, wenn seit dem letzten Aufruf ein neuer bereitsteht.
    virtual std::optional<int32_t> waegezelleLesen() = 0;
};

std::unique_ptr<Hardware> erstellePiHardware(const Konfiguration& konfig);
std::unique_ptr<Hardware> erstelleSimulation(const Konfiguration& konfig);
