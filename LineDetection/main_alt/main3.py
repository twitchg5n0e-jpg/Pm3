
import cv2
import numpy as np
import argparse
import os

import config


def create_demo_image():
    """Erzeugt ein Testbild mit unterschiedlich langen und unregelmäßigen Linien."""

    image = np.ones((900, 1200), dtype=np.uint8) * 255

    # ==========================================
    # GESUCHTE LINIEN
    # Gemeinsamer Neigungswinkel ca. 10°
    # Leichte Unregelmäßigkeiten
    # Zweite Linie ca. 15 % kürzer
    # ==========================================

    line1 = np.array([
        [120, 200],
        [270, 173],
        [420, 180],
        [570, 148],
        [720, 155],
        [870, 124]
    ], dtype=np.int32)

    line2 = np.array([
        [180, 405],
        [310, 378],
        [440, 387],
        [570, 355],
        [700, 362]
    ], dtype=np.int32)

    cv2.polylines(image, [line1], False, 0, 9)
    cv2.polylines(image, [line2], False, 0, 9)

    # ==========================================
    # STÖRLINIEN
    # Teilweise ähnliche Winkel
    # Unterschiedliche Längen
    # Keine Überschneidungen
    # ==========================================

    # 1. Lange Linie mit ähnlichem Winkel
    cv2.line(image, (100, 60), (850, 190), 0, 5)

    # 2. Lange Linie mit anderem Winkel
    cv2.line(image, (100, 550), (850, 680), 0, 5)

    # 3. Kurze Linie mit ähnlichem Winkel
    cv2.line(image, (850, 300), (1050, 335), 0, 6)

    # 4. Schräge Linie
    cv2.line(image, (100, 700), (350, 620), 0, 6)

    # 5. Vertikale Linie
    cv2.line(image, (1100, 100), (1100, 400), 0, 5)

    # 6. Horizontale Linie
    cv2.line(image, (500, 750), (850, 750), 0, 5)

    # 7. Kurze diagonale Linie
    cv2.line(image, (450, 480), (600, 520), 0, 5)

    # 8. Lange Linie mit leicht anderem Winkel
    cv2.line(image, (450, 820), (1000, 750), 0, 5)

    # 9. Kurze vertikale Linie
    cv2.line(image, (50, 300), (50, 430), 0, 5)

    # 10. Schräge Linie im rechten unteren Bereich
    cv2.line(image, (900, 550), (1100, 600), 0, 5)

    return image


def preprocess(image):
    """Erzeugt ein Binärbild."""

    if config.MODE == "BLACK_ON_WHITE":
        threshold_type = cv2.THRESH_BINARY_INV

    elif config.MODE == "WHITE_ON_BLACK":
        threshold_type = cv2.THRESH_BINARY

    else:
        raise ValueError("Unbekannter Kontrastmodus")

    _, binary = cv2.threshold(
        image,
        config.THRESHOLD,
        255,
        threshold_type
    )

    return binary



