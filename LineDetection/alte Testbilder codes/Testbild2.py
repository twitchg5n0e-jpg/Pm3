
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
