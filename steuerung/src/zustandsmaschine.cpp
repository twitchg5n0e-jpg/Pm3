#include "zustandsmaschine.hpp"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <sstream>

#include "konfiguration.hpp"
#include "messprotokoll.hpp"
#include "motor.hpp"

namespace {

std::string zahlText(double wert, int nachkomma = 1) {
    char puffer[32];
    std::snprintf(puffer, sizeof(puffer), "%.*f", nachkomma, wert);
    return puffer;
}

}  // namespace

const char* zustandName(Zustand zustand) {
    switch (zustand) {
        case Zustand::Unreferenziert: return "UNREFERENZIERT";
        case Zustand::Referenzfahrt: return "REFERENZFAHRT";
        case Zustand::Bereit: return "BEREIT";
        case Zustand::Positionieren: return "POSITIONIEREN";
        case Zustand::Pruefung: return "PRUEFUNG";
        case Zustand::Ende: return "ENDE";
        case Zustand::Fehler: return "FEHLER";
    }
    return "?";
}

Zustandsmaschine::Zustandsmaschine(Motor& motor, Messprotokoll& protokoll, const Konfiguration& k, Melden melden)
    : motor_(motor),
      protokoll_(protokoll),
      melden_(std::move(melden)),
      schritteProMm_(k.schritteProMm()),
      verfahrwegMm_(k.zahl("verfahrweg_mm", 100)),
      vMaxMmS_(k.zahl("max_geschwindigkeit_mm_s", 2)),
      vReferenzMmS_(k.zahl("referenz_geschwindigkeit_mm_s", 1)),
      beschleunigungMmS2_(k.zahl("beschleunigung_mm_s2", 5)),
      freifahrenMm_(k.zahl("freifahren_mm", 1)),
      kraftGrenzeN_(k.zahl("kraft_grenze_n", 550)),
      bruchMindestkraftN_(k.zahl("bruch_mindestkraft_n", 5)),
      zugVomEndschalterWeg_(k.ganzzahl("zug_vom_endschalter_weg", 1) != 0) {}

double Zustandsmaschine::positionMm() const { return motor_.position() / schritteProMm_; }

double Zustandsmaschine::wegMm() const {
    return pruefrichtung() * (motor_.position() - startSchritte_) / schritteProMm_;
}

int Zustandsmaschine::pruefrichtung() const {
    const int zug = zugVomEndschalterWeg_ ? 1 : -1;
    return parameter_.zug ? zug : -zug;
}

std::string Zustandsmaschine::befehl(const std::string& name, const std::string& argument) {
    const bool bereit = zustand_ == Zustand::Bereit || zustand_ == Zustand::Ende;

    if (name == "nothalt") {
        fehler("Not-Halt");
        return "";
    }
    if (name == "stopp") {
        switch (zustand_) {
            case Zustand::Referenzfahrt:
                motor_.geschwindigkeit(0);
                wechseln(Zustand::Unreferenziert);
                break;
            case Zustand::Positionieren:
                motor_.geschwindigkeit(0);
                wechseln(referenziert_ ? Zustand::Bereit : Zustand::Unreferenziert);
                break;
            case Zustand::Pruefung:
                beenden("Abgebrochen");
                break;
            default:
                break;
        }
        return "";
    }
    if (name == "referenz") {
        if (!bereit && zustand_ != Zustand::Unreferenziert) return "nur im Stillstand moeglich";
        wechseln(Zustand::Referenzfahrt);
        return "";
    }
    if (name == "start") {
        if (!referenziert_) return "zuerst Referenzfahrt";
        if (!bereit) return std::string("nicht im Zustand ") + zustandName(zustand_);
        wechseln(Zustand::Pruefung);
        return "";
    }
    if (name == "fahren") {
        if (!referenziert_) return "zuerst Referenzfahrt";
        if (!bereit) return std::string("nicht im Zustand ") + zustandName(zustand_);
        try {
            return positionieren(positionMm() + std::stod(argument));
        } catch (const std::exception&) {
            return "fahren braucht einen Weg in mm, z.B. fahren 5";
        }
    }
    if (name == "quittieren") {
        if (zustand_ == Zustand::Fehler) wechseln(Zustand::Unreferenziert);
        else if (zustand_ == Zustand::Ende) wechseln(Zustand::Bereit);
        return "";
    }
    if (name == "set") {
        if (zustand_ == Zustand::Pruefung) return "nicht waehrend einer Pruefung";
        return setzen(argument);
    }
    return "unbekannter Befehl";
}

