# Zertifikate für HTTPS

Das Handy braucht HTTPS, sonst gibt der Browser die Kamera nicht frei. `start.sh` erzeugt dafür
alles in diesem Ordner selbst. Ausser dieser README kommt nichts davon ins Repository (siehe `.gitignore`).

| Datei        | Inhalt                                                          | Gültig      |
|--------------|-----------------------------------------------------------------|-------------|
| `ca.key`     | geheimer Schlüssel der eigenen Zertifizierungsstelle (CA)       | –           |
| `ca.crt`     | CA-Zertifikat, wird einmalig auf dem Handy installiert          | 10 Jahre    |
| `server.key` | geheimer Schlüssel des Webservers                               | –           |
| `server.crt` | Server-Zertifikat, von der CA unterschrieben                    | 800 Tage    |
| `server.san` | IP-Adressen/Namen, für die `server.crt` ausgestellt wurde       | –           |
| `ca.srl`     | Seriennummer, von `openssl` verwaltet                           | –           |

`ca.key` und `server.key` nie weitergeben.

## Wann läuft was ab?

```bash
openssl x509 -in zertifikat/ca.crt     -noout -enddate
openssl x509 -in zertifikat/server.crt -noout -enddate
```

Ist ein Zertifikat abgelaufen, zeigt das Handy beim Öffnen von `https://<IP>:8443` eine
Sicherheitswarnung, und die Kamera geht nicht mehr.

## Server-Zertifikat erneuern (alle ~2 Jahre oder bei neuer IP-Adresse)

Das Handy muss dafür **nichts** neu installieren.

1. Pi im gewünschten Netz anschliessen (die aktuellen IP-Adressen kommen ins Zertifikat).
2. Im Projektordner:
   ```bash
   rm zertifikat/server.crt
   ./start.sh
   ```

Hat sich nur die IP-Adresse geändert, erneuert `start.sh` das Server-Zertifikat beim nächsten Start
von selbst. Man muss nichts löschen.

> Das Server-Zertifikat darf höchstens 825 Tage gültig sein, sonst lehnt iOS es ab.
> Deshalb steht in `start.sh` `-days 800`.

## CA erneuern (nach 10 Jahren, oder wenn `ca.key` verloren/weitergegeben wurde)

Danach muss **jedes Handy** die neue CA installieren.

1. Ganzen Ordner löschen und neu starten:
   ```bash
   rm -rf zertifikat/ca.* zertifikat/server.*
   ./start.sh
   ```
2. Auf dem Handy die alte „Pruefstand CA“ entfernen:
   - iPhone: Einstellungen > Allgemein > VPN und Geräteverwaltung > Profil löschen
   - Android: Einstellungen > Sicherheit > Vertrauenswürdige Anmeldedaten > Nutzer > entfernen
3. Neue CA installieren: `http://<IP des Pi>:8080/ca.crt` öffnen.
   - iPhone: Profil installieren, dann **Einstellungen > Allgemein > Info > Zertifikatsvertrauen**
     für „Pruefstand CA“ einschalten
   - Android: Einstellungen > Sicherheit > Zertifikat installieren > CA-Zertifikat
4. `https://<IP des Pi>:8443` öffnen. Es sollte keine Warnung mehr kommen.
