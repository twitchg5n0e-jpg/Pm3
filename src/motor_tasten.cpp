// =============================================================================
// Schrittmotor mit zwei Tastern steuern  –  Raspberry Pi 4 + DRV8434S
//
//   AKTUELL: Tastersteuerung auskommentiert. Der Motor dreht abwechselnd
//   TAKT_S Sekunden rechts, dann TAKT_S Sekunden links (bis Ctrl+C).
//
//   (Auskommentiert) Up-Taster   (GPIO9)  gedrückt halten -> Motor fährt hoch
//   (Auskommentiert) Down-Taster (GPIO11) gedrückt halten -> Motor fährt runter
//
//   Dehnmessstreifen über HX711 (DOUT=GPIO23, SCK=GPIO24) werden die ganze
//   Zeit gelesen – im Stillstand und während der Motor fährt.
//   Beim Start wird tariert (Nullwert), danach Ausgabe alle DMS_AUSGABE_MS.
//
// Kompilieren:  g++ -O2 -std=c++17 -o motor_tasten motor_tasten.cpp
// Starten:      ./motor_tasten          (Beenden mit Ctrl+C)
//
// Greift direkt über /dev/gpiomem auf die GPIO-Register des BCM2711 zu
// -> keine Zusatzbibliothek nötig. Nur für Raspberry Pi 4 (nicht Pi 5)!
// =============================================================================
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

// ---------------- Pins (BCM) ----------------
constexpr int STEP = 17, DIR = 27, FAULT = 22;
constexpr int SLP = 4;                        // DRV8434S SLP (Pi-Pin 7): HIGH = Treiber wach
constexpr int TASTER_UP = 9, TASTER_DOWN = 11;
constexpr int HX_DOUT = 23, HX_SCK = 24;      // HX711 (Dehnmessstreifen)

// ---------------- Einstellungen ----------------
constexpr int DIR_HOCH = 1;               // fährt der Motor falsch herum? -> 0
constexpr double TAKT_S   = 2.0;          // Sekunden pro Richtung (rechts / links)

constexpr double PERIODE_START_US = 2000; // µs pro Schritt beim Anfahren
constexpr double PERIODE_MIN_US   = 500;  // µs pro Schritt bei Endgeschwindigkeit
constexpr double RAMPE            = 0.97; // Beschleunigungsfaktor pro Schritt
constexpr double GESCHWINDIGKEIT  = 0.20; // Anteil der Endgeschwindigkeit (0.20 = 20 %)

// Software-SPI für den DRV8434S. Auf true setzen, sobald verdrahtet.
constexpr bool SPI_AKTIV = true;
// Motorstrom in Prozent des Maximalstroms des Treibers (6.25 % Schritte, 6.25 … 100).
// Wird der Motor oder der Treiber zu heiss -> kleiner; fehlt Kraft / verliert Schritte -> grösser.
constexpr double STROM_PROZENT = 50.0;
constexpr int SPI_SCLK = 5, SPI_SDI = 6, SPI_SDO = 13, SPI_SCS = 26;

// Dehnmessstreifen (HX711)
constexpr bool   DMS_AKTIV      = true;
constexpr double DMS_FAKTOR     = 1.0;   // Counts -> Einheit (z.B. N), nach Kalibrierung anpassen
constexpr int    DMS_AUSGABE_MS = 0;     // 0 = jeden Messwert ausgeben, sonst Mindestabstand in ms

// ============================================================================
// Minimaler GPIO-Treiber für BCM2711
// ============================================================================
class Gpio {
public:
    enum Pull { NONE = 0, UP = 1, DOWN = 2 };

