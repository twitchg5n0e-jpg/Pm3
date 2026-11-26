
# ==========================================
# LineDetection - Configuration
# ==========================================

# Kontrastmodus:
# BLACK_ON_WHITE
# WHITE_ON_BLACK
MODE = "BLACK_ON_WHITE"

# Bildverarbeitung
THRESHOLD = 127

# Mindestlänge einer erkannten Linie in Pixeln
MIN_LINE_LENGTH = 30

# Maximale Dicke einer Linie in Pixeln
MAX_LINE_THICKNESS = 20

# Kalibrierung
# Beispielwert! Durch deinen Wert ersetzen.
MM_PER_PIXEL = 0.25

# Linienauswahl
MAX_ANGLE_DIFFERENCE = 3.0
MAX_LENGTH_DIFFERENCE = 0.30
MIN_OVERLAP_RATIO = 0.60

# Gewichtung der Bewertung
ANGLE_WEIGHT = 0.50
LENGTH_WEIGHT = 0.25
OVERLAP_WEIGHT = 0.25

# Anzeige
SHOW_INTERMEDIATE_IMAGES = True

# Ausgabeordner
OUTPUT_FOLDER = "results"