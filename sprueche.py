"""Sprüche des Tages. Jeden Tag ist ein anderer dran. Die Liste kannst du beliebig ändern."""

import datetime

SPRUECHE = [
    "Morgenstund hat Gold im Mund.",
    "Wer wagt, gewinnt.",
    "Aller Anfang ist schwer.",
    "Übung macht den Meister.",
    "Der frühe Vogel fängt den Wurm.",
    "Ohne Fleiß kein Preis.",
    "Probieren geht über Studieren.",
    "In der Ruhe liegt die Kraft.",
    "Steter Tropfen höhlt den Stein.",
    "Wo ein Wille ist, ist auch ein Weg.",
    "Lachen ist die beste Medizin.",
    "Was du heute kannst besorgen, das verschiebe nicht auf morgen.",
    "Es ist noch kein Meister vom Himmel gefallen.",
    "Ende gut, alles gut.",
    "Kleine Schritte führen auch ans Ziel.",
    "Auf Regen folgt Sonnenschein.",
    "Geteilte Freude ist doppelte Freude.",
    "Gut Ding will Weile haben.",
    "Frisch gewagt ist halb gewonnen.",
    "Man lernt nie aus.",
]


def spruch_des_tages(tag=None):
    tag = tag or datetime.date.today()
    return SPRUECHE[tag.toordinal() % len(SPRUECHE)]
