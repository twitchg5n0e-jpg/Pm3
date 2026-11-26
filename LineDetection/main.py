
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



def print_details(*texts):
    """
    Gibt Detail-Informationen aus (jede Komponente, jedes Paar).

    Im Live-Betrieb stören diese vielen Zeilen und kosten Zeit.
    Mit PRINT_DETAILS = False in config.py werden sie abgeschaltet.
    """

    if config.PRINT_DETAILS:
        print(*texts)



def to_gray(image):
    """
    Wandelt ein Farbbild in ein Helligkeitsbild um.

    Verwendet wird der hellste Farbkanal jedes Pixels. Dadurch ist
    nur dunkel, was in ALLEN Kanälen dunkel ist (= schwarz). Ein grüner
    Hintergrund bleibt hell, weil sein Grünkanal hell ist.
    """

    if image.ndim == 2:
        return image

    # Nur die drei Farbkanäle verwenden (ein Alphakanal wird ignoriert)
    blue, green, red = cv2.split(image[:, :, :3])

    if config.MODE == "WHITE_ON_BLACK":
        return cv2.min(cv2.min(blue, green), red)

    return cv2.max(cv2.max(blue, green), red)



def to_dark_gray(image):
    """
    Helligkeitsbild, in dem die gesuchten Linien dunkel sind
    (bei WHITE_ON_BLACK wird das Bild dafür invertiert).
    """

    gray = to_gray(image)

    if config.MODE == "BLACK_ON_WHITE":
        return gray

    if config.MODE == "WHITE_ON_BLACK":
        # Bild invertieren, danach ist der Ablauf identisch
        return 255 - gray

    raise ValueError("Unbekannter Kontrastmodus")



def clean_binary(binary, image_width):
    """
    Entfernt kleine Störungen aus einem Binärbild und schliesst
    kleine Unterbrechungen.

    image_width ist die Breite des GANZEN Bildes. Damit ist der Filter
    auch für einen kleinen Bildausschnitt gleich gross.
    """

    # Filtergrösse passend zur Bildgrösse (ungerade, mindestens 3)
    size = int(round(image_width * config.MORPH_KERNEL_RATIO))
    size = max(3, size | 1)

    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (size, size)
    )

    # Kleine Störungen entfernen
    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        kernel
    )

    # Kleine Unterbrechungen schliessen
    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        kernel
    )

    return binary



def preprocess(image, threshold_factor=None):
    """
    Erzeugt ein Binärbild mit schwarzen Objekten als weisse Pixel.

    threshold_factor: Schwelle relativ zur Bildhelligkeit. Ohne Angabe
    wird der erste (strengste) Wert aus config.THRESHOLD_FACTORS benutzt.
    """

    if threshold_factor is None:
        threshold_factor = config.THRESHOLD_FACTORS[0]

    gray = to_dark_gray(image)

    # Schwelle relativ zur mittleren Helligkeit des Bildes
    # (jedes 8. Pixel reicht für den Median und spart Rechenzeit)
    median = float(np.median(gray[::8, ::8]))
    threshold = threshold_factor * median

    print_details(f"Median-Helligkeit: {median:.0f}, Schwelle: {threshold:.0f}")

    # Thresholding
    _, binary = cv2.threshold(
        gray,
        threshold,
        255,
        cv2.THRESH_BINARY_INV
    )

    return clean_binary(binary, image.shape[1])



def fit_line(mask, offset_x, offset_y):
    """
    Passt mit PCA eine Gerade an die Pixel einer Komponente an.

    mask ist nur der kleine Bildausschnitt (Bounding Box) der
    Komponente, offset_x / offset_y ist dessen linke obere Ecke
    im ganzen Bild.
    """

    ys, xs = np.nonzero(mask)

    if len(xs) < 10:
        return None

    points = np.column_stack(
        (xs + offset_x, ys + offset_y)
    ).astype(np.float64)

    area = len(points)

    # Mittelpunkt (Flächenschwerpunkt)
    center = np.mean(points, axis=0)

    centered = points - center

    # PCA
    covariance = np.cov(
        centered,
        rowvar=False
    )

    eigenvalues, eigenvectors = np.linalg.eigh(
        covariance
    )

    direction = eigenvectors[:, -1]

    if direction[0] < 0:
        direction = -direction

    direction /= np.linalg.norm(direction)

    normal = np.array([
        -direction[1],
        direction[0]
    ])

    # Projektionen
    longitudinal = centered @ direction
    transverse = centered @ normal

    start = np.percentile(longitudinal, 1)
    end = np.percentile(longitudinal, 99)

    length = end - start

    thickness = (
        np.percentile(transverse, 95)
        - np.percentile(transverse, 5)
    )

    thickness = max(thickness, 1.0)

    angle = np.degrees(
        np.arctan2(direction[1], direction[0])
    ) % 180

    elongation = length / thickness

    # Geradheit: mittlere Strichdicke (Fläche / Länge) im Verhältnis
    # zur Breite quer zur Geraden. Ein gerader Balken ergibt ca. 1,
    # ein Kreuz oder ein Bogen deutlich weniger.
    straightness = min(
        1.0,
        area / max(length, 1.0) / thickness
    )

    p1 = center + direction * start
    p2 = center + direction * end

    # Bounding Box der Pixel im ganzen Bild (links, oben, rechts, unten)
    box = (
        int(xs.min()) + offset_x,
        int(ys.min()) + offset_y,
        int(xs.max()) + offset_x,
        int(ys.max()) + offset_y
    )

    return {
        "center": center,
        "direction": direction,
        "normal": normal,
        "angle": angle,
        "length": length,
        "thickness": thickness,
        "area": area,
        "elongation": elongation,
        "straightness": straightness,
        "p1": p1,
        "p2": p2,
        "box": box
    }



