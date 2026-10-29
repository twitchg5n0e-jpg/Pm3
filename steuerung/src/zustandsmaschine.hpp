#pragma once

#include <chrono>
#include <functional>
#include <string>

class Konfiguration;
class Messprotokoll;
class Motor;

// Ablauf des Pruefstands:
//
//   UNREFERENZIERT --referenz--> REFERENZFAHRT --Endschalter--> POSITIONIEREN (freifahren) --> BEREIT
//   BEREIT --start--> PRUEFUNG --Maximalkraft / Maximalweg / Bruch / stopp--> ENDE --quittieren--> BEREIT
//   BEREIT --fahren <mm>--> POSITIONIEREN --> BEREIT
//   jeder Zustand --Kraftgrenze / Endschalter / nothalt--> FEHLER --quittieren--> UNREFERENZIERT
enum class Zustand { Unreferenziert, Referenzfahrt, Bereit, Positionieren, Pruefung, Ende, Fehler };

const char* zustandName(Zustand zustand);

struct Pruefparameter {
    bool zug = true;
    double geschwindigkeitMmMin = 5.0;
    double maxKraftN = 500.0;
    double maxWegMm = 20.0;
    double bruchProzent = 50.0;  // Bruch, wenn die Kraft um so viel unter die Spitzenkraft faellt
};

struct Messwerte {
    double kraftN;
    bool kraftNeu;  // seit dem letzten Aufruf kam ein neuer Wert der Waegezelle
    bool endschalter;
};

class Zustandsmaschine {
public:
    using Melden = std::function<void(const std::string& text)>;

    Zustandsmaschine(Motor& motor, Messprotokoll& protokoll, const Konfiguration& konfig, Melden melden);

    // Bedienbefehl. Gibt bei Erfolg einen leeren Text zurueck, sonst den Grund der Ablehnung.
    std::string befehl(const std::string& name, const std::string& argument);

    // Wird zyklisch aus der Hauptschleife aufgerufen.
    void schritt(const Messwerte& m);

    void optikSetzen(std::string text) { optik_ = std::move(text); }

    Zustand zustand() const { return zustand_; }
    bool referenziert() const { return referenziert_; }
    double positionMm() const;
    double wegMm() const;  // seit Pruefungsbeginn, in Pruefrichtung positiv
    double spitzenkraftN() const { return spitzenkraft_; }
    const Pruefparameter& parameter() const { return parameter_; }
    const std::string& ergebnis() const { return ergebnis_; }
    const std::string& datei() const { return datei_; }

private:
    void wechseln(Zustand neu);
    void fehler(const std::string& grund);
    void beenden(const std::string& grund);
    std::string positionieren(double zielMm);
    std::string setzen(const std::string& argument);
    double pruefkraft(double kraftN) const { return parameter_.zug ? kraftN : -kraftN; }
    int pruefrichtung() const;

    Motor& motor_;
    Messprotokoll& protokoll_;
    Melden melden_;

    // aus der Konfiguration
    double schritteProMm_, verfahrwegMm_, vMaxMmS_, vReferenzMmS_, beschleunigungMmS2_, freifahrenMm_;
    double kraftGrenzeN_, bruchMindestkraftN_;
    bool zugVomEndschalterWeg_;

    Zustand zustand_ = Zustand::Unreferenziert;
    bool referenziert_ = false;
    Pruefparameter parameter_;
    long zielSchritte_ = 0, startSchritte_ = 0;
    double spitzenkraft_ = 0.0;
    std::chrono::steady_clock::time_point startZeit_;
    std::string optik_, ergebnis_, datei_;
};
