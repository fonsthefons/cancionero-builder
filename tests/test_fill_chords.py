"""Tests of fill_chords: copying chords onto lyric-only stanzas."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from importer.fill_chords import fill_chords  # noqa: E402

ME_SOBREPASA = """Intro: G Em C D7

G
Tú me sondeas y me conoces,
Em
cuando me siento o me levanto,
   C
de lejos penetras mis pensamientos;
  D7
distingues mi camino y mi descanso.

Todas mis sendas te son familiares,
conoces mis palabras.
Me estrechas, me cubres con tu palma.
Tanto saber me sobrepasa.

**
         C         D
¿Adónde iré lejos de tu aliento,
   G         G/F#        Em
a dónde escaparé de tu mirada?
           Am             D7
Allí estás tú, allí te encuentro.
**

G Em C D7

    G
Si vuelo hasta el margen de la aurora,
    Em
si emigro hasta el confín del mar,
 C
allí me alcanzará tu mano izquierda,
        D7
o tu derecha me agarrará.

Mas si digo: «Que al menos la tiniebla
me encubra,
que la luz se haga noche en torno a mí».
La noche es clara como el día.
La tiniebla no es oscura para ti.
"""


def test_me_sobrepasa():
    new, filled, doubts = fill_chords(ME_SOBREPASA)
    expected = ME_SOBREPASA
    for chord, lyric in [
        ("G", "Todas mis sendas"),
        ("Em", "conoces mis palabras."),
        ("   C", "Me estrechas"),
        ("  D7", "Tanto saber"),
    ]:
        expected = expected.replace(lyric, f"{chord}\n{lyric}", 1)
    assert new == expected
    assert filled == ["stanza 3 (Todas mis sendas te…) <- stanza 2"]
    assert len(doubts) == 1 and doubts[0].startswith("stanza 7 (Mas si digo:")
    assert "5 lines" in doubts[0] and doubts[0].endswith("have 3, 4")


def test_same_text_beats_line_count():
    body = "F\nverse uno\nG\nverse dos\nC\nverse tres\n\n**\nAm\nHola mundo\nDm\nadios mundo\nEm\nsiempre\n**\n\nHola mundo (x2)\nAdiós, mundo\nsiempre"
    new, filled, doubts = fill_chords(body)
    assert new.endswith("Am\nHola mundo (x2)\nDm\nAdiós, mundo\nEm\nsiempre")
    assert filled == ["stanza 3 (Hola mundo (x2)…) <- stanza 2"] and not doubts


def test_chord_past_short_line_is_pulled_back():
    body = "C        G\na long lyric line\nAm\nb\n\nshort\nxyz"
    new, _, _ = fill_chords(body)
    assert new.endswith("C   G\nshort\nAm\nxyz")


def test_body_without_chords_unchanged():
    body = "uno\ndos\n\ntres\ncuatro"
    new, filled, doubts = fill_chords(body)
    assert new == body and filled == [] and len(doubts) == 2
