"""
VORSCHLAG: So könnte auswertung.py die Linienerkennung aufrufen.

verarbeite() bekommt jedes Live-Bild als OpenCV-Bild (BGR) und gibt
einen Text zurück, der auf dem Handy erscheint,
z.B. "Abstand: 1234.5 px (verfolgt)".

Ablauf:
1. Im ersten Bild wird das Linienpaar im ganzen Bild gesucht.
   Der Text endet dann mit "(gefunden)".
2. Stimmt das Paar, ruft das Programm einmal bestaetigen() auf
   (z.B. über einen Knopf auf dem Handy).
3. Ab jetzt wird nicht mehr gesucht, sondern nur noch von Bild zu
   Bild verfolgt. Der Text endet mit "(verfolgt)".
4. Geht das Paar verloren, kommt "Markierungen verloren". Sobald
   dieselben Markierungen wieder sichtbar sind, geht die Verfolgung
   von selbst weiter. Ein anderes Paar wird nie übernommen: Für eine
   neue Probe muss das Programm neu_suchen() aufrufen.

Testen mit:
python beispiel_auswertung.py
python beispiel_auswertung.py test_images/Testbild_0.1.png
"""

import os
import sys

import cv2

# Ordner, in dem main.py und config.py der Linienerkennung liegen.
# Hier: derselbe Ordner wie diese Datei. Auf dem Raspberry Pi den
# richtigen Pfad eintragen, z.B. "/home/pi/LineDetection".
LINE_DETECTION_FOLDER = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, LINE_DETECTION_FOLDER)

import config
import main

# Live-Betrieb: keine Detail-Ausgaben und keine Fenster
config.PRINT_DETAILS = False
config.SHOW_INTERMEDIATE_IMAGES = False

# Merkt sich das Linienpaar von Bild zu Bild
tracker = main.create_tracker()


def bestaetigen():
    """
    Bestätigt das zuletzt gefundene Linienpaar.
    Ab dann wird nur noch verfolgt statt neu gesucht.

    Rückgabe: True, wenn ein Paar zum Bestätigen vorhanden war.
    """

    return main.confirm_tracker(tracker)


def neu_suchen():
    """Vergisst das Linienpaar und sucht wieder im ganzen Bild."""

    main.reset_tracker(tracker)


def verarbeite(bild):
    """
    Misst den Abstand der beiden Markierungen im Bild.

    Rückgabe: Text mit dem Abstand in Pixel oder None.
    """

    if bild is None:
        return None

    # Ein Fehler in einem einzelnen Bild darf die
    # Live-Auswertung nicht beenden.
    try:
        selected_pair, distance_px = main.process_frame(bild, tracker)

    except Exception as error:
        print("Fehler in der Linienerkennung:", error)
        return None

    if tracker["status"] == "verloren":
        return "Markierungen verloren"

    if selected_pair is None:
        return None

    return f"Abstand: {distance_px:.1f} px ({tracker['status']})"


if __name__ == "__main__":

    # Kleiner Test: Demo-Bild oder ein Bild von der Festplatte
    if len(sys.argv) > 1:
        test_image = cv2.imread(sys.argv[1], cv2.IMREAD_COLOR)
    else:
        test_image = main.create_demo_image()

    # 1. Bild: suchen
    print(verarbeite(test_image))

    # Bestätigen, danach wird nur noch verfolgt
    print("Bestätigt:", bestaetigen())

    print(verarbeite(test_image))
