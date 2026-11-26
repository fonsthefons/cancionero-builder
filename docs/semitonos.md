# Semitonos over psalms: chords and syllables

What the builder does when a psalm gets a semitono (cancionero-liturgia's "Choose fórmula"),
the rules worked out with the user, and what is still open. Add to it as we learn more.

## What it does now (web/js/formula.js)

**Which bar each line sings** (`versePlan`, `semitono2Plan`): de 2 alternates bars 1, 2; an odd
verse gets one flexa, placed by punctuation. De 3 / de 4: one bar per line, the verse must have
exactly 3 / 4 lines (de 4 splits the Gloria's first line).

**Where each chord goes** (`chordSpots`, `chordLineText`), from the semitono's melody (ABC):
- The bar's notes up to the long reciting note (length ≥ 4) take the line's first syllables,
  one each. Their chords go there (usually just the first chord, on the first syllable).
- The notes after the reciting note end on the **line's last stressed syllable**: the last note on
  it, each earlier note one syllable before. A chord goes over the first letter of its note's
  syllable. So in Alegre 5 bar 1 (`"D"F4 G A "G"B2`): D on the first syllable, G on the stressed
  syllable: aguda "de [G]Dios", llana "la [G]cierva", esdrújula "invo[G]cándote".
- A tuplet `(3F/G/F/` counts as one syllable.
- Chords that would touch move right. If the melody's chords don't match the chord line's (count
  per bar), the old placement is used: first chord on the first word, the others on the last words.

**Syllables** (`lineSyllables`, port of docs/experiments/semitono-marks/marks.py): Spanish
spelling rules (diphthongs, hiatus with a, e, o or accented í/ú, consonant clusters), stress from
the accent mark or the ending (vowel, n, s → second to last), a list of unstressed little words
(`ATONIC`: el, la, de, y, mi, tu, su, que, es…), and sinalefa across words **unless one of the
two vowels is stressed** ("de|agua", "recuerdo|otros", "entraré|a"; but "se‿acongoja").

## Evidence (user's marks, docs/experiments/semitono-marks/)

| Round | Semitono | Psalms | Lines | Result |
|---|---|---|---|---|
| 1 (rules made from it) | (11) Alegre 5 | 41, 99, 62 | 85 | 85/85 after the user's answers |
| 2 (held out, pre-filled) | (11) Alegre 5 | 148, 121, 116 | 63 | 63/63, nothing changed |
| 3 (held out, pre-filled) | (5) Narrativo breve: 1 and 0 passing notes | 130, 125, 112 | 51 | 50/51; the miss is Si-ón (hiatus) |
| JS port | the same 3 files | | 193 | 193/193 chords where the user put them (`check_js_chords.py`) |

Every semitono in the book (47) has melody chords matching its chord line, so none uses the old
placement (`check_spots.py`).

## Open: chord placement

Only bars with chords on the first and last notes are tested (de 2 Alegre 5, Narrativo breve).
Everything else follows the same mapping but nobody has checked it by singing:

1. **Chords on passing notes**: Narrativo 21 / 23, Alegre 2, Alegre 3 Rodrigo, Alegre 4, Fernando 14,
   Solemne, Suplicante 1 / 2 / 4, Glorioso, the de 3 and most de 4. Assumed one note per
   syllable going back from the stress. Next check: a pre-filled page for one of them
   (`marks.py <semitono> <psalms> -o page.html --pred`).
2. **Bars whose last note has no chord** (Glorioso bar 1 `"D"C D2`, Miserere, Cantad al Señor,
   Gorgoritos bar 1): the last chord lands one or more syllables before the stress. Probably
   right, unchecked.
3. **Notes before the reciting note** (pickup): Glorioso `"A"C/ E4…`, Laudate Dominum
   `D/"D"F/ A4…` (its D chord goes on the 2nd syllable). Unchecked.
4. **A second long note after the reciting one**: Nistalmata bars 3–4 (`"F"G4 A4 F "Dm"D2`,
   `D4 "G"G4 F "C"E2`). Treated as one syllable; it may be a second reciting tone covering
   several syllables. Then the G chord would be wrong.
5. **Hiatus hidden by spelling**: santuario (san-tu-a-rio), Sión (Si-ón). The chord goes one
   syllable off when the stressed syllable is one of these. 2 of 199 marked lines. A small list of
   exception words would fix it if it matters.
6. **Unstressed little words** (`ATONIC`) are a hand-made list. A line ending in one, or with no
   stressed word, uses its last syllable. "es" is unstressed (user's marks: "misericordia‿es").
7. **Short lines** (fewer syllables than notes): positions are clamped to the first syllable and
   chords pushed right, so they can land later than sung.
8. **Rodrigo (16)** (3 passing notes in bar 2): page `rodrigo-round3.html` pre-filled, not marked yet.
   René (15) dropped: hard to sing.

## Open: marking the syllables where the melody changes (later feature)

The same rules give the syllable each note starts on (`marks.py predict`; the page shows them).
Not in the book yet. Open points:

1. **How to show it**: underline, italic, bold or colour on the syllables where a new note starts
   (all of them, or only the stressed one). Not designed.
2. **Sinalefa by taste**: "noche | y día" (the user split it, no stressed vowel) and "júbilo | y‿a
   alabanza" (three vowels: only the last two joined). The user: either is fine.
3. **Short lines**: when there are fewer syllables than notes, the reciting note and the first
   passing note share the first syllable ("t[E]e-[A]e [G]re[F]cuerdo", "d[E]e-[A]el [G]Dios
   [F]vivo"). How to show two notes on one syllable is open.
4. **Melismas** in general (tuplets, two notes on one syllable): not marked by the user yet.
5. **Hiatus** (point 5 above) matters more here: the marked syllable would be wrong.

## Tools

- `docs/experiments/semitono-marks/marks.py`: builds the marking page (`--pred` fills it with the
  rule's guess); `--test` self-check.
- `show_marks.py <marks.json>`: the user's marks against word stress.
- `rules.py <marks.json>`: scores the rule (Python) on a marks file.
- `check_js_chords.py`, `check_spots.py` (same folder): formula.js against the marks / every
  semitono in the book (read-only, WebKit).
