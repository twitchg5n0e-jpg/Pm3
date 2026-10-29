#include "gpio.hpp"

GpioChip::GpioChip(const std::string& pfad) : fd_(-1) {
    (void)pfad;
    // TODO: /dev/gpiochipN oeffnen (open mit O_RDWR), bei Fehler Ausnahme werfen
}

GpioChip::~GpioChip() {
    // TODO: Datei schliessen
}

GpioPin::GpioPin(const GpioChip& chip, unsigned nummer, Modus modus, const char* name) : fd_(-1) {
    (void)chip;
    (void)nummer;
    (void)modus;
    (void)name;
    // TODO: Leitung mit ioctl(GPIO_V2_GET_LINE_IOCTL) anfordern (Ausgang, Eingang oder Eingang mit Pull-up)
}

GpioPin::~GpioPin() {
    // TODO: Leitung freigeben (Datei schliessen)
}

void GpioPin::setzen(bool an) {
    (void)an;
    // TODO: ioctl(GPIO_V2_LINE_SET_VALUES_IOCTL)
}

bool GpioPin::lesen() const {
    // TODO: ioctl(GPIO_V2_LINE_GET_VALUES_IOCTL)
    return false;
}
