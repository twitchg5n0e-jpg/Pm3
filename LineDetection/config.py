# ==========================================
# Version 0.6 - Connected Components
# ==========================================
# Alle Grössenangaben sind relativ zur Bildgrösse,
# damit die Werte für kleine und grosse Bilder passen.

# Thresholding
MODE = "BLACK_ON_WHITE"

# Schwelle relativ zur mittleren Bildhelligkeit (Median):
# Ein Pixel gilt als "schwarz", wenn sein hellster Farbkanal
# dunkler ist als Faktor * Median.
# Es wird zuerst der erste (strengste) Faktor probiert. Wird damit
# kein Linienpaar gefunden (z.B. glänzende, nur dunkelgraue
# Markierungen), kommt der nächste an die Reihe.
THRESHOLD_FACTORS = [0.30, 0.40, 0.50]

# Ein Paar gilt erst, wenn dasselbe Paar auch mit einem um
# CONFIRM_STEP lockereren oder strengeren Faktor gefunden wird
# und sich der Abstand höchstens um CONFIRM_TOLERANCE (Anteil) ändert.
# Das verhindert falsche Paare, kostet aber etwa die doppelte Rechenzeit.
# CONFIRM_STEP = 0 schaltet die Kontrolle aus.
CONFIRM_STEP = 0.10
CONFIRM_TOLERANCE = 0.01

# Gelingt die Kontrolle mit CONFIRM_STEP nicht, wird sie mit diesem
# kleineren Schritt wiederholt (hilft bei glänzenden Markierungen).
# Kostet nur Zeit, wenn die erste Kontrolle scheitert. 0 = aus.
CONFIRM_SMALL_STEP = 0.05

# Bei einer gelockerten Schwelle muss eine Fläche mindestens diesen
# Anteil wirklich schwarzer Pixel (strengste Schwelle) enthalten
MIN_CORE_RATIO = 0.05

# Grösse des Filters gegen kleine Störungen (Anteil der Bildbreite)
MORPH_KERNEL_RATIO = 0.0015

# Flächenerkennung: Mindestfläche (Anteil der Bildfläche)
MIN_COMPONENT_AREA_RATIO = 0.00002

# Grössere Flächen werden ignoriert (Anteil der Bildfläche)
MAX_COMPONENT_AREA_RATIO = 0.05

# Flächen ignorieren, deren umschliessendes Rechteck grösser ist
# (Anteil der Bildfläche), z.B. ein dünner Rahmen um das ganze Bild
MAX_COMPONENT_BOX_RATIO = 0.50

# Linien ignorieren, die den Bildrand berühren
# (abgeschnittene Linien, Spannbacken, dunkler Bildrand)
IGNORE_BORDER_COMPONENTS = True

# Grösster Filter beim Abtrennen dünner Anhängsel an einer Linie
# (Anteil der Bildbreite)
MAX_THIN_PART_RATIO = 0.02

# Mindestlänge einer Linie (Anteil der Bilddiagonale)
MIN_LINE_LENGTH_RATIO = 0.015

# Mindest-Streckung Länge / Breite
MIN_ELONGATION = 3.0

# Mindestgeradheit zwischen 0 und 1
# (1 = gerader, gleichmässig dicker Balken)
MIN_STRAIGHTNESS = 0.25


# Kalibrierung
MM_PER_PIXEL = 0.25

# Linienauswahl

# Mindestfläche einer Linie im Verhältnis zur grössten gefundenen Linie
MIN_RELATIVE_AREA = 0.20

MAX_ANGLE_DIFFERENCE = 5.0
MAX_LENGTH_DIFFERENCE = 0.40
MAX_THICKNESS_DIFFERENCE = 0.60
# (0.30 statt 0.60: schief geklebte Markierungen verschieben sich
# bei grosser Dehnung gegeneinander)
MIN_OVERLAP_RATIO = 0.30

