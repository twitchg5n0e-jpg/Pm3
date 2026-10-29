#include <chrono>

#include "gpio.hpp"
#include "hardware.hpp"
#include "konfiguration.hpp"

namespace {

using Uhr = std::chrono::steady_clock;

void warte(std::chrono::nanoseconds dauer) {
    const auto ende = Uhr::now() + dauer;
    while (Uhr::now() < ende) {
    }
}

class PiHardware : public Hardware {
public:
    explicit PiHardware(const Konfiguration& k)
        : chip_(k.text("gpio_chip", "/dev/gpiochip0")),
          step_(chip_, k.ganzzahl("pin_step", 20), GpioPin::Modus::Ausgang, "pruefstand-step"),
          dir_(chip_, k.ganzzahl("pin_dir", 21), GpioPin::Modus::Ausgang, "pruefstand-dir"),
          enable_(chip_, k.ganzzahl("pin_enable", 16), GpioPin::Modus::Ausgang, "pruefstand-enable"),
          endschalter_(chip_, k.ganzzahl("pin_endschalter", 26), GpioPin::Modus::EingangPullUp,
                       "pruefstand-endschalter"),
          hxDout_(chip_, k.ganzzahl("pin_hx711_dout", 5), GpioPin::Modus::Eingang, "pruefstand-hx711-dout"),
          hxSck_(chip_, k.ganzzahl("pin_hx711_sck", 6), GpioPin::Modus::Ausgang, "pruefstand-hx711-sck"),
          umkehren_(k.ganzzahl("richtung_umkehren", 0) != 0) {
        enable_.setzen(true);  // EN aktiv LOW: Motor erst einmal stromlos
        step_.setzen(false);
        hxSck_.setzen(false);  // SCK laenger als 60 us HIGH schaltet den HX711 ab
    }

    ~PiHardware() override { enable_.setzen(true); }

    void motorFreigeben(bool an) override { enable_.setzen(!an); }

    void richtung(bool vomEndschalterWeg) override { dir_.setzen(vomEndschalterWeg != umkehren_); }

    void schritt() override {
        step_.setzen(true);
        warte(std::chrono::microseconds(2));  // TMC2209 braucht mindestens 100 ns
        step_.setzen(false);
    }

    // Der Endschalter schliesst nach GND, betaetigt heisst also LOW.
    bool endschalter() override { return !endschalter_.lesen(); }

    std::optional<int32_t> waegezelleLesen() override {
        if (hxDout_.lesen()) return std::nullopt;  // DOUT LOW = neuer Wert bereit

        // 24 Datenbits, dann ein 25. Takt fuer Kanal A mit Verstaerkung 128. Bleibt SCK durch eine
        // Unterbrechung des Programms zu lange HIGH, ist der Wert unbrauchbar und wird verworfen.
        uint32_t wert = 0;
        bool gestoert = false;
        for (int bit = 0; bit < 25; ++bit) {
            const auto start = Uhr::now();
            hxSck_.setzen(true);
            warte(std::chrono::microseconds(1));
            if (bit < 24) wert = (wert << 1) | (hxDout_.lesen() ? 1u : 0u);
            hxSck_.setzen(false);
            if (Uhr::now() - start > std::chrono::microseconds(50)) gestoert = true;
            warte(std::chrono::microseconds(1));
        }
        if (gestoert) return std::nullopt;
        if (wert & 0x800000) wert |= 0xFF000000;  // Vorzeichen des 24-Bit-Werts
        return static_cast<int32_t>(wert);
    }

private:
    GpioChip chip_;
    GpioPin step_, dir_, enable_, endschalter_, hxDout_, hxSck_;
    bool umkehren_;
};

}  // namespace

std::unique_ptr<Hardware> erstellePiHardware(const Konfiguration& konfig) {
    return std::make_unique<PiHardware>(konfig);
}
