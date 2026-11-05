#!/usr/bin/env bash
# Baut und startet den Pruefstand (C++-Programm mit Webserver).
#
# Beim ersten Start wird eine eigene Zertifizierungsstelle (CA) in zertifikat/ erzeugt. Das Handy
# laedt sie einmalig ueber http://<IP des Pi>:8080/ca.crt und vertraut ihr:
#   iPhone:  installieren, dann Einstellungen > Allgemein > Info > Zertifikatsvertrauen einschalten
#   Android: Einstellungen > Sicherheit > Zertifikat installieren > CA-Zertifikat
# Danach die Seite ueber https://<IP des Pi>:8443 oeffnen (nur ueber HTTPS gibt es die Kamera).
set -euo pipefail
cd "$(dirname "$0")"

mkdir -p zertifikat
cd zertifikat

# Eigene CA (einmalig, 10 Jahre)
if [[ ! -f ca.key ]]; then
  openssl ecparam -name prime256v1 -genkey -noout -out ca.key
  openssl req -x509 -new -key ca.key -sha256 -days 3650 -subj "/CN=Pruefstand CA" -out ca.crt
fi

# Server-Zertifikat fuer alle aktuellen IP-Adressen; neu, wenn sich die Adressen geaendert haben
ips=$(hostname -I 2>/dev/null || ip -4 -o addr show | awk '{split($4,a,"/"); print a[1]}')
san="DNS:localhost,DNS:$(hostname).local,IP:127.0.0.1"
for ip in $ips; do [[ $ip == *:* ]] || san+=",IP:$ip"; done
if [[ ! -f server.crt || "$(cat server.san 2>/dev/null)" != "$san" ]]; then
  openssl ecparam -name prime256v1 -genkey -noout -out server.key
  openssl req -new -key server.key -subj "/CN=Pruefstand" -out server.csr
  printf "subjectAltName=%s\nextendedKeyUsage=serverAuth\n" "$san" > server.ext
  # max. 825 Tage, sonst lehnt iOS das Zertifikat ab
  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 800 -sha256 \
    -extfile server.ext -out server.crt
  echo "$san" > server.san
  rm -f server.csr server.ext
fi
cd ..

make
echo
echo "Handy: zuerst einmal http://<IP>:8080/ca.crt installieren, dann https://<IP>:8443 oeffnen"
for ip in $ips; do [[ $ip == *:* ]] || echo "  https://$ip:8443"; done
echo
exec ./pruefstand
