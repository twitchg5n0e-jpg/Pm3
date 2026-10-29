#pragma once

#include <functional>
#include <string>

class Konfiguration;
class Messprotokoll;
class Motor;
class UsbExport;

// Ablauf des Pruefstands:
//
//   UNREFERENZIERT --referenz--> REFERENZFAHRT --Endschalter--> POSITIONIEREN (freifahren) --> BEREIT
//   BEREIT --start--> PRUEFUNG --Maximalkraft / Maximalweg / Bruch / stopp--> ENDE --quittieren--> BEREIT
//   BEREIT --fahren <mm>--> POSITIONIEREN --> BEREIT
//   jeder Zustand --Kraftgrenze / Endschalter / nothalt--> FEHLER --quittieren--> UNREFERENZIERT
//
// Bei ENDE wird die Messdatei automatisch auf einen eingesteckten USB-Stick kopiert.
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

    Zustandsmaschine(Motor& motor, Messprotokoll& protokoll, UsbExport& usb, const Konfiguration& konfig,
                     Melden melden);

    // Bedienbefehl. Gibt bei Erfolg einen leeren Text zurueck, sonst den Grund der Ablehnung.
    std::string befehl(const std::string& name, const std::string& argument);

    // Wird zyklisch aus der Hauptschleife aufgerufen.
    void schritt(const Messwerte& m);

    Zustand zustand() const { return zustand_; }
    const Pruefparameter& parameter() const { return parameter_; }
    const std::string& ergebnis() const { return ergebnis_; }

private:
    void wechseln(Zustand neu);
    void fehler(const std::string& grund);
    void beenden(const std::string& grund);

    Motor& motor_;
    Messprotokoll& protokoll_;
    UsbExport& usb_;
    Melden melden_;

    Zustand zustand_ = Zustand::Unreferenziert;
    Pruefparameter parameter_;
    std::string ergebnis_;
    // TODO: referenziert, Ziel- und Startposition, Spitzenkraft, Startzeit, Werte aus der Konfiguration
};
