"""Deine Auswertung des Live-Bilds.

verarbeite() bekommt jedes Live-Bild als OpenCV-Bild (numpy-Array, BGR, 1920x1080, 15 Bilder/s) und laeuft in einem eigenen
Thread. Gibt sie einen Text zurueck, erscheint er auf dem Handy unter "Auswertung". None zeigt nichts Neues an.
Ist sie langsamer als die Kamera, werden Bilder ausgelassen; sie bekommt immer das neueste.

Beispiel unten: zeigt einmal pro Sekunde Bildgroesse, Bilder pro Sekunde und mittlere Helligkeit.
Fuer OpenCV:  import cv2  (auf dem Pi: sudo apt install python3-opencv)
"""
import time

_start = None
_count = 0


def verarbeite(bild):
    global _start, _count
    now = time.monotonic()
    if _start is None:
        _start = now
    _count += 1
    if now - _start < 1:
        return None

    fps = _count / (now - _start)
    _start, _count = now, 0
    hoehe, breite = bild.shape[:2]
    return f"{breite}×{hoehe} · {fps:.0f} Bilder/s · Helligkeit {bild.mean():.0f}"