def remove_thin_parts(mask, offset_x, offset_y, max_size):
    """
    Für Komponenten, die keine saubere Linie sind (z.B. eine dünnere
    Linie kreuzt eine dicke Linie, oder ein dünner Strich verbindet
    beide gesuchten Linien): Entfernt schrittweise immer dickere
    Anhängsel (Opening mit wachsendem Filter), bis das grösste übrig
    bleibende Stück eine gerade Linie ist.

    max_size begrenzt den Filter, damit grosse unförmige Flächen
    (z.B. ein dunkler Bildrand) nicht minutenlang rechnen.

    Rückgabe: Liste aller geraden Stücke (dicts). Die Liste ist leer,
    falls nichts Gerades übrig bleibt.
    """

    size = 3

    while size <= min(max_size, min(mask.shape)):

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (size, size)
        )

        core = cv2.morphologyEx(
            mask,
            cv2.MORPH_OPEN,
            kernel
        )

        number_labels, labels, stats, _ = (
            cv2.connectedComponentsWithStats(
                core,
                connectivity=8
            )
        )

        # Nichts mehr übrig
        if number_labels < 2:
            return []

        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])

        line = fit_line(labels == largest, offset_x, offset_y)

        if line is None:
            return []

        if line["straightness"] >= config.MIN_STRAIGHTNESS:

            lines = [line]

            # Auch die anderen Stücke prüfen
            # (z.B. die zweite gesuchte Linie)
            for label in range(1, number_labels):

                if label == largest:
                    continue

                other = fit_line(labels == label, offset_x, offset_y)

                if other is None:
                    continue

                if other["straightness"] >= config.MIN_STRAIGHTNESS:
                    lines.append(other)

            return lines

        size += 2

    return []



def detect_lines(binary, core=None):
    """
    Sucht längliche, gerade Flächen im Binärbild.

    core ist das Binärbild der strengsten Schwelle (oder None). Damit
    wird bei einer gelockerten Schwelle geprüft, ob eine Fläche einen
    wirklich schwarzen Kern hat. Schatten und dunkle Flecken haben
    keinen und werden so aussortiert.
    """

    # Zusammenhängende Flächen suchen (8er-Nachbarschaft).
    # Das Verfahren CCL_GRANA liefert genau dieselben Flächen wie
    # die Standardeinstellung, braucht mit einem einzelnen
    # Prozessorkern aber nur etwa ein Drittel der Zeit.
    number_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStatsWithAlgorithm(
            binary,
            8,
            cv2.CV_32S,
            cv2.CCL_GRANA
        )
    )

    height, width = binary.shape

    # Grenzwerte in Pixel für diese Bildgrösse
    min_area = config.MIN_COMPONENT_AREA_RATIO * height * width
    min_length = config.MIN_LINE_LENGTH_RATIO * np.hypot(height, width)
    max_area = config.MAX_COMPONENT_AREA_RATIO * height * width
    max_box_area = config.MAX_COMPONENT_BOX_RATIO * height * width
    max_thin_size = max(3, int(config.MAX_THIN_PART_RATIO * width))

    candidates = []

    print_details("\nGefundene Komponenten:", number_labels - 1)

    for label in range(1, number_labels):

        x, y, w, h, area = stats[label]

        # Schnelle Vorauswahl nur mit den Statistiken
        if area < min_area:
            continue

        if np.hypot(w, h) < min_length:
            continue

        # Sehr grosse Flächen sind keine Markierung
        if area > max_area:
            continue

        if w * h > max_box_area:
            continue

        # Nur den Ausschnitt der Komponente betrachten
        # (nicht das ganze Bild -> viel schneller)
        mask = (
            labels[y:y + h, x:x + w] == label
        ).astype(np.uint8)

        line = fit_line(mask, x, y)

        if line is None:
            continue

        # Anteil der wirklich schwarzen Pixel in dieser Fläche
        if core is not None:

            core_part = core[y:y + h, x:x + w]

            core_pixels = cv2.countNonZero(
                cv2.bitwise_and(core_part, core_part, mask=mask)
            )

            if core_pixels < config.MIN_CORE_RATIO * area:
                continue

        # Keine saubere Linie: evtl. hängt eine dünnere Linie daran
        # oder mehrere Linien sind miteinander verbunden
        if line["straightness"] < config.MIN_STRAIGHTNESS:
            lines = remove_thin_parts(mask, x, y, max_thin_size)

        else:
            lines = [line]

        for line in lines:

            print_details(
                f"Komponente {label}: "
                f"Fläche={line['area']}, "
                f"Länge={line['length']:.1f}px, "
                f"Breite={line['thickness']:.1f}px, "
                f"Winkel={line['angle']:.2f}°, "
                f"Streckung={line['elongation']:.2f}, "
                f"Geradheit={line['straightness']:.2f}"
            )

            if line["length"] < min_length:
                continue

            if line["elongation"] < config.MIN_ELONGATION:
                continue

            if line["straightness"] < config.MIN_STRAIGHTNESS:
                continue

            # Linien am Bildrand sind abgeschnitten (oder Spannbacken,
            # dunkler Bildrand) und würden einen falschen Abstand liefern
            left, top, right, bottom = line["box"]

            if config.IGNORE_BORDER_COMPONENTS and (
                left == 0 or top == 0
                or right == width - 1 or bottom == height - 1
            ):
                continue

            candidates.append(line)

    print_details(
        "\nGültige Flächenkandidaten:",
        len(candidates)
    )

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



