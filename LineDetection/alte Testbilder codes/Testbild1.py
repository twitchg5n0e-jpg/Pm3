def create_demo_image():
    """Erzeugt ein Testbild mit 12 getrennten Linien ohne Kollisionen."""

    image = np.ones((900, 1200), dtype=np.uint8) * 255

    # ==========================================
    # GESUCHTE LINIEN
    # Zwei lange, leicht unregelmäßige Linien
    # ==========================================

    line1 = np.array([
        [120, 200],
        [270, 195],
        [420, 201],
        [570, 194],
        [720, 198],
        [870, 193]
    ], dtype=np.int32)

    line2 = np.array([
        [120, 400],
        [270, 395],
        [420, 401],
        [570, 394],
        [720, 398],
        [870, 393]
    ], dtype=np.int32)

    cv2.polylines(image, [line1], False, 0, 9)
    cv2.polylines(image, [line2], False, 0, 9)

    # ==========================================
    # STÖRLINIEN
    # ==========================================

    # 1. Lange Linie mit leicht anderem Winkel
    cv2.line(image, (120, 70), (850, 110), 0, 5)

    # 2. Kurze schräge Linie
    cv2.line(image, (100, 520), (300, 565), 0, 6)

    # 3. Vertikale Linie links
    cv2.line(image, (50, 650), (55, 820), 0, 5)

    # 4. Diagonale Linie unten links
    cv2.line(image, (150, 700), (400, 790), 0, 6)

    # 5. Lange Linie mit anderem Winkel unten
    cv2.line(image, (500, 650), (1050, 590), 0, 5)

    # 6. Kurze horizontale Linie rechts
    cv2.line(image, (950, 200), (1080, 200), 0, 5)

    # 7. Schräge Linie rechts oben
    cv2.line(image, (950, 300), (1100, 340), 0, 5)

    # 8. Vertikale Linie rechts unten
    cv2.line(image, (1100, 450), (1105, 700), 0, 5)

    # 9. Kurze diagonale Linie mittig unten
    cv2.line(image, (500, 500), (620, 550), 0, 5)

    # 10. Horizontale Linie unten mittig
    cv2.line(image, (650, 820), (950, 820), 0, 5)

    return image