// =============================================================================
// Dehnmessstreifen allein auslesen  –  Raspberry Pi 4 + HX711
//
//   Liest den HX711 (DOUT=GPIO23, SCK=GPIO24), Kanal A, Verstärkung 128.
//   Beim Start wird tariert (Nullwert), danach wird jede Kraft in N ausgegeben
//   (bzw. höchstens alle DMS_AUSGABE_MS). Kein Motor, kein SPI.
//
//   Tasten während des Laufs (Enter drücken):
//     t        -> neu tarieren (ohne Last!)
//     k 500    -> kalibrieren mit 500 g Gewicht (gibt N_PRO_COUNT zum Eintragen aus)
//
//   Ausgabe: Brückenspannung U (mV, roh), dU (mV, seit Tara) und Kraft in Newton. dmsNewton() gibt die Kraft als Zahl zurück.
//
// Kompilieren:  g++ -O2 -std=c++17 -o dms dms.cpp     (oder: make dms)
// Starten:      ./dms                                 (Beenden mit Ctrl+C)
//
// Greift direkt über /dev/gpiomem auf die GPIO-Register des BCM2711 zu
// -> keine Zusatzbibliothek nötig. Nur für Raspberry Pi 4 (nicht Pi 5)!
// =============================================================================
#include <chrono>
#include <cmath>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <fcntl.h>
#include <poll.h>
#include <sys/mman.h>
#include <unistd.h>

// ---------------- Pins (BCM) ----------------
constexpr int HX_DOUT = 23, HX_SCK = 24;

// ---------------- Einstellungen ----------------
// Newton pro Count. Mit "k <Gramm>" kalibrieren und den ausgegebenen Wert hier eintragen.
// 1.0 = noch nicht kalibriert (dann sind die "Newton" in Wahrheit Counts).
constexpr double N_PRO_COUNT       = 1.0;
constexpr double ERDBESCHLEUNIGUNG = 9.81;  // m/s²
constexpr int    KAL_MESSUNGEN     = 20;    // Anzahl Messungen fürs Kalibrieren
constexpr int    DMS_AUSGABE_MS = 0;    // 0 = jeden Messwert ausgeben, sonst Mindestabstand in ms
constexpr int    TARA_MESSUNGEN = 10;   // Anzahl Messungen für den Nullwert
// Analoge Speisung des HX711 (= Brückenspeisung E+). Auf den üblichen Modulen ca. 4.3 V
// bei 5-V-Versorgung; am besten zwischen E+ und E- nachmessen und hier eintragen.
constexpr double HX_AVDD        = 4.3;  // V
constexpr double HX_GAIN        = 128;  // Kanal A

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
        volatile uint32_t* r = reg_ + (0xE4 / 4) + pin / 16;   // GPIO_PUP_PDN_CNTRL_REG
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

static void warteUs(double us) {
    auto ende = std::chrono::steady_clock::now() + std::chrono::duration<double, std::micro>(us);
    while (std::chrono::steady_clock::now() < ende) {}
}

// ============================================================================
// HX711 – Kanal A, Verstärkung 128
// ============================================================================
static long   dmsNull   = 0;
static double nProCount = N_PRO_COUNT;
static long   dmsRoh    = 0;                      // letzter Rohwert (ohne Tara)

// Rohwert -> Differenzspannung am HX711-Eingang (A+ - A-) in Millivolt.
// Vollausschlag 2^23 counts = 0.5 * AVDD / Gain  (bei 4.3 V und Gain 128: ca. 16.8 mV).
static double hxMillivolt(long counts) {
    return counts / 8388608.0 * (0.5 * HX_AVDD / HX_GAIN) * 1000.0;
}

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

// Mittelwert von n Rohwerten (ohne Tara). false, wenn der HX711 nicht antwortet.
static bool hxMittel(int n, double& mittel) {
    long summe = 0; int k = 0;
    auto ende = std::chrono::steady_clock::now() + std::chrono::milliseconds(300 * n + 1000);
    while (laufen && k < n && std::chrono::steady_clock::now() < ende) {
        if (hxBereit()) { summe += hxLesen(); ++k; }
        else usleep(1000);
    }
    if (k == 0) return false;
    mittel = double(summe) / k;
    return true;
}

