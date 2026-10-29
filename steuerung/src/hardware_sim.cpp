#include "hardware.hpp"
#include "konfiguration.hpp"

namespace {

// Simulierter Pruefstand zum Testen ohne Hardware: Schlitten, Endschalter bei Position 0,
// Probe als Feder, die beim Zug ab einer bestimmten Kraft reisst.
class Simulation : public Hardware {
public:
    explicit Simulation(const Konfiguration& konfig) {
        (void)konfig;
        // TODO: sim_startposition_mm, sim_probe_mm, sim_steifigkeit_n_mm, sim_bruch_bei_n lesen
    }

    void motorFreigeben(bool an) override { (void)an; }

    void richtung(bool vomEndschalterWeg) override {
        (void)vomEndschalterWeg;
        // TODO: Richtung merken
    }

    void schritt() override {
        // TODO: simulierte Position um einen Schritt aendern
    }

    bool endschalter() override {
        // TODO: betaetigt bei Position <= 0
        return false;
    }

    std::optional<int32_t> waegezelleLesen() override {
        // TODO: alle 12,5 ms einen Rohwert aus der Dehnung der Probe berechnen (mit etwas Rauschen)
        return std::nullopt;
    }
};

}  // namespace

std::unique_ptr<Hardware> erstelleSimulation(const Konfiguration& konfig) {
    return std::make_unique<Simulation>(konfig);
}
