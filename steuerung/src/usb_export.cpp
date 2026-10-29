#include "usb_export.hpp"

UsbExport::UsbExport(std::string suchordner) : suchordner_(std::move(suchordner)) {}

std::string UsbExport::stickFinden() const {
    // TODO: unter suchordner_ (z.B. /media/pi/*) das erste beschreibbare Verzeichnis suchen
    return "";
}

bool UsbExport::kopieren(const std::string& datei) const {
    (void)datei;
    // TODO: Stick finden, Ordner "pruefstand" anlegen, Datei kopieren, danach sync() (Daten wirklich schreiben)
    return false;
}

int UsbExport::alleKopieren(const std::string& datenOrdner) const {
    (void)datenOrdner;
    // TODO: alle *.csv im Datenordner kopieren, die auf dem Stick noch fehlen
    return 0;
}
