# Semitonos over psalms: chords and syllables

What the builder does when a psalm gets a semitono (cancionero-liturgia's "Choose fórmula"),
the rules worked out with the user, and what is still open. Add to it as we learn more.

## What it does now (web/js/formula.js)

**Which bar each line sings** (`versePlan`, `semitono2Plan`): de 2 alternates bars 1, 2; an odd
verse gets one flexa, placed by punctuation; a quote is never split (a line inside an open « or
“, or a ":" line just before one, doesn't count as a group end). Flexa evidence: round 1
(`docs/experiments/flexa-marks/round1-marks.json`) 59/60 before the quote rule, 60/60 after; it
moves 3 of the book's 201 odd verses. Round 2 (60 unseen verses, incl. the 2 moved ones): 60/60.
81 odd verses never marked. De 3 / de 4: one bar per line, the verse must have
exactly 3 / 4 lines (de 4 splits the Gloria's first line).

**Planned (user, 2026-11-27):**
- Flexas only apply to semitonos de 2 (done, see above: 120/120 marked verses).
- De 3 (user, 2026-11-27): only for psalms whose every verse has 3 lines, the Gloria included
  (one bar per line). That is already what the code does. Salmos: only Salmo 99 fits; Ez 36,
  24-28 and Salmo 92 are one verse off. Hymns: "Bello es el rostro de la luz, abierto" and
  "Padre: has de oír" fit too.
- **Picker hints** (`formulaFit`, done): nothing hidden; green = suggested, shown first; red = not
  recommended (picking it works as before: no chords over the lines when the verses don't fit).
  - de 3: green if every verse has 3 lines, else red.
  - de 4: red if any verse has 3 lines, except the exact standard Gloria ("Gloria al Padre, y al
    Hijo… por los siglos de los siglos. Amén."). Other doxologies count like any verse.
  - Cánticos: tonos rectos green and first.
  - Scratch build check (WebKit, 170 picker songs): de 4 red in 48/102 salmos, 14/35 hymns,
    17/33 cánticos.
- De 4 never uses flexas. Done (`semitono4Plan`, user's de 4 marks round 1: 54/60):
  - 2 lines → bars 1, 4. 3 lines (and 1-line rubrics) don't fit: the song gets no chords.
  - n ≥ 4 lines: n // 4 passes of bars 1–4 (8 lines = two passes). The lines left over share a
    bar with a neighbour (never more than 2 lines on a bar), joined where the first line ends most
    weakly; ties → joins nearest the verse's start or end, then the earliest. E.g. 6 lines
    "En el lecho me acuerdo de ti…" → 1 1 2 3 4 4.
  - Two lines on one bar (`splitBar`): the first line gets the bar's chords counted from its start
    (melody notes up to the reciting note), the second those counted back from its stressed
    syllable. The HTML keeps both lines.
  - The 6 misses are 5/6-line verses where commas tie and the user split by meaning (Salmo 62|3 and
    112|2 have the same punctuation, different splits). Round 2 (60 unseen verses, ≥ 5 lines):
    51/60 (6 lines 30/31, 7–9 lines 10/10, 5 lines 10/15, 10 lines 1/4). Together 105/120.
    `rules2.py` grid-searched line length, short lines ("Aleluya.") and joins in the second pass:
    none beats the rule. The user: some joins are arbitrary, most right is the goal. Kept as is.
  - Songs with their own chords (Bendito eres…, Hora de la tarde…) never get a semitono; the
    marking pages skip them.

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
5. **Hiatus hidden by spelling**: fixed in formula.js with `HIATUS` (Sión, santuario, santuarios;
   add words as found). The Python port (marks.py) doesn't have the list.
6. **Unstressed little words** (`ATONIC`) are a hand-made list. A line ending in one, or with no
   stressed word, uses its last syllable. "es" is unstressed (user's marks: "misericordia‿es").
7. **Short lines** (fewer syllables than notes): positions are clamped to the first syllable and
   chords pushed right, so they can land later than sung.
8. **Rodrigo (16)** (3 passing notes in bar 2): page `rodrigo-round3.html` pre-filled, not marked yet.
   René (15) dropped: hard to sing.

## Syllables where the melody changes ("Sílabas" button, done 2026-11-27)

A "Sílabas" button beside the fórmula button (only when the psalm has a semitono with a melody;
remembered per psalm on this device) underlines, in the browser (`syllableMarks`, `markedText`):
- each syllable where a note **after the reciting note** starts (same rule as the chords: the
  last on the line's last stressed syllable, one syllable each going back);
- only the syllable's letters, each line 3px short so syllables in a row stay apart;
- a double line when two notes start on one syllable (short lines: "te recuerdo");
- two lines on one de 4 bar: all those notes on the second line.
Check: `check_js_syllables.py`: 193/193 lines where the user put the notes. Hidden in print.

Still open:
1. **Sinalefa units**: a merged unit ("se‿acongoja") underlines only the first word's letters.
2. **Sinalefa by taste**: "noche | y día" (the user split it, no stressed vowel) and "júbilo | y‿a
   alabanza" (three vowels: only the last two joined). The user: either is fine.
3. **Melismas** in general (tuplets count as one note): not marked by the user yet.

## Tools

- `docs/experiments/semitono-marks/marks.py`: builds the marking page (`--pred` fills it with the
  rule's guess); `--test` self-check.
- `show_marks.py <marks.json>`: the user's marks against word stress.
- `docs/experiments/flexa-marks/`: `flexa.py` builds the flexa page (odd verses, rule pre-filled;
  marks files given are skipped, `--include` forces verses in), `show.py` lists the user's
  changes, `rules.py` scores variants, `check_js.py` checks formula.js against Python and marks.
- `rules.py <marks.json>`: scores the rule (Python) on a marks file.
- `check_js_chords.py`, `check_spots.py` (same folder): formula.js against the marks / every
  semitono in the book (read-only, WebKit).
