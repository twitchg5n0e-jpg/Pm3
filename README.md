# Motorsteuerung mit Up/Down-Tastern (Raspberry Pi 4)

## Struktur
```
motor_projekt/
├── .vscode/        Build-, Run- und Debug-Konfiguration für VS Code
├── src/            Quellcode (motor_tasten.cpp)
├── build/          hier landet das kompilierte Programm
└── Makefile
```

## Voraussetzungen auf dem Pi
```bash
sudo apt install build-essential gdb
```

## In VS Code
Den Ordner auf dem Pi öffnen (direkt oder über die Erweiterung *Remote - SSH*).

| Aktion            | Tastenkürzel / Menü                       |
|-------------------|-------------------------------------------|
| Kompilieren       | `Ctrl+Shift+B`                            |
| Starten           | `Terminal → Run Task… → Run`              |
| Debuggen          | `F5`                                      |

## Im Terminal
```bash
make        # kompilieren
make run    # kompilieren und starten (Beenden mit Ctrl+C)
make clean  # Build löschen
```

Einstellungen (Richtung, Geschwindigkeit, SPI, Dehnmessstreifen) stehen oben in `src/motor_tasten.cpp`.
