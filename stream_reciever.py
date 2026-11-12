"""
iPhone-Kamera-Stream: Python-Server

Ablauf:
1. Liefert die Webseite (index.html) per HTTPS an Safari aus.
2. Empfängt über einen WebSocket abwechselnd:
   - Text (JSON): Lage des Ausschnitts im ganzen Video (cropX, cropY)
   - Binär: das zugehörige JPEG-Bild
3. Sucht im Bild die 4 ArUco-Marker (ID 0 oben links, 1 oben rechts,
   2 unten links, 3 unten rechts).
4. Wenn alle 4 gefunden wurden:
   - Perspektiv-Korrektur -> Fenster "Entzerrt" (fester Massstab in px/mm)
   - Rahmen um alle Marker zurück ans iPhone schicken
"""

import json
import ssl

import cv2
import numpy as np
from aiohttp import web


# ===================== Einstellungen =====================

# Marker-Geometrie in Metern
ARUCO_INNENABSTAND = 0.03          # Lücke zwischen zwei Markern
ARUCO_GROESSE = 0.03               # Kantenlänge eines Markers
ARUCO_AUSSENABSTAND = ARUCO_INNENABSTAND + 2 * ARUCO_GROESSE   # Aussenkante zu Aussenkante

RAND = 100                         # Rand um die Marker beim Ausschnitt (Pixel)

PIXEL_PRO_MM = 10                  # Auflösung des entzerrten Bildes
ZIEL_GROESSE = int(ARUCO_AUSSENABSTAND * 1000 * PIXEL_PRO_MM)  # Seitenlänge in Pixel


# ===================== ArUco-Detektor =====================

woerterbuch = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)

parameter = cv2.aruco.DetectorParameters()
parameter.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX   # Ecken auf Subpixel genau

detektor = cv2.aruco.ArucoDetector(woerterbuch, parameter)


# ===================== Webserver =====================

app = web.Application()


async def startseite(request):
    """Liefert die Webseite für das iPhone aus."""
    return web.FileResponse("index.html")


async def leitung(request):
    """WebSocket-Verbindung zum iPhone: empfängt Bilder und antwortet mit dem Rahmen."""

    # Zustand für diese Verbindung
    glatt = None        # geglättete Marker-Ecken in Video-Koordinaten
    crop_x = 0          # Lage des aktuellen Ausschnitts im ganzen Video
    crop_y = 0

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print("iPhone verbunden!")

    cv2.namedWindow("Stream", cv2.WINDOW_NORMAL)   # Fenster mit der Maus skalierbar

    async for nachricht in ws:

        # ---------- Bild empfangen ----------
        if nachricht.type == web.WSMsgType.BINARY:
            # print("Bild empfangen:", len(nachricht.data), "Bytes")

            # JPEG-Bytes -> NumPy-Array -> Bild (BGR)
            roh = np.frombuffer(nachricht.data, dtype=np.uint8)
            bild = cv2.imdecode(roh, cv2.IMREAD_COLOR)

            # Marker erkennen
            ecken, ids, _ = detektor.detectMarkers(bild)
            print("Gefunden:", ids)

            if ids is not None and len(ids) == 4:

                # Alle 16 Ecken (4 Marker x 4 Ecken) als Liste von Punkten (x, y)
                punkte = np.concatenate(ecken).reshape(-1, 2)

                # Ecken nach Marker-ID ablegen: marker[id] = 4 Ecken
                marker = {}
                for i in range(len(ids)):
                    marker[int(ids[i])] = ecken[i][0]

                # --- Perspektiv-Korrektur ---

                # Äusserste Ecke jedes Markers im Bild
                # (Ecken-Reihenfolge eines Markers: 0 oben links, 1 oben rechts,
                #  2 unten rechts, 3 unten links)
                quelle = np.array([
                    marker[0][0],   # Marker 0, oben links
                    marker[1][1],   # Marker 1, oben rechts
                    marker[3][2],   # Marker 3, unten rechts
                    marker[2][3],   # Marker 2, unten links
                ], dtype=np.float32)

                # Wo diese Ecken im entzerrten Bild landen sollen
                ziel = np.array([
                    [0,            0],
                    [ZIEL_GROESSE, 0],
                    [ZIEL_GROESSE, ZIEL_GROESSE],
                    [0,            ZIEL_GROESSE],
                ], dtype=np.float32)

                # Glätten gegen Zittern: in Video-Koordinaten, weil sich der
                # Ausschnitt von Bild zu Bild verschieben kann
                quelle_video = quelle + [crop_x, crop_y]
                if glatt is None:
                    glatt = quelle_video                        # erstes Bild
                else:
                    glatt = glatt * 0.9 + quelle_video * 0.1    # gleitender Mittelwert

                # Zurück in Koordinaten des aktuellen Ausschnitts
                quelle_glatt = (glatt - [crop_x, crop_y]).astype(np.float32)

                # Bild entzerren (vor dem Einzeichnen der Marker, damit es sauber bleibt)
                matrix = cv2.getPerspectiveTransform(quelle_glatt, ziel)
                entzerrt = cv2.warpPerspective(bild, matrix, (ZIEL_GROESSE, ZIEL_GROESSE))
                cv2.imshow("Entzerrt", entzerrt)

                # --- Rahmen für den nächsten Ausschnitt ---

                x_min = punkte[:, 0].min()
                x_max = punkte[:, 0].max()
                y_min = punkte[:, 1].min()
                y_max = punkte[:, 1].max()

                # Rahmen um alle Marker plus RAND, in Video-Koordinaten
                await ws.send_json({
                    "x": int(x_min - RAND + crop_x),
                    "y": int(y_min - RAND + crop_y),
                    "b": int(x_max - x_min + 2 * RAND),
                    "h": int(y_max - y_min + 2 * RAND),
                })

            # Gefundene Marker ins Live-Bild zeichnen und anzeigen
            cv2.aruco.drawDetectedMarkers(bild, ecken, ids)
            cv2.imshow("Stream", bild)
            cv2.waitKey(1)      # nötig, damit OpenCV die Fenster neu zeichnet

        # ---------- Text empfangen: Lage des Ausschnitts ----------
        else:
            print("Text empfangen:", nachricht.data)
            daten = json.loads(nachricht.data)
            crop_x = daten["cropX"]
            crop_y = daten["cropY"]

    print("iPhone getrennt")
    cv2.destroyAllWindows()

    return ws


# ===================== Start =====================

app.router.add_get("/", startseite)     # Webseite
app.router.add_get("/ws", leitung)      # WebSocket

# HTTPS mit selbst erstelltem Zertifikat (Safari braucht HTTPS für die Kamera)
ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ctx.load_cert_chain("cert.pem", "key.pem")

web.run_app(app, host="0.0.0.0", port=8443, ssl_context=ctx)
