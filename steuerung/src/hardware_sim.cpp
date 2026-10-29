#include <atomic>
#include <chrono>
#include <cmath>
#include <random>

#include "hardware.hpp"
#include "konfiguration.hpp"

namespace {

// Simulierter Pruefstand: Der Schlitten startet etwas vom Endschalter entfernt. Nach der Referenzfahrt
// gilt die Probe als eingespannt; sie verhaelt sich wie eine Feder und reisst beim Zug bei einer
// einstellbaren Kraft. So laesst sich der ganze Ablauf samt Bedienoberflaeche ohne Hardware ausprobieren.
class Simulation : public Hardware {
public:
    explicit Simulation(const Konfiguration& k)
        : schritteProMm_(k.schritteProMm()),
          faktor_(k.zahl("waegezelle_faktor", 0.0001)),
          steifigkeit_(k.zahl("sim_steifigkeit_n_mm", 50)),
          bruchBei_(k.zahl("sim_bruch_bei_n", 400)),
          position_(std::lround(k.zahl("sim_startposition_mm", 10) * schritteProMm_)),
          probeNull_(std::lround(k.zahl("sim_probe_mm", 1) * schritteProMm_)) {}

    void motorFreigeben(bool) override {}
    void richtung(bool vomEndschalterWeg) override { vorwaerts_ = vomEndschalterWeg; }
    void schritt() override { position_ += vorwaerts_ ? 1 : -1; }
    bool endschalter() override {
        if (position_ <= 0) eingespannt_ = true;
        return position_ <= 0;
    }

    std::optional<int32_t> waegezelleLesen() override {
        const auto jetzt = std::chrono::steady_clock::now();
        if (jetzt < naechsterWert_) return std::nullopt;
        naechsterWert_ = jetzt + std::chrono::microseconds(12500);  // HX711 mit 80 Messungen/s

        const double dehnung = (position_ - probeNull_) / schritteProMm_;
        double kraft = eingespannt_ ? steifigkeit_ * dehnung : 0.0;
        if (kraft >= bruchBei_) gerissen_ = true;
        if (gerissen_ && kraft > 0) kraft = 0;
        kraft += rauschen_(zufall_);
        return static_cast<int32_t>(std::lround(kraft / faktor_));
    }

private:
    double schritteProMm_, faktor_, steifigkeit_, bruchBei_;
    std::atomic<long> position_;
    std::atomic<bool> vorwaerts_{true};
    long probeNull_;
    bool eingespannt_ = false, gerissen_ = false;
    std::chrono::steady_clock::time_point naechsterWert_{};
    std::mt19937 zufall_{42};
    std::normal_distribution<double> rauschen_{0.0, 0.2};
};

}  // namespace

std::unique_ptr<Hardware> erstelleSimulation(const Konfiguration& konfig) {
    return std::make_unique<Simulation>(konfig);
}
