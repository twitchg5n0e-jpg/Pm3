#!/usr/bin/env python3
"""Webserver des Pruefstands: verbindet die Handy-Seite (web/) mit der Steuerung (steuerung/) und der
Bildanalyse (bildanalyse/).

HTTPS (Port 8443): Bedienoberflaeche. Browser geben die Kamera nur ueber HTTPS frei.
                   /stream     speichert den Full-HD-Video-Stream des Handys
                   /offer      Live-Bild per WebRTC, Bild fuer Bild an auswertung.verarbeite()
                   /steuerung  Befehle an das C++-Hauptprogramm, Status und Ereignisse zurueck
HTTP  (Port 8080): Einrichtungsseite, auf der das Handy einmalig das Zertifikat herunterlaedt.
"""
import argparse
import asyncio
import pathlib
import re
import ssl
import struct
import sys
from concurrent.futures import ThreadPoolExecutor

from aiohttp import web
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError

ROOT = pathlib.Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "bildanalyse"))
import auswertung  # noqa: E402

SESSION_RE = re.compile(r"[0-9A-Za-z_-]{1,64}")
NO_CACHE = {"Cache-Control": "no-store"}


async def index(request):
    return web.FileResponse(WEB / "index.html", headers=NO_CACHE)


async def setup_page(request):
    return web.FileResponse(WEB / "einrichten.html", headers=NO_CACHE)


async def ca_cert(request):
    return web.Response(
        body=request.app["ca"].read_bytes(),
        content_type="application/x-x509-ca-cert",
        headers={"Content-Disposition": 'attachment; filename="kamera-ca.crt"', **NO_CACHE},
    )


async def stream(request):
    ws = web.WebSocketResponse(max_msg_size=64 * 1024 * 1024, heartbeat=10)
    await ws.prepare(request)

    session = request.query.get("session", "")
    ext = request.query.get("ext", "")
    if not SESSION_RE.fullmatch(session) or ext not in ("webm", "mp4"):
        await ws.close(code=4000, message=b"ungueltige Sitzung")
        return ws

    # Nach einem Verbindungsabbruch schickt das Handy alle unbestaetigten Teile erneut.
    # Die letzte gespeicherte Teilnummer steht neben dem Video, damit doppelte Teile
    # auch nach einem Neustart des Servers verworfen werden.
    out = request.app["out"]
    path = out / f"{session}.{ext}"
    seq_file = out / f"{session}.teil"
    last_seq = int(seq_file.read_text()) if seq_file.exists() else 0
    print(f"[{session}] verbunden, speichere nach {path}")

    with path.open("ab") as f:
        async for msg in ws:
            if msg.type == web.WSMsgType.BINARY and len(msg.data) >= 4:
                (seq,) = struct.unpack(">I", msg.data[:4])
                if seq > last_seq:
                    f.write(msg.data[4:])
                    f.flush()
                    last_seq = seq
                    seq_file.write_text(str(seq))
                await ws.send_json({"seq": seq, "total": f.tell()})
            elif msg.type == web.WSMsgType.TEXT:
                print(f"[{session}] {msg.data}")

    print(f"[{session}] getrennt")
    return ws


class Steuerung:
    """Verbindung zum C++-Hauptprogramm: Befehle hin, Status und Ereignisse (JSON-Zeilen) an alle Handys."""

    def __init__(self, port):
        self.port = port
        self.writer = None
        self.clients = set()
        self.letzter_status = None

    async def lauf(self):
        while True:
            try:
                reader, self.writer = await asyncio.open_connection("127.0.0.1", self.port)
                await self.verteilen('{"typ":"ereignis","text":"Verbunden mit der Steuerung"}')
                while line := await reader.readline():
                    text = line.decode(errors="replace").strip()
                    if text.startswith('{"typ":"status"'):
                        self.letzter_status = text
                    await self.verteilen(text)
            except OSError:
                pass
            if self.writer:
                self.writer.close()
                self.writer = None
                await self.verteilen('{"typ":"ereignis","text":"Verbindung zur Steuerung verloren"}')
            await asyncio.sleep(2)

    async def verteilen(self, text):
        for ws in list(self.clients):
            try:
                await ws.send_str(text)
            except ConnectionResetError:
                self.clients.discard(ws)

    def senden(self, befehl):
        if self.writer is None:
            return False
        self.writer.write((" ".join(befehl.split()) + "\n").encode())
        return True