static bool dmsTarieren() {
    double m;
    if (!hxMittel(TARA_MESSUNGEN, m)) {
        std::puts("WARNUNG: HX711 antwortet nicht (DOUT bleibt high) – Verkabelung prüfen.");
        return false;
    }
    dmsNull = std::lround(m);
    std::printf("DMS tariert: Nullwert = %ld\n", dmsNull);
    return true;
}

// Kalibrieren: bekanntes Gewicht (in Gramm) liegt auf -> Newton pro Count berechnen.
// Vorher OHNE Gewicht tarieren!
static void dmsKalibrieren(double gramm) {
    double m;
    if (gramm <= 0 || !hxMittel(KAL_MESSUNGEN, m)) { std::puts("Kalibrieren fehlgeschlagen."); return; }
    double counts = m - dmsNull;
    if (std::fabs(counts) < 100) { std::puts("Kalibrieren fehlgeschlagen: kaum Ausschlag – liegt das Gewicht drauf?"); return; }
    double newton = gramm / 1000.0 * ERDBESCHLEUNIGUNG;
    nProCount = newton / counts;
    std::printf("Kalibriert: %.1f g = %.4f N = %.0f counts\n", gramm, newton, counts);
    std::printf(">>> Oben im Code eintragen:  constexpr double N_PRO_COUNT = %.6e;\n", nProCount);
}

// Gibt die aktuelle Kraft in NEWTON zurück (tariert und kalibriert).
// Wartet auf den nächsten Messwert des HX711 (max. timeoutMs).
// Kommt in dieser Zeit nichts (oder Ctrl+C), wird NAN zurückgegeben.
static double dmsNewton(int timeoutMs = 1000) {
    auto ende = std::chrono::steady_clock::now() + std::chrono::milliseconds(timeoutMs);
    while (!hxBereit()) {
        if (!laufen || std::chrono::steady_clock::now() >= ende) return NAN;
        usleep(1000);                             // HX711 liefert 10 bzw. 80 Werte/s
    }
    dmsRoh = hxLesen();
    return (dmsRoh - dmsNull) * nProCount;
}

// Liest ohne zu blockieren eine Eingabezeile: "t" = tarieren, "k 500" = kalibrieren mit 500 g.
static void befehlePruefen() {
    pollfd pfd{STDIN_FILENO, POLLIN, 0};
    if (poll(&pfd, 1, 0) <= 0 || !(pfd.revents & POLLIN)) return;
    char buf[64];
    ssize_t n = ::read(STDIN_FILENO, buf, sizeof buf - 1);
    if (n <= 0) return;
    buf[n] = '\0';
    double gramm;
    if (buf[0] == 't' || buf[0] == 'T') dmsTarieren();
    else if ((buf[0] == 'k' || buf[0] == 'K') && std::sscanf(buf + 1, "%lf", &gramm) == 1) dmsKalibrieren(gramm);
    else std::puts("Befehle: t = tarieren,  k <Gramm> = kalibrieren (z.B. k 500)");
}

int main() {
    if (!gpio.open()) return 1;
    std::signal(SIGINT, onSignal);
    std::signal(SIGTERM, onSignal);

    gpio.output(HX_SCK, 0);                       // SCK low = HX711 aktiv
    gpio.input(HX_DOUT, Gpio::UP);                // nicht angeschlossen -> "nicht bereit"

    dmsTarieren();
    if (N_PRO_COUNT == 1.0)
        std::puts("HINWEIS: noch nicht kalibriert – Gewicht auflegen und z.B. 'k 500' + Enter (500 g).");
    std::puts("Messe ... (t = tarieren, k <Gramm> = kalibrieren, Ctrl+C = Ende)");

    auto naechsteAusgabe = std::chrono::steady_clock::now();

    while (laufen) {
        befehlePruefen();

        double kraft = dmsNewton();
        if (std::isnan(kraft)) {
            if (laufen) std::puts("WARNUNG: seit 1 s kein neuer Messwert vom HX711.");
            continue;
        }

        auto jetzt = std::chrono::steady_clock::now();
        if (jetzt >= naechsteAusgabe) {
            std::printf("U = %8.4f mV   dU = %8.4f mV   F = %9.3f N\n",
                        hxMillivolt(dmsRoh), hxMillivolt(dmsRoh - dmsNull), kraft);
            std::fflush(stdout);
            naechsteAusgabe = jetzt + std::chrono::milliseconds(DMS_AUSGABE_MS);
        }
    }
    gpio.write(HX_SCK, 0);
    std::puts("\nBeendet.");
    return 0;
}
