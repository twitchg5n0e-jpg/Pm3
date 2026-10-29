"""Auswertung des Live-Bilds vom Handy.

verarbeite() bekommt jedes Live-Bild als OpenCV-Bild (numpy-Array, BGR, 1920x1080) und laeuft in einem eigenen
Thread. Gibt sie einen Text zurueck, erscheint er auf dem Handy unter "Auswertung" und landet in der Spalte
"optik" der Messdatei. None zeigt nichts Neues an.
"""


def verarbeite(bild):
    # TODO: z.B. Marker / Kalibrierplatte finden, Massstab mm pro Pixel bestimmen,
    #       Kanten des Bauteils finden, Laenge in mm berechnen
    return None
