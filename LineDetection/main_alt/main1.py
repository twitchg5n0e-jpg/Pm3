
import cv2
import numpy as np
import argparse
import os

import config


def create_demo_image():
    """Erzeugt ein künstliches Testbild."""

    image = np.ones((600, 900), dtype=np.uint8) * 255

    # Zwei leicht unregelmäßige, schräge Linien
    line1 = np.array([
        [100, 180], [250, 175], [400, 180],
        [550, 174], [700, 178]
    ], dtype=np.int32)

    line2 = np.array([
        [100, 380], [250, 375], [400, 380],
        [550, 374], [700, 378]
    ], dtype=np.int32)

    cv2.polylines(image, [line1], False, 0, 9)
    cv2.polylines(image, [line2], False, 0, 9)

    # Zusätzliche Störlinien
    cv2.line(image, (50, 80), (800, 100), 0, 4)
    cv2.line(image, (300, 450), (600, 500), 0, 5)
    cv2.line(image, (750, 150), (800, 450), 0, 5)

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
    Erkennt zusammenhängende Linienbereiche.
    Bestimmt für jeden Bereich eine Ausgleichsgerade
    mittels PCA.
    """

    count, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            binary,
            connectivity=8
        )
    )

    candidates = []

    for label in range(1, count):

        area = stats[label, cv2.CC_STAT_AREA]

        if area < 20:
            continue

        # Alle Pixel des aktuellen Bereichs
        ys, xs = np.where(labels == label)

        points = np.column_stack((xs, ys)).astype(np.float64)

        if len(points) < 2:
            continue

        # PCA / Hauptkomponentenanalyse
        center = np.mean(points, axis=0)
        centered = points - center

        covariance = np.cov(centered.T)

        eigenvalues, eigenvectors = np.linalg.eigh(covariance)

        direction = eigenvectors[:, np.argmax(eigenvalues)]

        # Richtungsvektor normieren
        direction /= np.linalg.norm(direction)

        normal = np.array([-direction[1], direction[0]])

        # Projektion auf die Linienrichtung
        along = centered @ direction

        # Projektion senkrecht zur Linie
        across = centered @ normal

        # Robuste Längenschätzung
        start = np.percentile(along, 1)
        end = np.percentile(along, 99)

        length = end - start

        # Dicke anhand der senkrechten Ausdehnung
        thickness = (
            np.percentile(across, 95)
            - np.percentile(across, 5)
        )

        if length < config.MIN_LINE_LENGTH:
            continue

        if thickness > config.MAX_LINE_THICKNESS:
            continue

        # Winkel in Grad
        angle = np.degrees(
            np.arctan2(direction[1], direction[0])
        ) % 180

        # Endpunkte der Ausgleichsgeraden
        p1 = center + direction * start
        p2 = center + direction * end

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


def select_line_pair(candidates):
    """
    Sucht das am besten passende Linienpaar.

    Kriterien:
    - möglichst parallele Linien
    - möglichst ähnliche Linienlängen
    """

    best_pair = None
    best_score = float("inf")

    for i in range(len(candidates)):

        for j in range(i + 1, len(candidates)):

            line1 = candidates[i]
            line2 = candidates[j]

            angle_diff = angle_difference(
                line1["angle"],
                line2["angle"]
            )

            if angle_diff > config.MAX_ANGLE_DIFFERENCE:
                continue

            # Verhältnis der Linienlängen
            length_ratio = (
                min(line1["length"], line2["length"])
                / max(line1["length"], line2["length"])
            )

            # Bewertungsfunktion
            score = (
                angle_diff
                / config.MAX_ANGLE_DIFFERENCE
                + 0.5 * (1 - length_ratio)
            )

            if score < best_score:
                best_score = score
                best_pair = (line1, line2)

    return best_pair


def calculate_distance(line1, line2):
    """Berechnet den senkrechten Linienabstand."""

    # Gemeinsame mittlere Linienrichtung
    direction = line1["direction"] + line2["direction"]
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

        print("\nErkanntes Linienpaar:")
        print(f"Linie 1 Winkel: {selected_pair[0]['angle']:.2f}°")
        print(f"Linie 2 Winkel: {selected_pair[1]['angle']:.2f}°")
        print(f"Winkeldifferenz: {angle_diff:.2f}°")

        print(f"\nAbstand: {distance_px:.2f} Pixel")
        print(f"Abstand: {distance_mm:.2f} mm")

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