def relative_difference(value1, value2):
    """Relativer Unterschied zweier positiver Werte (0 = gleich)."""

    return 1.0 - min(value1, value2) / max(value1, value2)



def select_line_pair(candidates):
    """
    Sucht das am besten passende Linienpaar.

    Kriterien:
    1. Parallelität
    2. Ähnliche Linienlänge
    3. Ähnliche Liniendicke
    4. Überlappung in Linienrichtung

    Der Abstand zwischen den Linien wird nicht bewertet.
    """

    best_pair = None
    best_score = float("inf")

    # Alle gültigen Paare: (Bewertung, Strichdicke, Linie 1, Linie 2)
    valid_pairs = []

    # Viel kleinere Flächen als die grösste Linie sind keine Markierung
    # (z.B. kleine dunkle Flecken oder Schattenstücke)
    if candidates:

        largest_area = max(line["area"] for line in candidates)

        candidates = [
            line for line in candidates
            if line["area"] >= config.MIN_RELATIVE_AREA * largest_area
        ]

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
            length_difference = relative_difference(
                line1["length"],
                line2["length"]
            )

            if length_difference > config.MAX_LENGTH_DIFFERENCE:
                continue

            length_score = (
                length_difference / config.MAX_LENGTH_DIFFERENCE
            )

            # 3. Ähnliche Liniendicke
            thickness_difference = relative_difference(
                line1["thickness"],
                line2["thickness"]
            )

            if thickness_difference > config.MAX_THICKNESS_DIFFERENCE:
                continue

            thickness_score = (
                thickness_difference / config.MAX_THICKNESS_DIFFERENCE
            )

            # 4. Überlappung
            overlap_ratio = calculate_overlap_ratio(
                line1, line2
            )

            if overlap_ratio < config.MIN_OVERLAP_RATIO:
                continue

            overlap_score = 1.0 - overlap_ratio

            # 5. Gesamtbewertung
            score = (
                config.ANGLE_WEIGHT * angle_score
                + config.LENGTH_WEIGHT * length_score
                + config.THICKNESS_WEIGHT * thickness_score
                + config.OVERLAP_WEIGHT * overlap_score
            )

            print_details(
                f"Paar {i+1}/{j+1}: "
                f"Winkeldifferenz={angle_diff:.2f}°, "
                f"Bewertung={score:.3f}"
            )

            # Schlecht passende Paare verwerfen: lieber kein Resultat
            # als ein falscher Abstand
            if score > config.MAX_PAIR_SCORE:
                continue

            # Strichdicke des Paars = mittlere Dicke (Fläche / Länge)
            # der dünneren der beiden Linien
            stroke = min(
                line1["area"] / max(line1["length"], 1.0),
                line2["area"] / max(line2["length"], 1.0)
            )

            valid_pairs.append((score, stroke, line1, line2))

    if not valid_pairs:
        return None

    # Die gesuchten Linien sind dicker als die Störlinien:
    # dünnere Paare erhalten einen Zuschlag auf die Bewertung.
    max_stroke = max(pair[1] for pair in valid_pairs)

    for score, stroke, line1, line2 in valid_pairs:

        score += config.THIN_PAIR_WEIGHT * (1.0 - stroke / max_stroke)

        if score < best_score:

            best_score = score
            best_pair = (line1, line2)

    return best_pair



def fit_edge(positions, edge, tolerance):
    """
    Passt eine Gerade an die Kantenpunkte einer Bandkante an.

    Ausreisser (z.B. Spalten neben der Probe oder Glanzstellen) werden
    in mehreren Durchgängen aussortiert.

    Rückgabe: (Steigung, Achsenabschnitt, brauchbare Spalten)
    """

    good = np.isfinite(edge)

    slope = 0.0
    offset = 0.0

    for _ in range(4):

        if np.count_nonzero(good) < 5:
            break

        slope, offset = np.polyfit(positions[good], edge[good], 1)

        residual = edge - (slope * positions + offset)

        good = np.isfinite(edge) & (np.abs(residual) < tolerance)

    return slope, offset, good