std::string Zustandsmaschine::setzen(const std::string& argument) {
    std::istringstream ein(argument);
    std::string name, wert;
    ein >> name >> wert;
    if (name == "modus") {
        if (wert != "zug" && wert != "druck") return "modus ist zug oder druck";
        parameter_.zug = wert == "zug";
        return "";
    }
    double zahl;
    try {
        zahl = std::stod(wert);
    } catch (const std::exception&) {
        return "Wert fehlt";
    }
    if (zahl <= 0) return "Wert muss groesser als 0 sein";
    if (name == "geschwindigkeit") {
        if (zahl / 60.0 > vMaxMmS_) return "hoechstens " + zahlText(vMaxMmS_ * 60, 0) + " mm/min";
        parameter_.geschwindigkeitMmMin = zahl;
    } else if (name == "maxkraft") {
        if (zahl > kraftGrenzeN_) return "hoechstens " + zahlText(kraftGrenzeN_, 0) + " N";
        parameter_.maxKraftN = zahl;
    } else if (name == "maxweg") {
        parameter_.maxWegMm = zahl;
    } else if (name == "bruch") {
        if (zahl >= 100) return "bruch in Prozent, unter 100";
        parameter_.bruchProzent = zahl;
    } else {
        return "unbekannter Parameter " + name;
    }
    return "";
}

std::string Zustandsmaschine::positionieren(double zielMm) {
    if (zielMm < 0 || zielMm > verfahrwegMm_)
        return "Ziel ausserhalb 0 bis " + zahlText(verfahrwegMm_, 0) + " mm";
    zielSchritte_ = std::lround(zielMm * schritteProMm_);
    wechseln(Zustand::Positionieren);
    return "";
}

void Zustandsmaschine::wechseln(Zustand neu) {
    zustand_ = neu;
    switch (neu) {
        case Zustand::Unreferenziert:
            break;
        case Zustand::Referenzfahrt:
            referenziert_ = false;
            startSchritte_ = motor_.position();
            motor_.freigeben(true);
            motor_.geschwindigkeit(-vReferenzMmS_ * schritteProMm_);
            break;
        case Zustand::Bereit:
            motor_.geschwindigkeit(0);
            break;
        case Zustand::Positionieren:
            motor_.freigeben(true);
            break;
        case Zustand::Pruefung: {
            startSchritte_ = motor_.position();
            startZeit_ = std::chrono::steady_clock::now();
            spitzenkraft_ = 0.0;
            ergebnis_.clear();
            std::ostringstream kopf;
            kopf << "Modus: " << (parameter_.zug ? "Zug" : "Druck") << '\n'
                 << "Geschwindigkeit: " << parameter_.geschwindigkeitMmMin << " mm/min\n"
                 << "Maximalkraft: " << parameter_.maxKraftN << " N\n"
                 << "Maximalweg: " << parameter_.maxWegMm << " mm\n"
                 << "Bruch bei Abfall um: " << parameter_.bruchProzent << " %\n"
                 << "Startposition: " << zahlText(positionMm(), 3) << " mm";
            datei_ = protokoll_.starten(kopf.str());
            motor_.geschwindigkeit(pruefrichtung() * parameter_.geschwindigkeitMmMin / 60.0 * schritteProMm_);
            break;
        }
        case Zustand::Ende:
            motor_.geschwindigkeit(0);
            break;
        case Zustand::Fehler:
            motor_.sofortHalt();
            motor_.freigeben(false);
            referenziert_ = false;
            if (protokoll_.offen()) protokoll_.beenden(ergebnis_);
            break;
    }
    melden_(std::string("Zustand: ") + zustandName(neu));
}

