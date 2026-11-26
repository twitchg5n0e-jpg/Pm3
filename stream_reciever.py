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
import asyncio


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
    cv2.namedWindow("Entzerrt", cv2.WINDOW_NORMAL)   # Fenster mit der Maus skalierbar
    

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

# ===================== Verbindung zu C++ =====================

# ===================== Verbindung zu C++ =====================

STEUERUNG_HOST = "127.0.0.1"   # C++ läuft auf demselben Rechner
STEUERUNG_PORT = 7000          # Port des Befehlsservers (mit dem Kollegen abgemacht)

browser = set()                # alle offenen /steuerung-WebSockets
cpp_schreiber = None           # Schreib-Ende der TCP-Verbindung, None = nicht verbunden


async def an_alle_browser(text):
    """Schickt einen Text an alle offenen /steuerung-WebSockets."""
    for ws in list(browser):          # list(): Kopie, falls sich die Menge ändert
        try:
            await ws.send_str(text)
        except ConnectionResetError:
            browser.discard(ws)       # Browser ist weg


async def mit_cpp_verbinden():
    """Läuft im Hintergrund: verbindet sich mit C++ und leitet jede Zeile weiter."""
    global cpp_schreiber

    while True:
        # ---------- Verbinden (bei Fehler: 2 s warten, neu versuchen) ----------
        try:
            leser, schreiber = await asyncio.open_connection(STEUERUNG_HOST, STEUERUNG_PORT)
        except OSError:
            await asyncio.sleep(2)
            continue

        print("C++ verbunden")
        cpp_schreiber = schreiber

        # ---------- Zeilen lesen und an die Browser weitergeben ----------
        try:
            while True:
                zeile = await leser.readline()   # wartet bis zum nächsten "\n"
                if not zeile:                    # leer = C++ hat die Verbindung geschlossen
                    break
                await an_alle_browser(zeile.decode().strip())
        except ConnectionResetError:
            pass                                 # C++ ist abgestürzt oder beendet

        # ---------- Verbindung weg ----------
        print("C++ getrennt")
        cpp_schreiber = None
        schreiber.close()
        await an_alle_browser('{"zustand": "getrennt"}')
        await asyncio.sleep(2)


async def steuerung(request):
    """WebSocket /steuerung: Befehle vom Browser an C++ weitergeben."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    browser.add(ws)
    print("Steuerung: Browser verbunden")

    try:
        async for nachricht in ws:
            if nachricht.type == web.WSMsgType.TEXT:
                befehl = nachricht.data
                print("Befehl:", befehl)
                if cpp_schreiber is not None:
                    cpp_schreiber.write((befehl + "\n").encode())
                    await cpp_schreiber.drain()
                else:
                    print("C++ nicht verbunden, Befehl verworfen")
    finally:
        browser.discard(ws)
        print("Steuerung: Browser getrennt")

    return ws


cpp_aufgabe = None             # die Hintergrund-Aufgabe (merken, damit Python sie nicht wegräumt)


async def beim_start(app):
    """Wird einmal beim Start des Servers aufgerufen."""
    global cpp_aufgabe
    cpp_aufgabe = asyncio.create_task(mit_cpp_verbinden())

# ===================== Start =====================

app.router.add_get("/", startseite)            # Webseite
app.router.add_get("/ws", leitung)             # WebSocket: Bilder
app.router.add_get("/steuerung", steuerung)    # WebSocket: Befehle und Zustand (C++)

app.on_startup.append(beim_start)              # Verbindung zu C++ im Hintergrund starten

# HTTPS mit selbst erstelltem Zertifikat (Safari braucht HTTPS für die Kamera)
ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ctx.load_cert_chain("cert.pem", "key.pem")

web.run_app(app, host="0.0.0.0", port=8443, ssl_context=ctx)