def refine_line(image, line):
    """
    Misst eine gefundene Markierung im Originalbild genauer nach.

    Die Fläche aus dem Binärbild hängt von der globalen Schwelle ab
    und enthält auch die Teile des Bands, die um die Probenkante
    herum laufen. Hier wird deshalb ein kleiner Ausschnitt um das
    Band so gedreht, dass das Band waagrecht liegt. In jeder Spalte
    wird die Ober- und Unterkante gesucht (Halbwert zwischen Band und
    heller Umgebung, auf Bruchteile eines Pixels genau). Durch beide
    Kanten wird je eine Gerade gelegt. Die Mittelachse des Bands ist
    die Mitte zwischen diesen beiden Geraden.

    Rückgabe: die verbesserte Linie, oder die unveränderte Linie,
    falls die Nachmessung nicht verlässlich ist.
    """

    direction = line["direction"]
    normal = line["normal"]
    thickness = line["thickness"]

    # Grösse des Ausschnitts: etwas länger als das Band und auf
    # beiden Seiten etwa eine halbe Banddicke helle Umgebung
    middle = (line["p1"] + line["p2"]) / 2

    half_width = int(
        line["length"] * (0.5 + config.REFINE_END_MARGIN)
    )
    half_height = int(thickness) + 2

    width = 2 * half_width + 1
    height = 2 * half_height + 1

    # Abbildung Ausschnitt -> Bild: Spalten laufen entlang des Bands,
    # Zeilen quer dazu. Die alte Mittelachse liegt in der mittleren Zeile.
    corner = middle - half_width * direction - half_height * normal

    matrix = np.float64([
        [direction[0], normal[0], corner[0]],
        [direction[1], normal[1], corner[1]]
    ])

    patch = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE
    )

    patch = to_gray(patch).astype(np.float32)

    if config.MODE == "WHITE_ON_BLACK":
        patch = 255 - patch

    # Entlang des Bands glätten: dämpft Rauschen und Glanzpunkte,
    # ohne die Kanten quer zum Band zu verwischen
    smooth = max(3, int(thickness * config.REFINE_SMOOTH_RATIO) | 1)

    patch = cv2.blur(patch, (smooth, 1))

    # Nur der mittlere Teil der Länge liegt sicher auf der Probe
    first = int(width * config.REFINE_END_MARGIN * 2)
    inner = patch[:, first:width - first]

    # Helligkeit des Bands (mittlere Zeilen) und der Umgebung
    # (äusserste Zeilen oben / unten), je ein Viertel der Banddicke
    core_rows = max(1, int(thickness * 0.25))
    strip_rows = max(2, int(thickness * 0.25))

    band_level = np.median(
        inner[half_height - core_rows:half_height + core_rows + 1]
    )
    level_above = np.median(inner[:strip_rows])
    level_below = np.median(inner[height - strip_rows:])

    # Zu wenig Kontrast: Nachmessung nicht möglich
    darkest_surrounding = min(level_above, level_below)

    if band_level > config.REFINE_MAX_BAND_LEVEL * darkest_surrounding:
        return line

    # Kanten in jeder Spalte suchen: von aussen (hell) nach innen
    # bis zum ersten Pixel, das dunkler ist als der Halbwert
    positions = np.arange(width, dtype=np.float64)
    columns = np.arange(width)

    edges = []

    for part, sample_level in (
        (patch[:half_height + 1], level_above),
        (patch[::-1][:half_height + 1], level_below)
    ):

        threshold = (band_level + sample_level) / 2

        dark = part < threshold

        row = np.argmax(dark, axis=0)

        # Unbrauchbar: gar kein dunkles Pixel oder schon am Rand dunkel
        usable = dark.any(axis=0) & (row > 0)

        row = np.maximum(row, 1)

        outside = part[row - 1, columns]
        inside = part[row, columns]

        # Genaue Lage des Halbwerts zwischen den beiden Pixeln
        edge = row - 1 + (outside - threshold) / np.maximum(
            outside - inside,
            1e-6
        )

        edge[~usable] = np.nan

        edges.append(edge)

    # Zeilen von oben gezählt (die untere Kante wurde von unten gesucht)
    top = edges[0]
    bottom = height - 1 - edges[1]

    # Geraden durch beide Kanten, Ausreisser weglassen
    tolerance = max(1.0, thickness * config.REFINE_EDGE_TOLERANCE)

    top_slope, top_offset, top_good = fit_edge(
        positions, top, tolerance
    )

    bottom_slope, bottom_offset, bottom_good = fit_edge(
        positions, bottom, tolerance
    )

    # Spalten, in denen beide Kanten zur Geraden passen
    good = np.nonzero(top_good & bottom_good)[0]

    # Verlässlich nur, wenn die Kanten über den grössten Teil der
    # Länge gerade sind (z.B. nicht bei einer Zickzack-Linie)
    if len(good) < config.REFINE_MIN_GOOD_RATIO * line["length"]:
        return line

    # Mittelachse = Mitte zwischen den beiden Kantengeraden
    slope = (top_slope + bottom_slope) / 2
    offset = (top_offset + bottom_offset) / 2

    start = float(good[0])
    end = float(good[-1])
    center_position = (start + end) / 2

    new_thickness = (
        (bottom_slope - top_slope) * center_position
        + bottom_offset - top_offset
    )

    # Verschiebung der Mitte quer zur alten Achse
    shift = slope * center_position + offset - half_height

    # Plausibilität: Die Nachmessung darf die Linie nur wenig verändern
    if abs(shift) > config.REFINE_MAX_SHIFT_RATIO * thickness:
        return line

    if abs(np.degrees(np.arctan(slope))) > config.MAX_ANGLE_DIFFERENCE:
        return line

    if new_thickness < 0.5 * thickness or new_thickness > 2.0 * thickness:
        return line

    # Zurück ins Bild rechnen
    def to_image(position):

        row = slope * position + offset

        return corner + position * direction + row * normal

    p1 = to_image(start)
    p2 = to_image(end)

    new_direction = (p2 - p1) / np.linalg.norm(p2 - p1)

    refined = dict(line)

    refined["center"] = to_image(center_position)
    refined["direction"] = new_direction
    refined["normal"] = np.array([-new_direction[1], new_direction[0]])
    refined["angle"] = np.degrees(
        np.arctan2(new_direction[1], new_direction[0])
    ) % 180
    refined["length"] = float(np.linalg.norm(p2 - p1))
    refined["thickness"] = float(new_thickness)
    refined["p1"] = p1
    refined["p2"] = p2

    return refined



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




