#pragma once

#include <string>

// GPIO-Zugriff ueber die Linux-Schnittstelle /dev/gpiochipN (uAPI v2). Braucht keine zusaetzliche
// Bibliothek und funktioniert mit jeder Raspberry-Pi-OS-Version ab Kernel 5.10.

class GpioChip {
public:
    explicit GpioChip(const std::string& pfad);
    ~GpioChip();
    GpioChip(const GpioChip&) = delete;
    GpioChip& operator=(const GpioChip&) = delete;

    int fd() const { return fd_; }

private:
    int fd_;
};

class GpioPin {
public:
    enum class Modus { Ausgang, Eingang, EingangPullUp };

    GpioPin(const GpioChip& chip, unsigned nummer, Modus modus, const char* name);
    ~GpioPin();
    GpioPin(const GpioPin&) = delete;
    GpioPin& operator=(const GpioPin&) = delete;

    void setzen(bool an);
    bool lesen() const;

private:
    int fd_;
};
