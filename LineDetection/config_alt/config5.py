
# ==========================================
# Version 0.5 - Connected Components
# ==========================================

# Thresholding
MODE = "BLACK_ON_WHITE"
THRESHOLD = 127

# Flächenerkennung
MIN_COMPONENT_AREA = 100

# Mindestlänge
MIN_LINE_LENGTH = 60

# Breite der gesuchten Flächen
MIN_LINE_THICKNESS = 3
MAX_LINE_THICKNESS = 40

# Mindest-Streckung Länge / Breite
MIN_ELONGATION = 4.0

# Kalibrierung
MM_PER_PIXEL = 0.25

# Linienauswahl
MAX_ANGLE_DIFFERENCE = 3.0
MAX_LENGTH_DIFFERENCE = 0.30
MIN_OVERLAP_RATIO = 0.60

# Gewichtung
ANGLE_WEIGHT = 0.60
LENGTH_WEIGHT = 0.10
OVERLAP_WEIGHT = 0.30

# Anzeige
SHOW_INTERMEDIATE_IMAGES = True

# Ausgabe
OUTPUT_FOLDER = "results"


# ==========================================
# Version 0.5 - Connected Components
# ==========================================

MIN_COMPONENT_AREA = 30

MIN_LINE_LENGTH = 60

MIN_LINE_THICKNESS = 1
MAX_LINE_THICKNESS = 60

# Verhältnis der Varianz in Längs- und Querrichtung
MIN_ELONGATION = 1.0

# Mindestgeradheit zwischen 0 und 1
MIN_STRAIGHTNESS = 0.0