def draw_results(image, selected_pair, distance_px=None):
    """
    Zeichnet das Linienpaar ins Bild.

    Mit distance_px wird zusätzlich die Messstrecke (senkrecht zu den
    Linien) und der Abstand in Pixel eingezeichnet.
    """

    if image.ndim == 2:
        result = cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2BGR
        )
    else:
        result = image.copy()

    # Strichstärke und Schrift passend zur Bildgrösse
    scale = max(1, image.shape[1] // 600)

    if selected_pair is None:
        cv2.putText(
            result,
            "Kein Linienpaar erkannt",
            (30 * scale, 50 * scale),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            (0, 0, 255),
            2 * scale
        )

        return result

    colors = [
        (0, 255, 0),
        (255, 0, 0)
    ]

    for line, color in zip(selected_pair, colors):

        p1 = tuple(
            int(v) for v in np.round(line["p1"])
        )

        p2 = tuple(
            int(v) for v in np.round(line["p2"])
        )

        cv2.line(
            result,
            p1,
            p2,
            color,
            2 * scale
        )

        center = tuple(
            int(v) for v in np.round(line["center"])
        )

        cv2.circle(
            result,
            center,
            4 * scale,
            (0, 0, 255),
            -1
        )

    if distance_px is None:
        return result

    # Messstrecke: vom Mittelpunkt der ersten Linie senkrecht
    # (wie in calculate_distance) bis auf die Höhe der zweiten Linie
    line1, line2 = selected_pair

    direction1 = line1["direction"]
    direction2 = line2["direction"]

    if np.dot(direction1, direction2) < 0:
        direction2 = -direction2

    direction = direction1 + direction2
    direction /= np.linalg.norm(direction)

    normal = np.array([-direction[1], direction[0]])

    start = line1["center"]
    end = start + normal * np.dot(line2["center"] - start, normal)

    cv2.line(
        result,
        tuple(int(v) for v in np.round(start)),
        tuple(int(v) for v in np.round(end)),
        (0, 255, 255),
        scale
    )

    # Abstand als Text neben die Mitte der Messstrecke schreiben
    text = f"{distance_px:.1f} px"

    (text_width, text_height), _ = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        2 * scale
    )

    middle = (start + end) / 2

    text_x = int(middle[0]) + 12 * scale
    text_y = int(middle[1]) + text_height // 2

    # Kein Platz rechts: Text links von der Messstrecke
    if text_x + text_width > result.shape[1]:
        text_x = int(middle[0]) - 12 * scale - text_width

    text_x = max(0, text_x)
    text_y = min(max(text_height, text_y), result.shape[0] - 1)

    # Zuerst dick in Schwarz, dann in Gelb: auf jedem Hintergrund lesbar
    text_styles = [
        ((0, 0, 0), 6 * scale),
        ((0, 255, 255), 2 * scale)
    ]

    for color, thickness in text_styles:

        cv2.putText(
            result,
            text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness
        )

    return result



def find_pair(image, threshold_factor, cache):
    """
    Sucht mit EINER Schwelle nach dem Linienpaar.

    cache merkt sich die Resultate pro Schwelle, damit keine Schwelle
    zweimal gerechnet wird.

    Rückgabe: Linienpaar oder None
    """

    if threshold_factor in cache["pairs"]:
        return cache["pairs"][threshold_factor]

    strictest_factor = config.THRESHOLD_FACTORS[0]

    binary = preprocess(image, threshold_factor)

    # Bei gelockerter Schwelle wird der schwarze Kern geprüft
    if threshold_factor > strictest_factor:
        candidates = detect_lines(binary, cache["core"])

    else:
        candidates = detect_lines(binary)

    print_details(f"\nGefundene Linienkandidaten: {len(candidates)}")

    pair = select_line_pair(candidates)

    # Binärbild der strengsten Schwelle merken
    if threshold_factor == strictest_factor:
        cache["core"] = binary

    cache["pairs"][threshold_factor] = pair

    return pair



def is_same_pair(pair1, pair2):
    """
    Prüft, ob zwei Linienpaare dieselben Markierungen zeigen:
    gleicher Abstand und beide Linien an derselben Stelle.
    """

    distance1, _ = calculate_distance(pair1[0], pair1[1])
    distance2, _ = calculate_distance(pair2[0], pair2[1])

    allowed = config.CONFIRM_TOLERANCE * max(distance1, distance2)

    if abs(distance1 - distance2) > allowed:
        return False

    for line in pair1:

        # Abstand zur nächstgelegenen Linie des anderen Paars
        nearest = min(
            np.linalg.norm(line["center"] - other["center"])
            for other in pair2
        )

        if nearest > 0.5 * line["length"]:
            return False

    return True