# Gewichtung (Summe = 1)
ANGLE_WEIGHT = 0.40
LENGTH_WEIGHT = 0.10
THICKNESS_WEIGHT = 0.20
OVERLAP_WEIGHT = 0.30

# Zuschlag für Paare, die dünner sind als das dickste gültige Paar
# (0 = Dicke spielt keine Rolle)
THIN_PAIR_WEIGHT = 2.0

# Schlechtere Paare werden verworfen (0 = perfekt passend, 1.0 = aus).
# Ein strenger Wert wie 0.45 verhindert falsche Paare, wenn eine
# Markierung fehlt, lehnt aber auch eine leicht gekippte Kamera ab.
MAX_PAIR_SCORE = 1.0

# Nachmessung der beiden gefundenen Markierungen im Originalbild

# Zugabe an beiden Bandenden für den Ausschnitt (Anteil der Länge)
REFINE_END_MARGIN = 0.10

# Glättung entlang des Bands (Anteil der Banddicke)
REFINE_SMOOTH_RATIO = 0.33

# Das Band muss deutlich dunkler sein als seine Umgebung
# (Helligkeit Band / Helligkeit Umgebung höchstens so gross)
REFINE_MAX_BAND_LEVEL = 0.70

# Erlaubte Abweichung eines Kantenpunkts von der Kantengeraden
# (Anteil der Banddicke, mindestens 1 Pixel)
REFINE_EDGE_TOLERANCE = 0.05

# Mindestanteil der Bandlänge mit sauberen, geraden Kanten.
# Darunter bleibt es beim Ergebnis der Flächenerkennung.
REFINE_MIN_GOOD_RATIO = 0.50

# Grösste erlaubte Verschiebung der Mittelachse quer zum Band
# (Anteil der Banddicke). Darüber bleibt es beim alten Ergebnis.
REFINE_MAX_SHIFT_RATIO = 0.50

# Verfolgung von Bild zu Bild (process_frame, für Live-Bilder)

# Suchfenster um die letzte Position der Linie: Zugabe auf allen
# Seiten (Anteil der Linienlänge). Zuerst wird im kleinsten Fenster
# gesucht; ist die Linie dort nicht, im nächstgrösseren.
TRACK_SEARCH_RATIOS = [0.50, 1.00, 2.00]

# Lücken entlang des Bands bis zu dieser Grösse werden beim
# Verfolgen geschlossen (Anteil der Banddicke, 0 = aus)
TRACK_CLOSE_RATIO = 0.50

# Grösste erlaubte Änderung von Länge und Dicke von Bild zu Bild
TRACK_MAX_CHANGE = 0.35

# Grösste erlaubte Änderung des Abstands von Bild zu Bild (Anteil).
# Grössere Sprünge gelten als "verloren" (z.B. Sprung auf ein anderes
# dunkles Objekt). Im echten Zugversuch ändert sich der Abstand pro
# Bild viel weniger; ein kleinerer Wert (z.B. 0.02) ist dann sicherer.
TRACK_MAX_DISTANCE_CHANGE = 0.05

# Nach so vielen verlorenen Bildern wird zusätzlich im ganzen Bild
# nach den bestätigten Markierungen gesucht
TRACK_MAX_LOST_FRAMES = 5

# Nach längerem Verlust wird zusätzlich im ganzen Bild gesucht. Das
# gefundene Paar gilt nur als die bestätigten Markierungen, wenn die
# Banddicke passt und der Abstand höchstens um diesen Anteil anders ist.
TRACK_RELOCK_DISTANCE_CHANGE = 0.05

# False: Die Verfolgung beginnt erst nach confirm_tracker().
# True: Das erste gefundene Paar wird ohne Bestätigung verfolgt.
TRACK_AUTO_CONFIRM = False

# Anzeige
SHOW_INTERMEDIATE_IMAGES = True

# Detail-Ausgaben im Terminal (jede Komponente, jedes Paar).
# Für den Live-Betrieb auf False setzen.
PRINT_DETAILS = True

# Ausgabe
OUTPUT_FOLDER = "results"