def detect_lines(binary):
    """
    Erkennt Liniensegmente mit HoughLinesP und fasst
    räumlich und geometrisch zusammengehörige Segmente
    zu einer gemeinsamen Linie zusammen.
    """

    # ------------------------------------------
    # 1. Hough-Linien erkennen
    # ------------------------------------------

    segments = cv2.HoughLinesP(
        binary,
        rho=config.HOUGH_RHO,
        theta=config.HOUGH_THETA,
        threshold=config.HOUGH_THRESHOLD,
        minLineLength=config.HOUGH_MIN_LINE_LENGTH,
        maxLineGap=config.HOUGH_MAX_LINE_GAP
    )

    if segments is None:
        return []

    print("HoughLinesP Shape:", segments.shape)
    print("HoughLinesP Datentyp:", segments.dtype)

    groups = []

    # ------------------------------------------
    # 2. Segmente vorbereiten und gruppieren
    # ------------------------------------------

    for segment in segments:

        segment = np.asarray(segment).reshape(-1)

        if segment.size != 4:
            continue

        x1, y1, x2, y2 = segment.astype(int)

        p1 = np.array([x1, y1], dtype=float)
        p2 = np.array([x2, y2], dtype=float)

        direction = p2 - p1
        length = np.linalg.norm(direction)

        if length < 2:
            continue

        direction /= length

        # Einheitliche Richtung
        if direction[0] < 0:
            direction = -direction

        normal = np.array([
            -direction[1],
            direction[0]
        ])

        angle = np.degrees(
            np.arctan2(direction[1], direction[0])
        ) % 180

        center = (p1 + p2) / 2

        # Position relativ zur Normalen
        offset = np.dot(center, normal)

        # Projektion auf die Linienrichtung
        start = np.dot(p1, direction)
        end = np.dot(p2, direction)

        segment_data = {
            "p1": p1,
            "p2": p2,
            "direction": direction,
            "normal": normal,
            "angle": angle,
            "offset": offset,
            "start": min(start, end),
            "end": max(start, end)
        }

        # --------------------------------------
        # 3. Passende Gruppe suchen
        # --------------------------------------

        best_group = None
        best_difference = float("inf")

        for group in groups:

            angle_diff = angle_difference(
                angle,
                group["angle"]
            )

            if angle_diff > config.SEGMENT_ANGLE_TOLERANCE:
                continue

            offset_diff = abs(
                offset - group["offset"]
            )

            if offset_diff > config.SEGMENT_DISTANCE_TOLERANCE:
                continue

            gap = max(
                0,
                max(group["start"], segment_data["start"])
                - min(group["end"], segment_data["end"])
            )

            if gap > config.SEGMENT_MAX_GAP:
                continue

            difference = angle_diff + offset_diff * 0.01

            if difference < best_difference:
                best_difference = difference
                best_group = group

        # --------------------------------------
        # 4. Gruppe erweitern oder neu erstellen
        # --------------------------------------

        if best_group is not None:

            best_group["segments"].append(segment_data)

            best_group["start"] = min(
                best_group["start"],
                segment_data["start"]
            )

            best_group["end"] = max(
                best_group["end"],
                segment_data["end"]
            )

            best_group["offset"] = np.mean([
                s["offset"] for s in best_group["segments"]
            ])

        else:

            groups.append({
                "segments": [segment_data],
                "angle": angle,
                "offset": offset,
                "start": segment_data["start"],
                "end": segment_data["end"]
            })

    # ------------------------------------------
    # 5. Gruppen zu endgültigen Linien machen
    # ------------------------------------------

    candidates = []

    for group in groups:

        points = []

        for segment in group["segments"]:
            points.append(segment["p1"])
            points.append(segment["p2"])

        points = np.array(points, dtype=np.float32)

        if len(points) < 2:
            continue

        # Gerade an alle Segmentendpunkte anpassen
        vx, vy, x0, y0 = cv2.fitLine(
            points,
            cv2.DIST_L2,
            0,
            0.01,
            0.01
        ).flatten()

        direction = np.array([vx, vy], dtype=float)
        direction /= np.linalg.norm(direction)

        # Einheitliche Richtung
        if direction[0] < 0:
            direction = -direction

        normal = np.array([
            -direction[1],
            direction[0]
        ])

        center = np.array([x0, y0], dtype=float)

        centered = points - center

        projections = centered @ direction
        across = centered @ normal

        start = np.percentile(projections, 1)
        end = np.percentile(projections, 99)

        length = end - start

        thickness = (
            np.percentile(across, 95)
            - np.percentile(across, 5)
        )

        if length < config.MIN_LINE_LENGTH:
            continue

        p1 = center + direction * start
        p2 = center + direction * end

        angle = np.degrees(
            np.arctan2(direction[1], direction[0])
        ) % 180

        candidates.append({
            "center": center,
            "direction": direction,
            "normal": normal,
            "angle": angle,
            "length": length,
            "thickness": thickness,
            "p1": p1,
            "p2": p2
        })

    return candidates