void Zustandsmaschine::fehler(const std::string& grund) {
    ergebnis_ = "Fehler: " + grund;
    melden_(ergebnis_);
    wechseln(Zustand::Fehler);
}

void Zustandsmaschine::beenden(const std::string& grund) {
    ergebnis_ = grund + ", Spitzenkraft " + zahlText(spitzenkraft_) + " N bei Weg " + zahlText(wegMm(), 3) + " mm";
    protokoll_.beenden(ergebnis_);
    melden_("Pruefung beendet: " + ergebnis_);
    wechseln(Zustand::Ende);
}

void Zustandsmaschine::schritt(const Messwerte& m) {
    if (zustand_ != Zustand::Fehler && std::abs(m.kraftN) > kraftGrenzeN_) {
        fehler("Kraftgrenze " + zahlText(kraftGrenzeN_, 0) + " N ueberschritten (" + zahlText(m.kraftN) + " N)");
        return;
    }
    const long position = motor_.position();

    switch (zustand_) {
        case Zustand::Referenzfahrt:
            if (m.endschalter) {
                motor_.sofortHalt();
                motor_.positionSetzen(0);
                referenziert_ = true;
                melden_("Endschalter erreicht, Nullpunkt gesetzt");
                positionieren(freifahrenMm_);
            } else if (startSchritte_ - position > (verfahrwegMm_ + 10) * schritteProMm_) {
                fehler("Endschalter nicht gefunden");
            }
            break;

        case Zustand::Positionieren: {
            const long rest = zielSchritte_ - position;
            if (m.endschalter && rest < 0) {
                fehler("Endschalter beim Positionieren");
                break;
            }
            // Bremskurve: v = sqrt(2 a s), damit der Motor genau am Ziel zum Stehen kommt.
            const double a = beschleunigungMmS2_ * schritteProMm_;
            const double v = std::min(vMaxMmS_ * schritteProMm_, std::sqrt(2.0 * a * std::abs(rest)));
            motor_.geschwindigkeit(std::abs(rest) <= 1 ? 0.0 : std::copysign(v, rest));
            if (std::abs(rest) <= 2 && motor_.steht()) wechseln(referenziert_ ? Zustand::Bereit : Zustand::Unreferenziert);
            break;
        }

        case Zustand::Pruefung: {
            if (m.endschalter) {
                fehler("Endschalter waehrend der Pruefung");
                break;
            }
            if (position < 0 || position > verfahrwegMm_ * schritteProMm_) {
                beenden("Ende des Verfahrwegs");
                break;
            }
            const double kraft = pruefkraft(m.kraftN);
            if (!m.kraftNeu) break;
            spitzenkraft_ = std::max(spitzenkraft_, kraft);
            const double zeit = std::chrono::duration<double>(std::chrono::steady_clock::now() - startZeit_).count();
            protokoll_.zeile(zeit, wegMm(), kraft, optik_);

            if (kraft >= parameter_.maxKraftN) {
                beenden("Maximalkraft erreicht");
            } else if (wegMm() >= parameter_.maxWegMm) {
                beenden("Maximalweg erreicht");
            } else if (spitzenkraft_ >= bruchMindestkraftN_ &&
                       kraft < spitzenkraft_ * (1.0 - parameter_.bruchProzent / 100.0)) {
                beenden("Bruch erkannt");
            }
            break;
        }

        case Zustand::Unreferenziert:
        case Zustand::Bereit:
        case Zustand::Ende:
        case Zustand::Fehler:
            break;
    }
}
