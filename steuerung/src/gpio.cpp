#include "gpio.hpp"

#include <fcntl.h>
#include <linux/gpio.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <system_error>

GpioChip::GpioChip(const std::string& pfad) : fd_(::open(pfad.c_str(), O_RDWR | O_CLOEXEC)) {
    if (fd_ < 0) throw std::system_error(errno, std::generic_category(), "GPIO-Chip " + pfad);
}

GpioChip::~GpioChip() { ::close(fd_); }

GpioPin::GpioPin(const GpioChip& chip, unsigned nummer, Modus modus, const char* name) {
    gpio_v2_line_request anfrage{};
    anfrage.offsets[0] = nummer;
    anfrage.num_lines = 1;
    std::strncpy(anfrage.consumer, name, sizeof(anfrage.consumer) - 1);
    switch (modus) {
        case Modus::Ausgang:
            anfrage.config.flags = GPIO_V2_LINE_FLAG_OUTPUT;
            break;
        case Modus::Eingang:
            anfrage.config.flags = GPIO_V2_LINE_FLAG_INPUT;
            break;
        case Modus::EingangPullUp:
            anfrage.config.flags = GPIO_V2_LINE_FLAG_INPUT | GPIO_V2_LINE_FLAG_BIAS_PULL_UP;
            break;
    }
    if (::ioctl(chip.fd(), GPIO_V2_GET_LINE_IOCTL, &anfrage) < 0)
        throw std::system_error(errno, std::generic_category(), "GPIO " + std::to_string(nummer));
    fd_ = anfrage.fd;
}

GpioPin::~GpioPin() { ::close(fd_); }

void GpioPin::setzen(bool an) {
    gpio_v2_line_values werte{};
    werte.mask = 1;
    werte.bits = an ? 1 : 0;
    ::ioctl(fd_, GPIO_V2_LINE_SET_VALUES_IOCTL, &werte);
}

bool GpioPin::lesen() const {
    gpio_v2_line_values werte{};
    werte.mask = 1;
    ::ioctl(fd_, GPIO_V2_LINE_GET_VALUES_IOCTL, &werte);
    return werte.bits & 1;
}