    bool open() {
        int fd = ::open("/dev/gpiomem", O_RDWR | O_SYNC);
        if (fd < 0) { perror("/dev/gpiomem"); return false; }
        void* p = mmap(nullptr, 4096, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        ::close(fd);
        if (p == MAP_FAILED) { perror("mmap"); return false; }
        reg_ = static_cast<volatile uint32_t*>(p);
        return true;
    }

    void output(int pin, int initial = 0) {
        write(pin, initial);
        setFunction(pin, 1);
    }

    void input(int pin, Pull pull) {
        setFunction(pin, 0);
        // GPIO_PUP_PDN_CNTRL_REG0..3 ab Offset 0xE4, 2 Bit pro Pin
        volatile uint32_t* r = reg_ + (0xE4 / 4) + pin / 16;
        int shift = (pin % 16) * 2;
        *r = (*r & ~(3u << shift)) | (uint32_t(pull) << shift);
    }

    void write(int pin, int value) {
        reg_[(value ? 0x1C : 0x28) / 4 + pin / 32] = 1u << (pin % 32);  // GPSET0 / GPCLR0
    }

    int read(int pin) const {
        return (reg_[0x34 / 4 + pin / 32] >> (pin % 32)) & 1;            // GPLEV0
    }

private:
    void setFunction(int pin, uint32_t fn) {                              // GPFSEL0..5
        volatile uint32_t* r = reg_ + pin / 10;
        int shift = (pin % 10) * 3;
        *r = (*r & ~(7u << shift)) | (fn << shift);
    }
    volatile uint32_t* reg_ = nullptr;
};

static Gpio gpio;
static volatile std::sig_atomic_t laufen = 1;
static void onSignal(int) { laufen = 0; }

// Präzises Warten in Mikrosekunden (aktives Warten -> gleichmässige Schritte)
static void warteUs(double us) {
    auto ende = std::chrono::steady_clock::now() + std::chrono::duration<double, std::micro>(us);
    while (std::chrono::steady_clock::now() < ende) {}
}

// ============================================================================
// DRV8434S per Software-SPI einschalten (SPI-Mode 1, 16 Bit)
// ============================================================================
static uint16_t spiTransfer(uint16_t word) {
    gpio.write(SPI_SCS, 0);
    warteUs(1);                                   // SCS-Setup-Zeit
    uint16_t rx = 0;
    for (int i = 15; i >= 0; --i) {
        gpio.write(SPI_SCLK, 1);
        gpio.write(SPI_SDI, (word >> i) & 1);
        warteUs(1);
        rx = (rx << 1) | gpio.read(SPI_SDO);
        gpio.write(SPI_SCLK, 0);
        warteUs(1);
    }
    gpio.write(SPI_SCS, 1);
    warteUs(2);                                   // SCS-High-Zeit vor dem nächsten Wort
    return rx;
}
static uint8_t drvRead(uint8_t a)             { return spiTransfer((1u << 14) | ((a & 0x1F) << 9)) & 0xFF; }
static void    drvWrite(uint8_t a, uint8_t d) { spiTransfer(((a & 0x1F) << 9) | d); }

static void drvEnable() {
    drvWrite(0x06, drvRead(0x06) | 0x80);   // CTRL4: CLR_FLT (Fehler löschen)
    // CTRL1: TRQ_DAC (Bit 7..4), 0000 = 100 %, jede Stufe -6.25 %, 1111 = 6.25 %
    int stufe = static_cast<int>((100.0 - STROM_PROZENT) / 6.25 + 0.5);
    if (stufe < 0) stufe = 0;
    if (stufe > 15) stufe = 15;
    drvWrite(0x03, static_cast<uint8_t>((drvRead(0x03) & 0x0F) | (stufe << 4)));
    uint8_t ctrl1 = drvRead(0x03);
    std::printf("DRV8434S Strom = %.2f %% (CTRL1 = 0x%02X)\n", 100.0 - 6.25 * (ctrl1 >> 4), ctrl1);
    drvWrite(0x04, drvRead(0x04) | 0x80);   // CTRL2: EN_OUT  (Endstufe ein)
    std::printf("DRV8434S CTRL2 = 0x%02X (Bit 7 muss 1 sein)\n", drvRead(0x04));
}

// ============================================================================
// HX711 (Dehnmessstreifen) – Kanal A, Verstärkung 128
// ============================================================================
static long dmsNull = 0;
static std::chrono::steady_clock::time_point dmsNaechsteAusgabe;

static bool hxBereit() { return gpio.read(HX_DOUT) == 0; }   // DOUT low = Wert fertig

static long hxLesen() {
    long v = 0;
    for (int i = 0; i < 24; ++i) {                // SCK nie > 60 µs high lassen!
        gpio.write(HX_SCK, 1); warteUs(1);
        v = (v << 1) | gpio.read(HX_DOUT);
        gpio.write(HX_SCK, 0); warteUs(1);
    }
    gpio.write(HX_SCK, 1); warteUs(1);            // 25. Takt -> nächste Messung Kanal A, Gain 128
    gpio.write(HX_SCK, 0); warteUs(1);
    if (v & 0x800000) v -= 0x1000000;             // 24-Bit-Zweierkomplement
    return v;
}

static void dmsTarieren() {
    long summe = 0; int n = 0;
    auto ende = std::chrono::steady_clock::now() + std::chrono::seconds(3);
    while (laufen && n < 10 && std::chrono::steady_clock::now() < ende) {
        if (hxBereit()) { summe += hxLesen(); ++n; }
        else usleep(1000);
    }
    if (n == 0) { std::puts("WARNUNG: HX711 antwortet nicht (DOUT bleibt high) – Verkabelung prüfen."); return; }
    dmsNull = summe / n;
    std::printf("DMS tariert: Nullwert = %ld (aus %d Messungen)\n", dmsNull, n);
}

// Wird ständig aufgerufen; liest nur, wenn der HX711 einen neuen Wert hat.
static void dmsPoll() {
    if (!DMS_AKTIV || !hxBereit()) return;
    long roh = hxLesen() - dmsNull;
    auto jetzt = std::chrono::steady_clock::now();
    if (jetzt >= dmsNaechsteAusgabe) {
        std::printf("DMS: %9ld counts  = %10.3f\n", roh, roh * DMS_FAKTOR);
        std::fflush(stdout);
        dmsNaechsteAusgabe = jetzt + std::chrono::milliseconds(DMS_AUSGABE_MS);
    }
}

// ============================================================================
// Logik
// ============================================================================
enum Richtung { KEINE, HOCH, RUNTER };   // HOCH = rechts, RUNTER = links

/* --- Tastersteuerung (auskommentiert) ---
static Richtung gewuenschteRichtung() {
    int up = gpio.read(TASTER_UP), down = gpio.read(TASTER_DOWN);
    if (up && !down) return HOCH;
    if (down && !up) return RUNTER;
    return KEINE;
}
--- Ende Tastersteuerung --- */

static bool faultOk() { return gpio.read(FAULT) == 1; }   // FAULT ist low-aktiv

int main() {
    if (!gpio.open()) return 1;
    std::signal(SIGINT, onSignal);
    std::signal(SIGTERM, onSignal);

    gpio.output(STEP); gpio.output(DIR);
    gpio.output(SLP, 0); warteUs(1000);       // Treiber kurz schlafen legen = Register-Reset
    gpio.write(SLP, 1);                       // Treiber aufwecken
    warteUs(5000);                            // Aufwachzeit abwarten (> 1.2 ms)
    // gpio.input(TASTER_UP, Gpio::DOWN);     // Tastersteuerung auskommentiert
    // gpio.input(TASTER_DOWN, Gpio::DOWN);
    gpio.input(FAULT, Gpio::UP);
    if (DMS_AKTIV) {
        gpio.output(HX_SCK, 0);                       // SCK low = HX711 aktiv
        gpio.input(HX_DOUT, Gpio::UP);                // nicht angeschlossen -> "nicht bereit"
    }

    if (SPI_AKTIV) {
        gpio.output(SPI_SCLK, 0); gpio.output(SPI_SDI, 0); gpio.output(SPI_SCS, 1);
        gpio.input(SPI_SDO, Gpio::NONE);
        drvEnable();
    }

    if (DMS_AKTIV) dmsTarieren();

    /* --- Tastersteuerung (auskommentiert) ---
    std::puts("Bereit. Up/Down gedrückt halten zum Fahren. Ctrl+C = Ende.");
    int letzteMeldung = -1;

    while (laufen) {
        dmsPoll();
        Richtung r = gewuenschteRichtung();

        if (!faultOk()) {
            if (letzteMeldung != 99) { std::puts("FEHLER: DRV8434S meldet FAULT – Motor gesperrt."); letzteMeldung = 99; }
            warteUs(50000);
            continue;
        }

        if (r != KEINE) {
            std::printf("Fahre %s ...\n", r == HOCH ? "hoch" : "runter");
            letzteMeldung = -1;
            gpio.write(DIR, r == HOCH ? DIR_HOCH : 1 - DIR_HOCH);
            warteUs(5);                                   // DIR-Setup-Zeit

            double periode = PERIODE_START_US;
            long schritte = 0;
            while (laufen && gewuenschteRichtung() == r && faultOk()) {
                gpio.write(STEP, 1); warteUs(periode / 2);
                gpio.write(STEP, 0); warteUs(periode / 2);
                dmsPoll();                                // DMS auch während der Fahrt
                if (periode > PERIODE_MIN_US) periode *= RAMPE;
                ++schritte;
            }
            std::printf("Stopp nach %ld Schritten.\n", schritte);
        }

        if (r == KEINE) letzteMeldung = -1;
        usleep(10000);                                    // 10 ms, schont die CPU
    }

    --- Ende Tastersteuerung --- */

    std::printf("Bereit. Motor dreht je %.1f s rechts, dann links. Ctrl+C = Ende.\n", TAKT_S);

    Richtung r = HOCH;                                    // HOCH = rechts
    while (laufen) {
        dmsPoll();

        if (!faultOk()) {
            std::puts("FEHLER: DRV8434S meldet FAULT – Motor gesperrt.");
            while (laufen && !faultOk()) { dmsPoll(); usleep(50000); }
            continue;
        }

        std::printf("Drehe %s (%.1f s) ...\n", r == HOCH ? "rechts" : "links", TAKT_S);
        gpio.write(DIR, r == HOCH ? DIR_HOCH : 1 - DIR_HOCH);
        warteUs(5);                                       // DIR-Setup-Zeit

        const double zielPeriode = PERIODE_MIN_US / GESCHWINDIGKEIT;   // 20 % -> 2500 µs
        double periode = PERIODE_START_US > zielPeriode ? PERIODE_START_US : zielPeriode;
        long schritte = 0;
        auto ende = std::chrono::steady_clock::now() + std::chrono::duration<double>(TAKT_S);
        while (laufen && faultOk() && std::chrono::steady_clock::now() < ende) {
            gpio.write(STEP, 1); warteUs(periode / 2);
            gpio.write(STEP, 0); warteUs(periode / 2);
            dmsPoll();                                    // DMS auch während der Fahrt
            if (periode > zielPeriode) { periode *= RAMPE; if (periode < zielPeriode) periode = zielPeriode; }
            ++schritte;
        }
        std::printf("Stopp nach %ld Schritten.\n", schritte);

        r = (r == HOCH) ? RUNTER : HOCH;                  // Richtung wechseln
    }

    gpio.write(STEP, 0);
    std::puts("\nBeendet.");
    return 0;
}
