"""Tests of online_chords.guide with hand-written online versions (no network)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from importer.fill_chords import fill_chords  # noqa: E402
from importer.online_chords import guide  # noqa: E402
from tests.test_fill_chords import ME_SOBREPASA  # noqa: E402

# The same song as a chord site shows it: in D (no capo), the long line not split.
ME_SOBREPASA_ONLINE = """Intro:
D Bm G A7

D
Tú me sondeas y me conoces,
Bm
cuando me siento o me levanto,
G
de lejos penetras mis pensamientos;
A7
distingues mi camino y mi descanso.

D
Todas mis sendas te son familiares,
Bm
conoces mis palabras.
G
Me estrechas, me cubres con tu palma.
A7
Tanto saber me sobrepasa.

        G         A
¿Adónde iré lejos de tu aliento,
   D         D/C#        Bm
a dónde escaparé de tu mirada?
           Em             A7
Allí estás tú, allí te encuentro.

D
Mas si digo: que al menos la tiniebla me encubra,
Bm
que la luz se haga noche en torno a mí.
G
La noche es clara como el día.
   A7
La tiniebla no es oscura para ti."""

TWO_VERSES = "G\nuno dos tres\nD\ncuatro cinco seis\n\nAm\nsiete ocho nueve\nF\ndiez once doce\n\n"
TWO_VERSES_IN_A = "A\nuno dos tres\nE\ncuatro cinco seis\n\nBm\nsiete ocho nueve\nG\ndiez once doce\n\n"


def test_without_online_versions_same_as_fill_chords():
    new, filled, doubts = guide(ME_SOBREPASA, [])
    assert new == fill_chords(ME_SOBREPASA)[0]
    assert filled == ["stanza 3 (Todas mis sendas te…) <- stanza 2 (shape)"]
    assert len(doubts) == 1 and doubts[0].endswith("have 3, 4 (shape)")


def test_me_sobrepasa_in_another_key():
    new, filled, doubts = guide(ME_SOBREPASA, [("https://x/me", ME_SOBREPASA_ONLINE)])
    expected = fill_chords(ME_SOBREPASA)[0]
    for chord, lyric in [("G", "Mas si digo"), ("Em", "que la luz"), ("C", "La noche es"), ("   D7", "La tiniebla no")]:
        expected = expected.replace(lyric, f"{chord}\n{lyric}", 1)
    assert "G\nMas si digo: «Que al menos la tiniebla\nme encubra,\nEm\nque la luz" in new  # line break kept
    assert new == expected
    assert filled == ["stanza 3 (Todas mis sendas te…) <- stanza 2 (confirmed online)",
                      "stanza 7 (Mas si digo: «Que…) <- online: https://x/me"]
    assert doubts == []


def test_online_overrides_wrong_model():
    body = TWO_VERSES + "trece catorce quince\ndieciseis diecisiete"
    online = TWO_VERSES_IN_A + "A\ntrece catorce quince\nE\ndieciseis diecisiete"
    assert fill_chords(body)[1] == ["stanza 3 (trece catorce quince…) <- stanza 2"]
    new, filled, doubts = guide(body, [("u", online)])
    assert new == TWO_VERSES + "G\ntrece catorce quince\nD\ndieciseis diecisiete"
    assert filled == ["stanza 3 (trece catorce quince…) <- stanza 1 (online: u)"] and doubts == []


def test_model_with_a_label_line():
    body = "G\nla la la\nD\nle le le\n\nFinal:\nG\nuno dos\nD\ntres\n\ncuatro cinco\nseis\nsiete"
    online = "G\nla la la\nD\nle le le\n\nG\ncuatro cinco\nD\nseis siete"
    _, filled, _ = guide(body, [("u", online)])
    assert filled == ["stanza 3 (cuatro cinco…) <- stanza 2 (confirmed online)"]


def test_online_chord_not_in_our_song():
    body = TWO_VERSES + "aleluya aleluya"
    new, filled, doubts = guide(body, [("u", TWO_VERSES_IN_A + "C       D\naleluya aleluya")])
    assert new == body and filled == []
    assert doubts == ["stanza 3 (aleluya aleluya…): online chord C isn't in our song (online: u)"]


def test_single_line_stanza_filled():
    body = TWO_VERSES + "aleluya aleluya"
    new, filled, doubts = guide(body, [("u", TWO_VERSES_IN_A + "A       E\naleluya aleluya")])
    assert new == TWO_VERSES + "G       D\naleluya aleluya"
    assert filled == ["stanza 3 (aleluya aleluya…) <- online: u"] and doubts == []
