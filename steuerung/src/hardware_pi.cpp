#include "hardware.hpp"
#include "konfiguration.hpp"

namespace {

// Echte Hardware am Raspberry Pi 4: TMC2209 (STEP/DIR/EN), Endschalter, HX711.
class PiHardware : public Hardware {
public:
    explicit PiHardware(const Konfiguration& konfig) {
        (void)konfig;
        // TODO: GPIO-Pins aus der Konfiguration anfordern, Motor stromlos (EN = HIGH), HX711-SCK auf LOW
    }

    void motorFreigeben(bool an) override {
        (void)an;
        // TODO: EN ist aktiv LOW
    }

    void richtung(bool vomEndschalterWeg) override {
        (void)vomEndschalterWeg;
        // TODO: DIR setzen, richtung_umkehren beachten
    }

    void schritt() override {
        // TODO: kurzer Impuls auf STEP (mind. 100 ns HIGH)
    }

    bool endschalter() override {
        // TODO: Schalter nach GND, also betaetigt = LOW
        return false;
    }

    std::optional<int32_t> waegezelleLesen() override {
        // TODO: wenn DOUT LOW ist: 24 Bit einlesen, 25. Takt (Kanal A, Verstaerkung 128), Vorzeichen beachten.
        //       SCK darf nie laenger als 60 us HIGH sein, sonst Wert verwerfen.
        return std::nullopt;
    }
};

}  // namespace

std::unique_ptr<Hardware> erstellePiHardware(const Konfiguration& konfig) {
    return std::make_unique<PiHardware>(konfig);
}
