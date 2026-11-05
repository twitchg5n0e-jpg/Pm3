// =============================================================================
// config.hpp – alle Einstellwerte des Pruefstands an einem Ort
// =============================================================================
// Hier stehen alle festen Zahlen und Pfade, die das Programm braucht. Zu jedem Wert steht, woher
// er kommt bzw. wovon er abhaengt. Wer etwas aendern will, aendert es nur hier.
#pragma once

namespace config {

// -----------------------------------------------------------------------------
// Netzwerk
// -----------------------------------------------------------------------------

// HTTP: zum Testen am PC (http://localhost) und damit das Handy das CA-Zertifikat laden kann.
inline constexpr int HTTP_PORT = 8080;

// HTTPS: Bedienung vom Handy aus. Browser geben die Kamera nur ueber HTTPS (oder localhost) frei.
// Muss mit der Ausgabe in start.sh uebereinstimmen.
inline constexpr int HTTPS_PORT = 8443;

// So lange wartet die Hauptschleife hoechstens auf Netzwerkdaten. Muss deutlich kleiner sein als
// MESS_INTERVALL_MS, damit die Messung puenktlich bleibt.
inline constexpr int POLL_MS = 10;

// Groesste WebSocket-Nachricht (ein Video-Teil ist ca. 1 MB) steht im Makefile (MG_MAX_RECV_SIZE),
// weil Mongoose sie beim Kompilieren braucht.

// -----------------------------------------------------------------------------
// Daten speichern: false = keine CSV, kein Video, kein USB-Export (es wird nichts in daten/ angelegt).
// Fuer die Seite gibt es denselben Schalter oben im Skript von static/index.html.
// -----------------------------------------------------------------------------

inline constexpr bool DATEN_SPEICHERN = false;

// -----------------------------------------------------------------------------
// Pfade (relativ zum Projektordner; start.sh und "make run" starten dort)
// -----------------------------------------------------------------------------

inline constexpr const char* ORDNER_SEITEN = "static";               // Handy-Seite (index.html)
inline constexpr const char* ORDNER_MESSUNGEN = "daten/messungen";   // CSV pro Test
inline constexpr const char* ORDNER_AUFNAHMEN = "daten/aufnahmen";   // Video pro Test

// Werden von start.sh erzeugt. Fehlen sie, laeuft nur HTTP.
inline constexpr const char* DATEI_ZERTIFIKAT = "zertifikat/server.crt";
inline constexpr const char* DATEI_SCHLUESSEL = "zertifikat/server.key";
inline constexpr const char* DATEI_CA = "zertifikat/ca.crt";

// Hier haengt Linux USB-Sticks ein: Raspberry Pi OS unter /media/<user>, Fedora unter
// /run/media/<user>. Der Benutzername wird angehaengt.
inline constexpr const char* USB_ORDNER[] = {"/media/", "/run/media/"};

// -----------------------------------------------------------------------------
// Messung
// -----------------------------------------------------------------------------

// Abstand zwischen zwei Messungen: 50 ms = 20 Messungen pro Sekunde. Jede Messung wird sofort
// ans Handy geschickt; schneller bringt fuer die Anzeige nichts.
inline constexpr int MESS_INTERVALL_MS = 50;

// Bruch erkennen: Die Kraft faellt unter BRUCH_KRAFT_ANTEIL der bisher groessten Kraft.
// Erst ab BRUCH_AB_DEHNUNG pruefen, sonst loest das Rauschen am Anfang schon aus.
inline constexpr double BRUCH_KRAFT_ANTEIL = 0.5;
inline constexpr double BRUCH_AB_DEHNUNG = 0.05;   // 5 %

// -----------------------------------------------------------------------------
// Standardwerte der Probe, falls das Handy nichts schickt
// (gleich wie die Vorgaben der Eingabefelder in static/index.html)
// -----------------------------------------------------------------------------

inline constexpr double PROBE_LAENGE_MM = 50;
inline constexpr double PROBE_BREITE_MM = 10;
inline constexpr double PROBE_DICKE_MM = 2;
inline constexpr double PROBE_MAX_WEG_MM = 20;   // 40 % von 50 mm

}  // namespace config
