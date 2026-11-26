"""
Testet die Linienerkennung mit dem Demo-Bild und allen Testbildern.

Die Sollwerte wurden von Hand nachgemessen (Mittelachsen der beiden
schwarzen Markierungen, Abstand in Pixel bei voller Auflösung).

Starten mit:
python test_messung.py
"""

import contextlib
import io
import os
import time

import cv2
import numpy as np

import config
import main


# Sollabstand in Pixel und erlaubte Abweichung in Pixel.
# Die Abweichung entspricht der Unsicherheit der Handmessung
# (bei Testbild_1.3 glitzert das untere Band, darum 4 Pixel).
EXPECTED_DISTANCES = {
    "Demo": (207.1, 3.0),
    "Testbild_0.1.png": (1864.2, 3.0),
    "Testbild_0.2.png": (1838.6, 3.0),
    "Testbild_0.3.png": (1842.4, 3.0),
    "Testbild_0.4.png": (1596.3, 3.0),
    "Testbild_0.5.png": (974.3, 2.0),
    "Testbild_0.6.png": (1676.3, 3.0),
    "Testbild_1.0.png": (1399.5, 2.5),
    "Testbild_1.1.png": (1600.5, 2.5),
    "Testbild_1.2.png": (1775.3, 2.5),
    "Testbild_1.3.png": (1625.6, 4.0),
}


def run_tests():

    folder = os.path.dirname(os.path.abspath(__file__))

    failed = 0

    for name, (expected, tolerance) in EXPECTED_DISTANCES.items():

        if name == "Demo":
            image = main.create_demo_image()

        else:
            image = cv2.imread(
                os.path.join(folder, "test_images", name),
                cv2.IMREAD_COLOR
            )

            if image is None:
                print(f"{name}: FEHLER (Bild nicht gefunden)")
                failed += 1
                continue

        start = time.time()

        # Ausgaben der Erkennung unterdrücken
        with contextlib.redirect_stdout(io.StringIO()):
            pair, distance = main.process_image(image)

        duration = time.time() - start

        if pair is None:
            print(f"{name}: FEHLER (kein Linienpaar gefunden)")
            failed += 1
            continue

        error = distance - expected

        if abs(error) <= tolerance:
            status = "OK"

        else:
            status = "FEHLER"
            failed += 1

        print(
            f"{name}: {status}  "
            f"gemessen={distance:.2f}px, "
            f"soll={expected:.1f}px, "
            f"Abweichung={error:+.2f}px, "
            f"Zeit={duration:.2f}s"
        )

    total = len(EXPECTED_DISTANCES)

    print(f"\n{total - failed} von {total} Tests bestanden")

    return failed == 0


def run_tracking_tests():
    """
    Testet die Verfolgung von Bild zu Bild (process_frame).

    Das Bild wird in mehreren Schritten verschoben. Im ersten Bild
    wird gesucht und bestätigt, danach muss das Paar verfolgt werden
    und der Abstand gleich bleiben (höchstens 2 Pixel Unterschied).
    """

    folder = os.path.dirname(os.path.abspath(__file__))

    failed = 0

    names = ["Demo", "Testbild_0.1.png", "Testbild_1.3.png"]

    for name in names:

        if name == "Demo":
            image = main.create_demo_image()

        else:
            image = cv2.imread(
                os.path.join(folder, "test_images", name),
                cv2.IMREAD_COLOR
            )

            if image is None:
                print(f"Verfolgung {name}: FEHLER (Bild nicht gefunden)")
                failed += 1
                continue

        height, width = image.shape[:2]

        tracker = main.create_tracker()

        distances = []
        states = []

        for step in range(6):

            # Verschiebung relativ zur Bildgrösse (ca. 0.4 % je Bild)
            shift_x = step * width * 0.004
            shift_y = step * height * 0.003

            matrix = np.float32([
                [1, 0, shift_x],
                [0, 1, shift_y]
            ])

            frame = cv2.warpAffine(
                image,
                matrix,
                (width, height),
                borderMode=cv2.BORDER_REPLICATE
            )

            with contextlib.redirect_stdout(io.StringIO()):
                pair, distance = main.process_frame(frame, tracker)

            states.append(tracker["status"])
            distances.append(distance)

            # Nach dem ersten Bild bestätigen
            if step == 0:
                main.confirm_tracker(tracker)

        ok = (
            states[0] == "gefunden"
            and states[1:] == ["verfolgt"] * 5
            and max(distances) - min(distances) <= 2.0
        )

        if ok:
            print(
                f"Verfolgung {name}: OK  "
                f"Abstand {min(distances):.2f} bis {max(distances):.2f}px"
            )

        else:
            print(f"Verfolgung {name}: FEHLER  Zustände: {states}")
            failed += 1

    print(f"\n{len(names) - failed} von {len(names)} Tests bestanden")

    return failed == 0


if __name__ == "__main__":

    measurement_ok = run_tests()

    print()

    tracking_ok = run_tracking_tests()

    if not (measurement_ok and tracking_ok):
        raise SystemExit(1)
