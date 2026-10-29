#!/usr/bin/env python3
"""Liefert die Handy-Seite aus und speichert den Full-HD-Video-Stream, den sie schickt.

HTTPS (Port 8443): Kamera-Seite mit Testverlauf. Browser geben die Kamera nur ueber HTTPS frei.
                   Das Live-Bild kommt per WebRTC und geht Bild fuer Bild an auswertung.verarbeite().
HTTP  (Port 8080): Einrichtungsseite, auf der das Handy einmalig das Zertifikat herunterlaedt.
"""
import argparse
import asyncio
import pathlib
import re
import ssl
import struct
from concurrent.futures import ThreadPoolExecutor

from aiohttp import web
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamError

import auswertung

HERE = pathlib.Path(__file__).resolve().parent
SESSION_RE = re.compile(r"[0-9A-Za-z_-]{1,64}")
NO_CACHE = {"Cache-Control": "no-store"}


async def index(request):
    return web.FileResponse(HERE / "index.html", headers=NO_CACHE)


async def setup_page(request):
    return web.FileResponse(HERE / "einrichten.html", headers=NO_CACHE)


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
            request.app["live_tasks"].add(asyncio.ensure_future(live(track, channel)))

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


async def live(track, channel):
    """Gibt immer das neueste Bild an die Auswertung. Ist sie noch beschaeftigt, werden Bilder ausgelassen,
    damit keine Verzoegerung entsteht."""
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=1)
    busy = None

    def deliver(fut):
        text = fut.result()
        ch = channel.get("info")
        if text and ch and ch.readyState == "open":
            ch.send(str(text))

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
    camera["pcs"] = set()
    camera["live_tasks"] = set()

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
    parser.add_argument("--out", default=str(HERE / "aufnahmen"), help="Ordner fuer die Videos")
    args = parser.parse_args()
    try:
        asyncio.run(serve(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