async def steuerung_ws(request):
    ws = web.WebSocketResponse(heartbeat=10)
    await ws.prepare(request)
    steuerung = request.app["steuerung"]
    steuerung.clients.add(ws)
    if steuerung.letzter_status:
        await ws.send_str(steuerung.letzter_status)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT and not steuerung.senden(msg.data):
                await ws.send_str('{"typ":"ereignis","text":"Steuerung nicht erreichbar"}')
    finally:
        steuerung.clients.discard(ws)
    return ws


async def offer(request):
    params = await request.json()
    # Keine STUN-Server: Handy und Pi haengen direkt am selben Kabel.
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    request.app["pcs"].add(pc)
    channel = {}

    @pc.on("datachannel")
    def on_datachannel(ch):
        channel["info"] = ch

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            task = asyncio.ensure_future(live(track, channel, request.app["steuerung"]))
            request.app["live_tasks"].add(task)

    @pc.on("connectionstatechange")
    async def on_state():
        print(f"Live-Bild: {pc.connectionState}")
        if pc.connectionState in ("failed", "closed"):
            await pc.close()
            request.app["pcs"].discard(pc)

    await pc.setRemoteDescription(RTCSessionDescription(sdp=params["sdp"], type=params["type"]))
    await pc.setLocalDescription(await pc.createAnswer())
    return web.json_response({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})


def auswerten(frame):
    try:
        return auswertung.verarbeite(frame.to_ndarray(format="bgr24"))
    except Exception as e:  # ein Fehler in der Auswertung soll das Live-Bild nicht beenden
        return f"Fehler in der Auswertung: {e}"


async def live(track, channel, steuerung):
    """Gibt immer das neueste Bild an die Auswertung. Ist sie noch beschaeftigt, werden Bilder ausgelassen,
    damit keine Verzoegerung entsteht. Das Ergebnis geht ans Handy und in die Messdatei der Steuerung."""
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    busy = None

    def deliver(fut):
        text = fut.result()
        ch = channel.get("info")
        if not text:
            return
        if ch and ch.readyState == "open":
            ch.send(str(text))
        steuerung.senden("optik " + str(text).replace(";", ","))

    try:
        while True:
            frame = await track.recv()
            if busy and not busy.done():
                continue
            busy = loop.run_in_executor(executor, auswerten, frame)
            busy.add_done_callback(deliver)
    except MediaStreamError:
        pass
    finally:
        executor.shutdown(wait=False)


async def serve(args):
    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(args.cert, args.key)

    camera = web.Application()
    camera["out"] = pathlib.Path(args.out)
    camera["out"].mkdir(parents=True, exist_ok=True)
    camera.router.add_get("/", index)
    camera.router.add_get("/stream", stream)
    camera.router.add_post("/offer", offer)
    camera.router.add_get("/steuerung", steuerung_ws)
    camera["pcs"] = set()
    camera["live_tasks"] = set()
    camera["steuerung"] = Steuerung(args.steuerung_port)
    steuerung_task = asyncio.create_task(camera["steuerung"].lauf())

    setup = web.Application()
    setup["ca"] = pathlib.Path(args.ca)
    setup.router.add_get("/", setup_page)
    setup.router.add_get("/kamera-ca.crt", ca_cert)

    runners = []
    for app, port, ctx in ((camera, args.https_port, ssl_ctx), (setup, args.http_port, None)):
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, args.host, port, ssl_context=ctx).start()
        runners.append(runner)

    print(f"Kamera-Seite: https://<Pi>:{args.https_port}   Einrichtung: http://<Pi>:{args.http_port}")
    try:
        await asyncio.Event().wait()
    finally:
        steuerung_task.cancel()
        await asyncio.gather(*(pc.close() for pc in camera["pcs"]))
        for runner in runners:
            await runner.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--https-port", type=int, default=8443)
    parser.add_argument("--http-port", type=int, default=8080)
    parser.add_argument("--cert", required=True, help="Server-Zertifikat (von start.sh erzeugt)")
    parser.add_argument("--key", required=True, help="Schluessel zum Server-Zertifikat")
    parser.add_argument("--ca", required=True, help="CA-Zertifikat, das das Handy installiert")
    parser.add_argument("--out", default=str(ROOT / "daten" / "aufnahmen"), help="Ordner fuer die Videos")
    parser.add_argument("--steuerung-port", type=int, default=7000, help="Port des C++-Hauptprogramms")
    args = parser.parse_args()
    try:
        asyncio.run(serve(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