def angle_difference(angle1, angle2):
    """Kleinster Winkel zwischen zwei ungerichteten Linien."""

    difference = abs(angle1 - angle2)

    return min(difference, 180 - difference)



def calculate_overlap_ratio(line1, line2):
    """
    Berechnet, wie stark sich zwei Linien
    entlang ihrer gemeinsamen Richtung überlappen.
    """

    direction1 = line1["direction"]
    direction2 = line2["direction"]

    if np.dot(direction1, direction2) < 0:
        direction2 = -direction2

    direction = direction1 + direction2
    direction /= np.linalg.norm(direction)

    # Endpunkte auf gemeinsame Richtung projizieren
    projections1 = [
        np.dot(line1["p1"], direction),
        np.dot(line1["p2"], direction)
    ]

    projections2 = [
        np.dot(line2["p1"], direction),
        np.dot(line2["p2"], direction)
    ]

    min1, max1 = min(projections1), max(projections1)
    min2, max2 = min(projections2), max(projections2)

    # Gemeinsame Länge
    overlap = max(
        0,
        min(max1, max2) - max(min1, min2)
    )

    # Länge der kürzeren Linie
    shorter_length = min(
        max1 - min1,
        max2 - min2
    )

    if shorter_length <= 0:
        return 0

    return overlap / shorter_length



def select_line_pair(candidates):
    """
    Sucht das am besten passende Linienpaar.

    Kriterien:
    1. Parallelität
    2. Ähnliche Linienlänge
    3. Überlappung in Linienrichtung

    Der Abstand zwischen den Linien wird nicht bewertet.
    """

    best_pair = None
    best_score = float("inf")

    for i in range(len(candidates)):

        for j in range(i + 1, len(candidates)):

            line1 = candidates[i]
            line2 = candidates[j]

            # 1. Parallelität
            angle_diff = angle_difference(
                line1["angle"],
                line2["angle"]
            )

            if angle_diff > config.MAX_ANGLE_DIFFERENCE:
                continue

            angle_score = (
                angle_diff / config.MAX_ANGLE_DIFFERENCE
            )

            # 2. Ähnliche Linienlänge
            length1 = line1["length"]
            length2 = line2["length"]

            length_ratio = min(length1, length2) / max(
                length1, length2
            )

            length_difference = 1.0 - length_ratio

            if length_difference > config.MAX_LENGTH_DIFFERENCE:
                continue

            length_score = (
                length_difference / config.MAX_LENGTH_DIFFERENCE
            )

            # 3. Überlappung
            overlap_ratio = calculate_overlap_ratio(
                line1, line2
            )

            if overlap_ratio < config.MIN_OVERLAP_RATIO:
                continue

            overlap_score = 1.0 - overlap_ratio

            # 4. Gesamtbewertung
            score = (
                config.ANGLE_WEIGHT * angle_score
                + config.LENGTH_WEIGHT * length_score
                + config.OVERLAP_WEIGHT * overlap_score
            )

            if score < best_score:

                best_score = score
                best_pair = (line1, line2)

    return best_pair



def calculate_distance(line1, line2):
    """Berechnet den senkrechten Linienabstand."""

    direction1 = line1["direction"]
    direction2 = line2["direction"]

    # Beide Richtungsvektoren gleich ausrichten
    if np.dot(direction1, direction2) < 0:
        direction2 = -direction2

    direction = direction1 + direction2
    direction /= np.linalg.norm(direction)

    normal = np.array([-direction[1], direction[0]])

    # Differenz der Linienmittelpunkte
    center_difference = (
        line2["center"] - line1["center"]
    )

    distance_pixels = abs(
        np.dot(center_difference, normal)
    )

    distance_mm = (
        distance_pixels * config.MM_PER_PIXEL
    )

    return distance_pixels, distance_mm


