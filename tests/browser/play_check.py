"""Check the melody play/pause button (melody.js) in Chromium and WebKit: shown only with
a melody, play lights notes and starts oscillators, pause/resume, ends by itself, plays a
fórmula copied above a psalm in the psalm's key, and stops when the fórmula is removed.

Usage: .venv/bin/python tests/browser/play_check.py <book folder with psalm fórmulas>
(build the book first; a copy of cancionero-liturgia works)
"""
import os
import sys
from pathlib import Path

scratch = Path(__file__).parents[2] / "scratch"
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(scratch / "browsers"))
from playwright.sync_api import sync_playwright  # noqa: E402

URL = (Path(sys.argv[1]).resolve() / "index.html").as_uri()
# Count oscillators started, with their frequencies (to check the transposition).
SPY = """() => {
    window.oscFreqs = [];
    const orig = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function () {
        const osc = orig.call(this);
        const start = osc.start.bind(osc);
        osc.start = (t) => { window.oscFreqs.push(osc.frequency.value); start(t); };
        return osc;
    };
}"""
fails = []


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        fails.append(name)


def run(kind):
    with sync_playwright() as p:
        browser = getattr(p, kind).launch()
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.add_init_script(f"({SPY})()")
        page.goto(URL)
        song = page.evaluate("() => document.querySelector('.song .melody').closest('.song').id")
        # Centered: at the top, the fixed top bar covers the controls and takes the tap.
        page.evaluate(f"() => document.getElementById('{song}').scrollIntoView({{block: 'center'}})")
        button = page.locator(f"#{song} .controls .melody-play")
        button.wait_for(timeout=5000)
        page.screenshot(path=str(scratch / "shots" / f"play-{kind}.png"))
        check(f"{kind}: button shown ({song})", button.inner_text() == "▶ Melody")
        no_melody = page.evaluate("() => document.querySelector('.song:not(:has(.melody)) .melody-play')?.closest('.song').id")
        check(f"{kind}: hidden without a melody ({no_melody})",
              no_melody and not page.locator(f"#{no_melody} .melody-play").is_visible())
        button.click()
        page.wait_for_timeout(1200)
        check(f"{kind}: playing shows pause", button.inner_text() == "⏸ Pause")
        check(f"{kind}: a note is lit", page.locator(f"#{song} .melody-playing").count() > 0)
        check(f"{kind}: oscillators started", page.evaluate("window.oscFreqs.length") > 0)
        page.screenshot(path=str(scratch / "shots" / f"play-{kind}-on.png"))
        button.click()
        n = page.evaluate("window.oscFreqs.length")
        page.wait_for_timeout(1500)
        check(f"{kind}: pause stops new notes", page.evaluate("window.oscFreqs.length") == n and button.inner_text() == "▶ Melody")
        button.click()
        page.wait_for_timeout(300)
        check(f"{kind}: resume sounds the paused note again", page.evaluate("window.oscFreqs.length") > n)
        page.wait_for_function("() => !playing", timeout=60000)
        check(f"{kind}: resumes and ends by itself", button.inner_text() == "▶ Melody"
              and page.locator(f"#{song} .melody-playing").count() == 0)

        # A fórmula above a psalm, transposed +2: first note 2 semitones above the plain one.
        formula = page.evaluate("() => BOOK.formulas[0][1][0][0]")
        page.evaluate(f"() => document.getElementById('{formula}').scrollIntoView({{block: 'center'}})")
        fb = page.locator(f"#{formula} .controls .melody-play")
        fb.wait_for(timeout=5000)
        page.evaluate("() => { window.oscFreqs = []; }")
        fb.click()
        page.wait_for_function("() => window.oscFreqs.length", timeout=5000)
        plain = page.evaluate("window.oscFreqs[0]")
        fb.click()
        psalm = page.evaluate("() => document.querySelector('.formula-pick').closest('.song').id")
        pb = page.locator(f"#{psalm} .controls .melody-play")
        page.evaluate(f"() => document.getElementById('{psalm}').scrollIntoView({{block: 'center'}})")
        check(f"{kind}: psalm without fórmula: no button", not pb.is_visible())
        page.evaluate(f"""() => {{ const p = document.getElementById('{psalm}');
            setFormula(p, '{formula}'); p.dataset.transpose = '2'; p.scrollIntoView({{block: 'center'}}); }}""")
        pb.wait_for(timeout=5000)
        page.evaluate("() => { window.oscFreqs = []; }")
        pb.click()
        page.wait_for_function("() => window.oscFreqs.length", timeout=5000)
        moved = page.evaluate("window.oscFreqs[0]")
        check(f"{kind}: fórmula above psalm plays", pb.inner_text() == "⏸ Pause")
        check(f"{kind}: follows transposition ({plain:.1f} -> {moved:.1f})",
              abs(moved / plain - 2 ** (2 / 12)) < 0.01)
        page.screenshot(path=str(scratch / "shots" / f"play-{kind}-psalm.png"))
        page.evaluate(f"() => setFormula(document.getElementById('{psalm}'), null)")
        page.wait_for_timeout(1500)
        check(f"{kind}: removing the fórmula stops it", page.evaluate("() => !playing")
              and not pb.is_visible())
        page.evaluate(f"() => setFormula(document.getElementById('{psalm}'), '{formula}')")
        check(f"{kind}: button reset after", pb.inner_text() == "▶ Melody")
        browser.close()


for kind in ["chromium", "webkit"]:
    run(kind)
print("FAILED:" if fails else "all passed", fails or "")
sys.exit(1 if fails else 0)
