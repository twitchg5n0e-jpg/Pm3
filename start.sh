#!/usr/bin/env bash
# Startet den Server fuer Android und iPhone (USB-Tethering bzw. Persoenlicher Hotspot per Kabel).
# Erzeugt beim ersten Start eine eigene Zertifizierungsstelle (CA). Das Handy installiert deren
# Zertifikat einmal, danach vertraut es jedem Server-Zertifikat, das dieses Skript ausstellt.
set -euo pipefail
cd "$(dirname "$0")"
DIR=zertifikat
NAME="$(hostname).local"
mkdir -p "$DIR"

if [ ! -f "$DIR/kamera-ca.crt" ]; then
  echo "Erzeuge Zertifizierungsstelle (einmalig) ..."
  openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=Handy-Kamera CA" \
    -keyout "$DIR/ca.key" -out "$DIR/kamera-ca.crt" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
fi

# Alle IPv4-Adressen des Pi; beim Tethering vergibt das Handy sie neu.
ips() { hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+(\.[0-9]+){3}$' | sort | tr '\n' ' ' || true; }

# Server-Zertifikat fuer den Namen und die aktuellen Adressen ausstellen.
# Hoechstens 825 Tage gueltig, sonst lehnt iOS es ab.
issue_cert() {
  local san="DNS:$NAME,DNS:localhost,IP:127.0.0.1" ip
  for ip in $1; do san="$san,IP:$ip"; done
  openssl req -newkey rsa:2048 -nodes -subj "/CN=$NAME" \
    -keyout "$DIR/server.key" -out "$DIR/server.csr" 2>/dev/null
  openssl x509 -req -in "$DIR/server.csr" -CA "$DIR/kamera-ca.crt" -CAkey "$DIR/ca.key" -CAcreateserial \
    -days 800 -out "$DIR/server.crt" 2>/dev/null \
    -extfile <(printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\nbasicConstraints=CA:FALSE\n' "$san")
}

# Python aus dem venv nehmen, falls vorhanden (dort ist aiortc installiert).
PY=python3; [ -x venv/bin/python ] && PY=venv/bin/python
SERVER=""
CURRENT="-"
trap '[ -n "$SERVER" ] && kill "$SERVER" 2>/dev/null; exit 0' EXIT INT TERM

while true; do
  NOW="$(ips)"
  if [ "$NOW" != "$CURRENT" ] || ! kill -0 "$SERVER" 2>/dev/null; then
    if [ -n "$SERVER" ]; then kill "$SERVER" 2>/dev/null || true; wait "$SERVER" 2>/dev/null || true; fi
    CURRENT="$NOW"
    issue_cert "$CURRENT"
    "$PY" server.py --cert "$DIR/server.crt" --key "$DIR/server.key" --ca "$DIR/kamera-ca.crt" &
    SERVER=$!
    echo
    echo "Auf dem Handy öffnen:"
    echo "  https://$NAME:8443"
    for ip in $CURRENT; do echo "  https://$ip:8443"; done
    echo "Zertifikat einmalig installieren: dieselbe Adresse mit http:// und Port 8080"
  fi
  sleep 3
done