def draw_results(image, candidates, selected_pair):

    result = cv2.cvtColor(
        image,
        cv2.COLOR_GRAY2BGR
    )

    # Alle gefundenen Kandidaten gelb darstellen
    for line in candidates:

        p1 = tuple(np.round(line["p1"]).astype(int))
        p2 = tuple(np.round(line["p2"]).astype(int))

        cv2.line(result, p1, p2, (0, 255, 255), 2)

    if selected_pair is not None:

        colors = [(0, 255, 0), (255, 0, 0)]

        for line, color in zip(selected_pair, colors):

            p1 = tuple(np.round(line["p1"]).astype(int))
            p2 = tuple(np.round(line["p2"]).astype(int))

            cv2.line(result, p1, p2, color, 3)

            center = tuple(
                np.round(line["center"]).astype(int)
            )

            cv2.circle(result, center, 5, (0, 0, 255), -1)

    return result


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        type=str,
        default=None,
        help="Pfad zum Eingabebild"
    )

    args = parser.parse_args()

    # Bild laden oder Testbild erzeugen
    if args.image is None:

        image = create_demo_image()

        os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)

        cv2.imwrite(
            f"{config.OUTPUT_FOLDER}/demo_input.png",
            image
        )

    else:

        image = cv2.imread(
            args.image,
            cv2.IMREAD_GRAYSCALE
        )

        if image is None:
            raise FileNotFoundError(
                f"Bild konnte nicht geladen werden: {args.image}"
            )

    # Bildverarbeitung
    binary = preprocess(image)

    candidates = detect_lines(binary)

    print(f"\nGefundene Linienkandidaten: {len(candidates)}")

    selected_pair = select_line_pair(candidates)

    if selected_pair is None:

        print("Kein passendes Linienpaar gefunden.")

    else:

        distance_px, distance_mm = calculate_distance(
            selected_pair[0],
            selected_pair[1]
        )

        angle_diff = angle_difference(
            selected_pair[0]["angle"],
            selected_pair[1]["angle"]
        )

        length_difference = 1.0 - min(
            selected_pair[0]["length"],
            selected_pair[1]["length"]
        ) / max(
            selected_pair[0]["length"],
            selected_pair[1]["length"]
        )

        overlap_ratio = calculate_overlap_ratio(
            selected_pair[0],
            selected_pair[1]
        )

        print("\nErkanntes Linienpaar:")
        print(f"Linie 1 Winkel: {selected_pair[0]['angle']:.2f}°")
        print(f"Linie 2 Winkel: {selected_pair[1]['angle']:.2f}°")
        print(f"Winkeldifferenz: {angle_diff:.2f}°")
        print(f"Längendifferenz: {length_difference * 100:.2f}%")
        print(f"Überlappungskoeffizient: {overlap_ratio * 100:.2f}%")

        print(f"\nAbstand: {distance_px:.2f} Pixel")
        print(f"Abstand: {distance_mm:.2f} mm")

    # Ergebnisse unabhängig von der Linienauswahl darstellen
#    for i, line in enumerate(candidates):
#        print(
#            f"Linie {i + 1}: "
#            f"Winkel={line['angle']:.2f}°, "
#            f"Länge={line['length']:.1f}px, "
#            f"Dicke={line['thickness']:.1f}px"
#        )
    

    result = draw_results(
        image,
        candidates,
        selected_pair
    )

    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)

    cv2.imwrite(
        f"{config.OUTPUT_FOLDER}/result.png",
        result
    )

    if config.SHOW_INTERMEDIATE_IMAGES:

        cv2.imshow("Original", image)
        cv2.imshow("Binary", binary)
        cv2.imshow("Line Detection", result)

        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

#mit Testbildern Programm starten:
#python main.py --image test_images/test_01.png

#threshhold and componend labeling