def process_image(image):
    """
    Führt die ganze Auswertung für ein Bild durch.

    Rückgabe: (Linienpaar oder None, Abstand in Pixel oder None)

    Die Suche arbeitet mit Backtracking: Zuerst wird mit der strengsten
    Schwelle gesucht. Ein gefundenes Paar gilt erst, wenn dasselbe Paar
    auch mit einer leicht lockereren oder strengeren Schwelle gefunden
    wird. Echte Markierungen bleiben dabei an ihrem Platz, zufällig
    passende Schatten oder Flecken nicht. Ein nicht bestätigtes Paar
    wird verworfen und die Suche geht mit der nächsten Schwelle weiter.
    """

    selected_pair = None

    cache = {
        "pairs": {},
        "core": None
    }

    for threshold_factor in config.THRESHOLD_FACTORS:

        pair = find_pair(image, threshold_factor, cache)

        if pair is None:
            continue

        # Ohne Kontrolle (schneller): das erste Paar gilt
        if config.CONFIRM_STEP <= 0:
            selected_pair = pair
            break

        # Kontrolle: zuerst lockerer, dann strenger
        steps = [config.CONFIRM_STEP, -config.CONFIRM_STEP]

        # Danach dasselbe mit dem kleinen Schritt. Das hilft bei einer
        # glänzenden (nur dunkelgrauen) Markierung: Mit dem grossen
        # Schritt ist sie strenger noch nicht zu sehen und lockerer
        # schon mit dem Schatten der Probenkante verbunden.
        if config.CONFIRM_SMALL_STEP > 0:
            steps += [config.CONFIRM_SMALL_STEP, -config.CONFIRM_SMALL_STEP]

        for step in steps:

            check_factor = round(threshold_factor + step, 2)

            check_pair = find_pair(image, check_factor, cache)

            if check_pair is not None and is_same_pair(pair, check_pair):
                selected_pair = pair
                break

        if selected_pair is not None:
            break

        print_details("Paar nicht bestätigt, suche weiter.")

    if selected_pair is None:
        return None, None

    # Schwelle (Grauwert) merken, mit der das Paar gefunden wurde.
    # Die Verfolgung in den nächsten Bildern benutzt dieselbe Schwelle.
    median = float(np.median(to_dark_gray(image[::8, ::8])))

    for line in selected_pair:
        line["threshold"] = threshold_factor * median
        line["median"] = median
        line["coarse_length"] = line["length"]

    # Beide Markierungen im Originalbild genauer nachmessen
    selected_pair = [refine_line(image, line) for line in selected_pair]

    distance_px, distance_mm = calculate_distance(
        selected_pair[0],
        selected_pair[1]
    )

    return selected_pair, distance_px



def track_line(image, line, brightness, search_ratio):
    """
    Sucht eine Linie aus dem vorherigen Bild im neuen Bild wieder.

    Es wird nur ein kleines Suchfenster um die letzte Position
    betrachtet (nicht das ganze Bild). Das ist viel schneller und
    andere dunkle Objekte im Bild können nicht verwechselt werden.

    brightness: Helligkeit des Bildes im Verhältnis zum Bild, in dem
    das Paar gefunden wurde.
    search_ratio: Zugabe des Suchfensters (Anteil der Linienlänge).

    Rückgabe: die Linie im neuen Bild oder None (Linie verloren).
    """

    height, width = image.shape[:2]

    # Suchfenster: Rechteck um die Fläche der Linie im letzten Bild
    # plus Zugabe auf allen Seiten
    box_left, box_top, box_right, box_bottom = line["box"]

    margin = search_ratio * max(
        box_right - box_left,
        box_bottom - box_top
    )

    left = max(0, int(box_left - margin))
    top = max(0, int(box_top - margin))
    right = min(width, int(box_right + margin) + 1)
    bottom = min(height, int(box_bottom + margin) + 1)

    # Fenster liegt ausserhalb des Bildes (z.B. andere Bildgrösse)
    if right - left < 3 or bottom - top < 3:
        return None

    gray = to_dark_gray(image[top:bottom, left:right])

    # Gleiche Schwelle wie beim Finden des Paars, angepasst an die
    # aktuelle Bildhelligkeit (Belichtung, Lampe, Wolke)
    _, binary = cv2.threshold(
        gray,
        line["threshold"] * brightness,
        255,
        cv2.THRESH_BINARY_INV
    )

    binary = clean_binary(binary, width)

    # Lücken im Band schliessen (z.B. Glanzstellen), damit das Band
    # nicht in Bruchstücke zerfällt. Geschlossen wird nur ENTLANG des
    # Bands (strichförmiger Filter in Bandrichtung), damit das Band
    # nicht mit Flächen darüber oder darunter verschmilzt.
    close_size = int(config.TRACK_CLOSE_RATIO * line["thickness"]) | 1

    if close_size >= 3:

        kernel = np.zeros((close_size, close_size), dtype=np.uint8)

        middle = np.array([close_size // 2, close_size // 2])
        reach = line["direction"] * (close_size // 2)

        cv2.line(
            kernel,
            tuple(int(v) for v in np.round(middle - reach)),
            tuple(int(v) for v in np.round(middle + reach)),
            1,
            1
        )

        binary = cv2.morphologyEx(
            binary,
            cv2.MORPH_CLOSE,
            kernel
        )

    number_labels, labels, stats, centroids = (
        cv2.connectedComponentsWithStats(
            binary,
            connectivity=8
        )
    )

    max_thin_size = max(3, int(config.MAX_THIN_PART_RATIO * width))

    best_line = None
    best_distance = float("inf")

    for label in range(1, number_labels):

        x, y, w, h, area = stats[label]

        # Viel kleinere Flächen sind nicht die gesuchte Linie
        if area < (1.0 - config.TRACK_MAX_CHANGE) * 0.5 * line["area"]:
            continue

        mask = (
            labels[y:y + h, x:x + w] == label
        ).astype(np.uint8)

        new_line = fit_line(mask, left + x, top + y)

        if new_line is None:
            continue

        # Keine saubere Linie: dünnere Anhängsel abtrennen
        if new_line["straightness"] < config.MIN_STRAIGHTNESS:
            pieces = remove_thin_parts(mask, left + x, top + y, max_thin_size)

        else:
            pieces = [new_line]

        for piece in pieces:

            # Reicht die Fläche bis an den Rand des Suchfensters?
            # (wird nach der Nachmessung geprüft)
            box_left, box_top, box_right, box_bottom = piece["box"]

            piece["at_window_border"] = (
                box_left <= left or box_top <= top
                or box_right >= right - 1 or box_bottom >= bottom - 1
            )

            # Die Fläche, die der letzten Position am nächsten liegt
            distance = np.linalg.norm(piece["center"] - line["center"])

            if distance < best_distance:

                best_distance = distance
                best_line = piece

    if best_line is None:
        return None

    best_line["threshold"] = line["threshold"]
    best_line["median"] = line["median"]
    best_line["coarse_length"] = best_line["length"]

    # Im Originalbild genauer nachmessen
    coarse_line = best_line
    best_line = refine_line(image, coarse_line)

    # Die Fläche reicht bis an den Rand des Suchfensters, z.B. weil ein
    # Schatten an der Probenkante am Band hängt. Das Resultat gilt nur,
    # wenn die Nachmessung gelungen ist und das nachgemessene Band
    # vollständig im Suchfenster liegt.
    if coarse_line["at_window_border"]:

        # Nachmessung nicht gelungen (Linie unverändert)
        if best_line is coarse_line:
            return None

        border = 0.5 * best_line["thickness"]

        for point in (best_line["p1"], best_line["p2"]):

            if (
                point[0] < left + border or point[1] < top + border
                or point[0] > right - 1 - border
                or point[1] > bottom - 1 - border
            ):
                return None

    # Plausibilität: Die Linie darf sich von Bild zu Bild
    # nur wenig verändern. Die Länge wird an der Fläche verglichen
    # (die nachgemessene Länge schwankt bei glänzenden Bändern).
    length_change = relative_difference(
        best_line["coarse_length"],
        line["coarse_length"]
    )

    thickness_change = relative_difference(
        best_line["thickness"],
        line["thickness"]
    )

    angle_change = angle_difference(
        best_line["angle"],
        line["angle"]
    )

    if length_change > config.TRACK_MAX_CHANGE:
        return None

    if thickness_change > config.TRACK_MAX_CHANGE:
        return None

    if angle_change > config.MAX_ANGLE_DIFFERENCE:
        return None

    return best_line



def track_pair(image, previous_pair):
    """
    Verfolgt beide Linien vom vorherigen ins neue Bild.

    Rückgabe: neues Linienpaar oder None, falls eine Linie verloren ist.
    """

    new_pair = []

    # Helligkeit des Bildes im Vergleich zum Bild, in dem das Paar
    # gefunden wurde
    brightness = 1.0

    if previous_pair[0]["median"] > 0:
        median = float(np.median(to_dark_gray(image[::8, ::8])))
        brightness = median / previous_pair[0]["median"]

    for line in previous_pair:

        new_line = None

        # Zuerst im kleinen Fenster suchen. Ist die Linie dort nicht
        # (z.B. Kamera angestossen), wird das Fenster vergrössert.
        for search_ratio in config.TRACK_SEARCH_RATIOS:

            new_line = track_line(image, line, brightness, search_ratio)

            if new_line is not None:
                break

        if new_line is None:
            return None

        new_pair.append(new_line)

    return new_pair



def is_similar_pair(old_pair, new_pair):
    """
    Prüft nach einer Suche im ganzen Bild, ob das gefundene Paar zu
    den vorher verfolgten Markierungen passt: fast gleicher Abstand
    und gleich dicke Bänder.
    """

    old_distance, _ = calculate_distance(old_pair[0], old_pair[1])
    new_distance, _ = calculate_distance(new_pair[0], new_pair[1])

    distance_change = relative_difference(old_distance, new_distance)

    if distance_change > config.TRACK_RELOCK_DISTANCE_CHANGE:
        return False

    # Beide Paare gleich ordnen (entlang der Senkrechten zu den Linien)
    def sort_pair(pair):

        normal = pair[0]["normal"]

        return sorted(
            pair,
            key=lambda line: float(np.dot(line["center"], normal))
        )

    for old_line, new_line in zip(sort_pair(old_pair), sort_pair(new_pair)):

        thickness_change = relative_difference(
            old_line["thickness"],
            new_line["thickness"]
        )

        if thickness_change > config.TRACK_MAX_CHANGE:
            return False

    return True



def create_tracker():
    """
    Erzeugt den Zustand für die Auswertung einer Bildfolge
    (z.B. Live-Bilder der Kamera) mit process_frame().

    status:
    "suche"     es wurde noch kein Linienpaar gefunden
    "gefunden"  Paar gefunden, wartet auf Bestätigung (confirm_tracker)
    "verfolgt"  bestätigtes Paar wird von Bild zu Bild verfolgt
    "verloren"  Paar in diesem Bild nicht wiedergefunden
    """

    return {
        "pair": None,
        "confirmed": False,
        "lost_frames": 0,
        "status": "suche"
    }



def confirm_tracker(tracker):
    """
    Bestätigt das zuletzt gefundene Linienpaar (z.B. nachdem der
    Benutzer es auf dem Bildschirm kontrolliert hat). Ab jetzt wird
    nicht mehr im ganzen Bild gesucht, sondern nur noch verfolgt.

    Rückgabe: True, wenn ein Paar zum Bestätigen vorhanden war.
    """

    if tracker["pair"] is None:
        return False

    tracker["confirmed"] = True

    return True



def reset_tracker(tracker):
    """
    Setzt die Verfolgung zurück. Danach wird wieder im ganzen Bild
    gesucht.
    """

    tracker["pair"] = None
    tracker["confirmed"] = False
    tracker["lost_frames"] = 0
    tracker["status"] = "suche"



def process_frame(image, tracker):
    """
    Wertet ein Bild einer Bildfolge aus.

    1. Solange kein Paar bestätigt ist, wird in jedem Bild im ganzen
       Bild gesucht (process_image).
    2. Nach der Bestätigung (confirm_tracker) wird das Paar nur noch
       von Bild zu Bild verfolgt.
    3. Wird das Paar nicht wiedergefunden, gibt es für dieses Bild
       kein Resultat. Bleibt es länger verloren, wird zusätzlich im
       ganzen Bild nach den bestätigten Markierungen gesucht.
       Ein anderes Paar wird dabei nie übernommen; dafür muss das
       Programm reset_tracker() aufrufen und neu bestätigen.

    Rückgabe: (Linienpaar oder None, Abstand in Pixel oder None)
    Der Zustand steht danach in tracker["status"].
    """

    # Bestätigtes Paar verfolgen
    if tracker["confirmed"]:

        pair = track_pair(image, tracker["pair"])

        if pair is not None:

            distance_px, distance_mm = calculate_distance(
                pair[0],
                pair[1]
            )

            # Plausibilität: Der Abstand springt nicht von Bild zu Bild
            # (z.B. Sprung auf ein anderes dunkles Objekt)
            last_distance, _ = calculate_distance(
                tracker["pair"][0],
                tracker["pair"][1]
            )

            if abs(distance_px - last_distance) > (
                config.TRACK_MAX_DISTANCE_CHANGE * last_distance
            ):
                pair = None

        if pair is not None:

            tracker["pair"] = pair
            tracker["lost_frames"] = 0
            tracker["status"] = "verfolgt"

            return pair, distance_px

        tracker["lost_frames"] += 1
        tracker["status"] = "verloren"

        # Länger verloren: zusätzlich im ganzen Bild suchen. Das dort
        # gefundene Paar gilt nur, wenn es zu den bestätigten
        # Markierungen passt (gleiche Banddicke, fast gleicher
        # Abstand). Ein anderes Paar wird NICHT übernommen.
        if tracker["lost_frames"] > config.TRACK_MAX_LOST_FRAMES:

            pair, distance_px = process_image(image)

            if pair is not None and is_similar_pair(tracker["pair"], pair):

                tracker["pair"] = pair
                tracker["lost_frames"] = 0
                tracker["status"] = "verfolgt"

                return pair, distance_px

        return None, None

    # Noch nichts bestätigt: Suche im ganzen Bild
    pair, distance_px = process_image(image)

    tracker["pair"] = pair

    if pair is None:
        tracker["status"] = "suche"

        return None, None

    tracker["status"] = "gefunden"

    # Ohne Bestätigung von aussen direkt verfolgen
    if config.TRACK_AUTO_CONFIRM:
        tracker["confirmed"] = True

    return pair, distance_px



def show_images(images):
    """Zeigt Bilder an (falls ein Bildschirm vorhanden ist)."""

    # Verfügbare Bildschirmgrösse (Rückfall: Full HD)
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        root.destroy()

    except Exception:
        screen_w, screen_h = 1920, 1080

    try:
        for title, image in images.items():

            height, width = image.shape[:2]

            # Fenster möglichst gross: 90 % des Bildschirms ausnutzen
            # (kleine Bilder werden dafür auch vergrössert)
            factor = min(
                0.9 * screen_w / width,
                0.9 * screen_h / height
            )

            # Fenster lässt sich zusätzlich mit der Maus skalieren
            cv2.namedWindow(
                title,
                cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO
            )
            cv2.resizeWindow(
                title,
                int(width * factor),
                int(height * factor)
            )
            cv2.imshow(title, image)

        cv2.waitKey(0)
        cv2.destroyAllWindows()

    except cv2.error:
        print("Bildanzeige nicht möglich (kein Bildschirm).")



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

    else:

        # Absoluten Pfad erzeugen
        image_path = os.path.abspath(args.image)

        print("Gesuchter Bildpfad:")
        print(image_path)

        # Farbig laden, damit Schwarz von Grün unterscheidbar ist
        image = cv2.imread(
            image_path,
            cv2.IMREAD_COLOR
        )

        if image is None and image_path.lower().endswith(".heic"):
            raise ValueError(
                "HEIC-Bilder (iPhone) kann OpenCV nicht lesen. "
                "Bitte zuerst in PNG oder JPG umwandeln."
            )

        if image is None:
            raise FileNotFoundError(
                f"Bild konnte nicht geladen werden: {image_path}"
            )

    # Bildverarbeitung
    selected_pair, distance_px = process_image(image)

    if selected_pair is None:

        print("Kein passendes Linienpaar gefunden.")

    else:

        distance_mm = distance_px * config.MM_PER_PIXEL

        angle_diff = angle_difference(
            selected_pair[0]["angle"],
            selected_pair[1]["angle"]
        )

        length_difference = relative_difference(
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

    result = draw_results(
        image,
        selected_pair,
        distance_px
    )

    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)

    # Dateiname nach dem Eingabebild, z.B. Testbild_1.4_result.jpg
    if args.image is None:
        name = "Demo"
    else:
        name = os.path.splitext(os.path.basename(args.image))[0]

    result_path = os.path.join(
        config.OUTPUT_FOLDER,
        f"{name}_result.jpg"
    )

    cv2.imwrite(result_path, result)

    print(f"\nResultat gespeichert: {os.path.abspath(result_path)}")

    if config.SHOW_INTERMEDIATE_IMAGES:

        show_images({
            "Original": image,
            "Endresultat": result
        })


if __name__ == "__main__":
    main()

#mit Testbildern Programm starten:
#python main.py --image test_images/Testbild_0.1.png
