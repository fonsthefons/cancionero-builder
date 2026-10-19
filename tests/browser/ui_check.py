"""Full check of index.html in Chromium and WebKit (Safari's engine) at phone,
iPad and laptop sizes: chord alignment, fit, transposition, and every UI feature.

Usage: .venv/bin/python tests/browser/ui_check.py <book folder> [--shots]
(build the book first; browsers are installed in scratch/browsers, see README)
"""
import json
import os
import sys
from pathlib import Path

here = Path(__file__).parent
scratch = here.parent.parent / "scratch"
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(scratch / "browsers"))
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
BOOK = (Path(_args[0]).resolve() / "index.html").as_uri()
KEY = None  # storage prefix, read from the page's BOOK constant
CHECKS = str(here / "checks.js")
SHOTS = scratch / "shots"
SHOTS.mkdir(exist_ok=True)
TAKE_SHOTS = "--shots" in sys.argv

from playwright.sync_api import sync_playwright  # noqa: E402

DEVICES = {
    "phone": dict(viewport={"width": 390, "height": 844}, device_scale_factor=3, has_touch=True),
    "ipad": dict(viewport={"width": 820, "height": 1180}, device_scale_factor=2, has_touch=True),
    "laptop": dict(viewport={"width": 1440, "height": 900}),
}

failures = []


passes = []


def check(label, cond, detail=""):
    if cond:
        passes.append(label)
    else:
        print(f"  FAIL {label}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        failures.append(label)


def open_book(context):
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BOOK)
    page.add_script_tag(path=CHECKS)
    global KEY, A_ID, A_T, B_ID, B_T, H_ID, H_T, H_SEARCH
    KEY = page.evaluate("BOOK.storagePrefix")
    # Three songs with chords, in page order: A, B, H (H is added to the session first)
    (A_ID, A_T), (B_ID, B_T), (H_ID, H_T) = page.evaluate(
        "[...document.querySelectorAll('.song')].filter(s => s.querySelector('.chord-line')"
        " && document.querySelectorAll(`.song[data-title=\"${s.dataset.title}\"]`).length == 1)"
        ".slice(0, 3).map(s => [s.id, s.dataset.title])")
    H_SEARCH = page.evaluate("t => t.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase()", H_T)
    return page, errors


def skipped_song_checks(context):
    """Off-screen songs are skipped (content-visibility) so big books don't crash
    phones. Fresh page, no checks.js: jumps must still land below the top bar."""
    page = context.new_page()
    page.goto(BOOK)
    page.wait_for_timeout(300)
    n = page.evaluate("document.querySelectorAll('.song').length")
    song = lambda i: f"document.querySelectorAll('.song')[{i}]"  # noqa: E731
    lyric_shown = lambda i: page.evaluate(  # noqa: E731
        f"{song(i)}.querySelector('.lyrics').checkVisibility({{contentVisibilityAuto: true}})")
    far = max(n - 10, 0)  # not the last songs: the page ends before they reach the top
    check("songs far off screen are skipped", not lyric_shown(far))
    for i in sorted({2, n // 2, far}):
        page.evaluate("scrollTo(0, 0)")
        page.evaluate(f"location.hash = {song(i)}.id")
        page.wait_for_timeout(500)
        top = page.evaluate(f"{song(i)}.getBoundingClientRect().top")
        check(f"jump to song {i + 1}/{n} lands below the top bar", 50 <= top <= 120, f"top={top}")
    page.evaluate("setTextScale(1.5)")
    page.wait_for_timeout(500)
    top = page.evaluate(f"{song(far)}.getBoundingClientRect().top")
    # Safari stays exactly (scroll-anchor.js); Chromium's own anchoring can drift
    # up to a screen. (Before skipping, A+ lost the place by thousands of px.)
    check("A+ keeps the song on screen", 0 <= top < page.viewport_size["height"], f"top={top}")
    page.evaluate("setTextScale(1)")
    page.evaluate("scrollTo(0, 0)")
    page.emulate_media(media="print")
    check("printing renders every song", lyric_shown(far))
    page.emulate_media(media="screen")
    page.evaluate("localStorage.clear()")
    page.close()


def layout_checks(page, label):
    a = page.evaluate("alignmentReport()")
    check(f"{label}: {a['chords']} chords / {a['lines']} lines exactly aligned", a["bad"] == 0, a["examples"])
    f = page.evaluate("fitReport()")
    return a, f


def run(engine_name, engine):
    print(f"\n===== {engine_name} =====")
    browser = engine.launch()
    for device, opts in DEVICES.items():
        print(f"--- {device}")
        context = browser.new_context(**opts)
        page, errors = open_book(context)
        name = f"{engine_name}-{device}"

        _, fit = layout_checks(page, "default")
        check(f"every song fits the width (font {fit['fontPx']})", fit["overflowing"] == 0, fit["examples"])
        check("page never scrolls sideways", not fit["pageScrollsSideways"])

        page.evaluate("columnsSetting.toggleGlobal()")
        _, fit2 = layout_checks(page, "2 columns")
        check(f"2 columns: every song fits (font {fit2['fontPx']})", fit2["overflowing"] == 0, fit2["examples"])
        if TAKE_SHOTS:
            page.evaluate(f"document.getElementById('{A_ID}').scrollIntoView()")
            page.screenshot(path=str(SHOTS / f"{name}-song-2cols.png"))
        page.evaluate("columnsSetting.toggleGlobal()")

        for scale in (0.4, 2.5):
            page.evaluate(f"setTextScale({scale})")
            _, fit3 = layout_checks(page, f"text {int(scale * 100)}%")
            check(f"text {int(scale * 100)}%: page never scrolls sideways", not fit3["pageScrollsSideways"])
        page.evaluate("setTextScale(1)")

        if TAKE_SHOTS:
            page.evaluate("scrollTo(0, 0)")
            page.screenshot(path=str(SHOTS / f"{name}-top.png"))
            page.evaluate(f"document.getElementById('{A_ID}').scrollIntoView()")
            page.screenshot(path=str(SHOTS / f"{name}-song.png"))

        bar = page.evaluate("""() => {
            const bar = document.querySelector('.topbar');
            return { overflow: bar.scrollWidth > bar.clientWidth,
                     search: document.querySelector('.topbar .search input').getBoundingClientRect().width,
                     autoscrollVisible: !!document.querySelector('.autoscroll').offsetParent };
        }""")
        check(f"top bar fits: search {bar['search']:.0f}px wide, autoscroll visible",
              not bar["overflow"] and bar["search"] >= 90 and bar["autoscrollVisible"], bar)
        if TAKE_SHOTS:
            page.screenshot(path=str(SHOTS / f"{name}-topbar.png"), clip={"x": 0, "y": 0, "width": opts["viewport"]["width"], "height": 70})

        if device == "phone":
            skipped_song_checks(context)
            session_checks(page, name)
            persistence_checks(page)
            autoscroll_checks(page)
            t = page.evaluate("transposeReport()")
            check(f"transpose x11: {t['checked']} chord positions; {t['moved']} shifted only where "
                  f"chords are 1 space apart; 0 moved needlessly",
                  t["unjustified"] == 0, t["unjustifiedExamples"])
            check("transpose back to 0 restores every line exactly", t["restored"])
            ui_checks(page, context, name)

        check("no JavaScript errors", not errors, errors)
        context.close()
    browser.close()


def ui_checks(page, context, name):
    meta = page.get_attribute('meta[name="viewport"]', "content")
    check("pinch-zoom allowed (no maximum-scale / user-scalable=no)",
          "maximum-scale" not in meta and "user-scalable" not in meta, meta)

    # Drawer
    page.click('[data-action="open-drawer"]')
    page.wait_for_timeout(350)
    box = page.locator("#drawer").bounding_box()
    check("menu opens inside the screen", page.evaluate("document.body.classList.contains('drawer-open')") and box["x"] >= 0)
    if TAKE_SHOTS:
        page.screenshot(path=str(SHOTS / f"{name}-drawer.png"))
    page.mouse.click(380, 400)  # backdrop, right of the drawer
    page.wait_for_timeout(350)
    check("tapping outside closes the menu", not page.evaluate("document.body.classList.contains('drawer-open')"))
    page.click('[data-action="open-drawer"]')
    page.keyboard.press("Escape")
    check("Escape closes the menu", not page.evaluate("document.body.classList.contains('drawer-open')"))

    # Folded section is unfolded when jumping into it from the menu
    page.evaluate("scrollTo(0, 0)")
    tag = page.evaluate("document.querySelector('details.tag-index[id^=\"tag-\"]').id")
    is_open = f"document.getElementById('{tag}').open"
    # Hakuna/cancionero albums start folded; pagano's language sections start open
    start = page.evaluate(is_open)
    page.click(f"#{tag} > summary")
    check("tapping a section header unfolds/folds it", page.evaluate(is_open) != start)
    if start:
        page.click(f"#{tag} > summary")  # leave it folded for the menu-link check
    else:
        page.click(f"#{tag} > summary")
        check("index section folds", not page.evaluate(is_open))
    page.click('[data-action="open-drawer"]')
    page.wait_for_timeout(350)
    page.click(f'#drawer a[href="#{tag}"]')
    page.wait_for_timeout(500)
    top = page.evaluate(f"document.getElementById('{tag}').getBoundingClientRect().top")
    check("menu link unfolds the section and shows it below the top bar",
          page.evaluate(is_open) and 50 <= top <= 120, f"top={top}")

    # Search
    page.evaluate("scrollTo(0, 0)")
    page.fill(".topbar .search input", H_SEARCH)
    n = page.locator(".topbar .search-result").count()
    check(f"accent-insensitive search shows results ({n})", n > 0)
    if TAKE_SHOTS:
        page.screenshot(path=str(SHOTS / f"{name}-search.png"))
    target = page.locator(".topbar .search-result").first.get_attribute("href")[1:]
    page.locator(".topbar .search-result").first.click()
    page.wait_for_timeout(500)
    top = page.evaluate(f"document.getElementById('{target}').getBoundingClientRect().top")
    check("picking a result jumps to the song and closes the search",
          page.locator(".topbar .search-results").is_hidden() and page.input_value(".topbar .search input") == ""
          and 50 <= top <= 120, f"top={top}")
    page.fill(".topbar .search input", "zzzzqq")
    check("no-match message", page.locator(".topbar .search-empty").is_visible())
    page.keyboard.press("Escape")

    # Per-song controls
    song = page.locator(".song").nth(1)
    song.locator('[data-action="toggle-chords"]').click()
    check("song chords toggle", song.locator(".chord-line").first.is_hidden())
    song.locator('[data-action="toggle-chords"]').click()
    song.locator('[data-action="toggle-columns"]').click()
    check("song columns toggle", song.locator(".lyrics").evaluate("e => getComputedStyle(e).columnCount") == "2")
    song.locator('[data-action="toggle-columns"]').click()
    song.locator('[data-action="transpose-up"]').click()
    song.locator('[data-action="transpose-value"], .transpose-value').first.click()
    check("tapping the transpose value resets it", song.locator(".transpose-value").inner_text() == "0")

    # Settings: remembered after reload
    page.click('[data-action="open-drawer"]')
    page.wait_for_timeout(350)
    size_before = page.evaluate("getComputedStyle(document.querySelector('.lyrics')).fontSize")
    page.click('[data-action="text-bigger"]')
    page.click('[data-action="cycle-theme"]')
    page.click('[data-action="cycle-theme"]')
    page.click('[data-action="toggle-all-chords"]')
    page.keyboard.press("Escape")
    page.reload()
    page.add_script_tag(path=CHECKS)
    after = page.evaluate("""() => ({
        scale: document.querySelector('.text-scale-value').textContent,
        theme: document.body.dataset.theme,
        chords: document.body.dataset.chords,
        bg: getComputedStyle(document.body).backgroundColor,
        size: getComputedStyle(document.querySelector('.lyrics')).fontSize,
    })""")
    check(f"text size, theme and chords remembered after reload {after}",
          after["scale"] == "110%" and after["theme"] == "dark" and after["chords"] == "hide"
          and parseFloat(after["size"]) > parseFloat(size_before))
    if TAKE_SHOTS:
        page.evaluate(f"document.getElementById('{A_ID}').scrollIntoView()")
        page.screenshot(path=str(SHOTS / f"{name}-dark.png"))
    page.evaluate("localStorage.clear()")

    # Print dialog
    page.click('[data-action="open-drawer"]')
    page.wait_for_timeout(350)
    page.click('[data-action="open-print"]')
    check("print dialog opens and menu closes",
          page.evaluate("document.getElementById('print-dialog').open")
          and not page.evaluate("document.body.classList.contains('drawer-open')"))
    page.click('#print-dialog button[value="cancel"]')
    check("print dialog cancels", not page.evaluate("document.getElementById('print-dialog').open"))


def autoscroll_checks(page):
    toggle = '[data-action="toggle-autoscroll"]'
    speed = lambda: page.inner_text(".autoscroll-speed")  # noqa: E731
    scroll_y = lambda: page.evaluate("scrollY")  # noqa: E731

    page.evaluate(f"document.getElementById('{A_ID}').scrollIntoView()")
    start_y = scroll_y()
    check("autoscroll shows default speed 3 and ▶", speed() == "3" and page.inner_text(toggle) == "▶")

    page.click(toggle)
    page.wait_for_timeout(1000)
    moved_slow = scroll_y() - start_y
    check(f"autoscroll starts (moved {moved_slow:.0f}px in 1s at speed 3) and shows ⏸",
          10 <= moved_slow <= 30 and page.inner_text(toggle) == "⏸")

    for _ in range(3):
        page.click('[data-action="autoscroll-faster"]')
    y = scroll_y()
    page.wait_for_timeout(1000)
    moved_fast = scroll_y() - y
    check(f"faster: speed 6 moves ~2x ({moved_fast:.0f}px/s)", speed() == "6" and moved_fast > moved_slow * 1.5)

    for _ in range(12):
        page.click('[data-action="autoscroll-slower"]')
    for _ in range(12):
        page.click('[data-action="autoscroll-faster"]')
    check("speed stays within 1..10", speed() == "10")
    for _ in range(6):
        page.click('[data-action="autoscroll-slower"]')  # 10 -> 4

    page.evaluate("scrollTo(0, 200)")  # a manual scroll / jump while running
    page.wait_for_timeout(500)
    y = scroll_y()
    check(f"continues from a manual scroll position ({y:.0f})", 200 < y < 240)

    page.click('[data-action="open-drawer"]')
    page.wait_for_timeout(300)
    y = scroll_y()
    page.wait_for_timeout(600)
    check("pauses while the menu is open", abs(scroll_y() - y) < 1)
    page.keyboard.press("Escape")
    page.wait_for_timeout(600)
    check("resumes after closing the menu", scroll_y() > y + 3)

    page.click(toggle)
    y = scroll_y()
    page.wait_for_timeout(600)
    check("stop stops scrolling", abs(scroll_y() - y) < 1 and page.inner_text(toggle) == "▶")

    page.reload()
    page.add_script_tag(path=CHECKS)
    check("speed remembered after reload", speed() == "4")

    page.evaluate("scrollTo(0, document.documentElement.scrollHeight - innerHeight - 30)")
    page.click(toggle)
    page.wait_for_timeout(2500)
    check("stops by itself at the end of the page", page.inner_text(toggle) == "▶")
    page.evaluate("localStorage.clear()")
    page.evaluate("scrollTo(0, 0)")


def session_checks(page, name):
    def titles():
        return page.eval_on_selector_all(".session-list a", "els => els.map(e => e.textContent)")

    def open_menu():
        if not page.evaluate("document.body.classList.contains('drawer-open')"):
            page.click('[data-action="open-drawer"]')
            page.wait_for_timeout(350)

    open_menu()
    first_in_menu = page.evaluate("document.querySelector('#drawer > :not(.drawer-header)').id")
    check("Sing Session is the first item in the menu", first_in_menu == "session")
    check("empty session shows the 'add songs' message",
          page.locator(".session-empty").is_visible() and titles() == []
          and page.locator('[data-action="session-clear"]').is_hidden())

    # Add from the session's own search: stays in the menu, box ready for the next song
    page.fill(".session-search input", H_SEARCH)
    page.locator(".session-search .search-result").first.click()
    check("adding from session search keeps the menu open and clears the box",
          page.evaluate("document.body.classList.contains('drawer-open')")
          and page.input_value(".session-search input") == ""
          and titles() == [H_T], titles())
    page.fill(".session-search input", H_SEARCH)
    page.locator(".session-search .search-result").first.click()
    check("the same song is never added twice", len(titles()) == 1)
    page.keyboard.press("Escape")  # clears the session search box only
    page.keyboard.press("Escape")  # closes the menu

    # Add from the song's own button
    # By id, not position: new songs change positions.
    for song_id in (A_ID, B_ID):
        page.locator(f"#{song_id}").locator('[data-action="session-toggle"]').click()
    button = page.locator("#" + A_ID).locator('[data-action="session-toggle"]')
    check("song button shows ✓ In session", button.inner_text() == "✓ In session")
    open_menu()
    check(f"session count and order {titles()}", page.inner_text(".session-count") == "(3)"
          and titles() == [H_T, A_T, B_T])
    if TAKE_SHOTS:
        page.screenshot(path=str(SHOTS / f"{name}-session.png"))

    # Reorder by dragging the handle
    rows = page.locator(".session-list li")
    handles = page.locator(".session-list .session-handle")

    def center(locator):
        box = locator.bounding_box()
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    def mouse_drag(handle_index, to_y, shot=None):
        x, y = center(handles.nth(handle_index))
        page.mouse.move(x, y)
        page.mouse.down()
        steps = 12
        for s in range(1, steps + 1):
            page.mouse.move(x, y + (to_y - y) * s / steps)
        page.wait_for_timeout(200)
        if shot and TAKE_SHOTS:
            page.screenshot(path=str(SHOTS / shot))
        page.mouse.up()
        page.wait_for_timeout(100)

    _, row1_y = center(rows.nth(1))
    mouse_drag(0, row1_y + 12, shot=f"{name}-session-dragging.png")
    check("drag first song below the second", titles() == [A_T, H_T, B_T], titles())
    top_y = rows.nth(0).bounding_box()["y"] + 4
    mouse_drag(2, top_y)
    check("drag last song to the top", titles() == [B_T, A_T, H_T], titles())
    x, y = center(handles.nth(1))
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.up()
    check("a tap on the handle without moving changes nothing",
          titles() == [B_T, A_T, H_T], titles())

    handles.nth(0).focus()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("ArrowDown")
    check("keyboard ↓ on the handle moves the song (focus follows it)",
          titles() == [A_T, H_T, B_T], titles())

    if name.startswith("chromium"):
        # Real touch input (Chrome's touch pipeline honours touch-action).
        cdp = page.context.new_cdp_session(page)

        def touch(kind, x, y):
            points = [] if kind == "touchEnd" else [{"x": x, "y": y}]
            cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})

        def touch_drag(x, y, to_y):
            touch("touchStart", x, y)
            for s in range(1, 16):
                touch("touchMove", x, y + (to_y - y) * s / 15)
            page.wait_for_timeout(150)
            touch("touchEnd", x, to_y)
            page.wait_for_timeout(150)

        x, y = center(handles.nth(0))
        last_bottom = rows.nth(2).bounding_box()
        touch_drag(x, y, last_bottom["y"] + last_bottom["height"] - 4)
        check("finger drag on the handle moves a song to the end",
              titles() == [H_T, B_T, A_T], titles())

        x, y = center(page.locator(".session-list a").nth(0))
        touch_drag(x, y, y + 120)
        check("a finger swipe on a title does not reorder",
              titles() == [H_T, B_T, A_T], titles())

    # Long session: holding a drag at the menu's bottom edge scrolls the menu
    if page.locator(".song").count() >= 40:  # small books can't make a long session
        saved = page.evaluate("[...session]")
        page.evaluate("""() => setSession([...document.querySelectorAll('.song')].slice(20, 40).map(s => s.id))""")
        page.evaluate("document.getElementById('drawer').scrollTop = 0")
        first = titles()[0]
        x, y = center(handles.nth(0))
        page.mouse.move(x, y)
        page.mouse.down()
        bottom = page.viewport_size["height"] - 10
        for s in range(1, 11):
            page.mouse.move(x, y + (bottom - y) * s / 10)
        page.wait_for_timeout(1500)
        scrolled = page.evaluate("document.getElementById('drawer').scrollTop")
        page.mouse.up()
        position = titles().index(first)
        check(f"dragging at the menu's edge scrolls it ({scrolled:.0f}px) and drops further down (position {position + 1}/20)",
              scrolled > 100 and position >= 10)
        page.evaluate(f"setSession({saved})".replace("'", '"'))
        page.evaluate("document.getElementById('drawer').scrollTop = 0")

    # Remove (✕ and the song's toggle)
    page.locator(f'.session-list li:has(a:text-is({json.dumps(H_T, ensure_ascii=False)})) [data-action="session-remove"]').click()
    check("✕ removes a song", len(titles()) == 2 and H_T not in titles(), titles())
    page.keyboard.press("Escape")
    button.click()
    check("tapping ✓ In session removes it", button.inner_text() == "+ Session")
    other = page.locator(f".song:not(#{A_ID}):not(#{B_ID}):not(#{H_ID})").last
    other.locator('[data-action="session-toggle"]').click()

    # Remembered after reload
    open_menu()
    before = titles()
    reload(page)
    open_menu()
    check(f"session remembered after reload {titles()}", titles() == before and len(before) == 2)

    # Jump to a session song
    target = page.locator(".session-list a").first.get_attribute("href")[1:]
    page.locator(".session-list a").first.click()
    page.wait_for_timeout(500)
    top = page.evaluate(f"document.getElementById('{target}').getBoundingClientRect().top")
    check("tapping a session song closes the menu and shows the song",
          not page.evaluate("document.body.classList.contains('drawer-open')") and 50 <= top <= 120, f"top={top}")

    # Clear (asks for confirmation)
    open_menu()
    page.once("dialog", lambda d: d.dismiss())
    page.click('[data-action="session-clear"]')
    check("cancelling the confirmation keeps the session", len(titles()) == 2)
    page.once("dialog", lambda d: d.accept())
    page.click('[data-action="session-clear"]')
    check("clear session empties it", titles() == [] and page.locator(".session-empty").is_visible())
    reload(page)
    check("cleared session stays empty after reload",
          page.evaluate(f"localStorage.getItem('{KEY}session')") == "[]")

    # Shared link replaces the session only, opens the menu, jumps to the first song.
    ids = page.evaluate("[...document.querySelectorAll('.song')].slice(1, 3).map(s => s.id)")
    page.evaluate(f"localStorage.setItem('{KEY}songs', '{{\"{ids[0]}\": {{\"transpose\": 2}}}}')")
    page.goto(page.url.split("#")[0].split("?")[0] + "?session=" + ",".join(ids) + ",missing")
    check("shared link replaces the session (unknown ids dropped)",
          page.evaluate(f"localStorage.getItem('{KEY}session')") == json.dumps(ids, separators=(",", ":")))
    check("shared link keeps song changes", "transpose" in page.evaluate(f"localStorage.getItem('{KEY}songs')"))
    check("shared link opens the menu and jumps to the first song",
          page.locator("#drawer").is_visible() and page.url.endswith("#" + ids[0]) and "?" not in page.url)
    page.evaluate("localStorage.clear()")
    page.goto(page.url.split("#")[0])
    page.add_script_tag(path=CHECKS)


def reload(page):
    page.reload()
    page.add_script_tag(path=CHECKS)


def persistence_checks(page):
    abba = "#" + page.evaluate("document.querySelector('.song .chord-line').closest('.song').id")
    second = page.locator(".song").nth(1)  # A ti te alabo
    third = page.locator(".song").nth(2)
    first_chord = lambda: page.inner_text(f"{abba} .chord-line")  # noqa: E731
    original_chord = first_chord()

    for _ in range(3):
        page.click(f'{abba} [data-action="transpose-up"]')
    transposed_chord = first_chord()
    second.locator('[data-action="toggle-chords"]').click()
    third.locator('[data-action="toggle-columns"]').click()

    reload(page)
    check(f"Abba Padre still +3 after reload ({original_chord} -> {first_chord()})",
          page.inner_text(f"{abba} .transpose-value") == "+3" and first_chord() == transposed_chord
          and transposed_chord != original_chord)
    check("per-song hidden chords remembered", second.locator(".chord-line").first.is_hidden())
    check("per-song 2 columns remembered",
          third.locator(".lyrics").evaluate("e => getComputedStyle(e).columnCount") == "2")
    a = page.evaluate("alignmentReport()")
    check("restored transposition keeps every chord aligned", a["bad"] == 0, a["examples"])

    # A book-wide chords toggle clears the per-song override, also after reload.
    page.click('[data-action="open-drawer"]')
    page.wait_for_timeout(350)
    page.click('[data-action="toggle-all-chords"]')
    page.click('[data-action="toggle-all-chords"]')
    page.keyboard.press("Escape")
    reload(page)
    check("book-wide chords toggle clears the saved per-song override",
          second.locator(".chord-line").first.is_visible())

    page.click('[data-action="open-drawer"]')
    page.wait_for_timeout(350)
    page.click('[data-action="reset-songs"]')
    page.keyboard.press("Escape")
    check("reset puts songs back immediately",
          page.inner_text(f"{abba} .transpose-value") == "0" and first_chord() == original_chord
          and third.locator(".lyrics").evaluate("e => getComputedStyle(e).columnCount") != "2")
    reload(page)
    saved = page.evaluate(f"localStorage.getItem('{KEY}songs')")
    check(f"reset is remembered after reload (saved: {saved})",
          page.inner_text(f"{abba} .transpose-value") == "0" and saved == "{}")
    page.evaluate("localStorage.clear()")
    reload(page)


def parseFloat(value):
    return float(str(value).replace("px", ""))


with sync_playwright() as p:
    run("chromium", p.chromium)
    run("webkit", p.webkit)

print(f"\n{len(passes)} passed, {len(failures)} failed")
print("FAILURES:", json.dumps(failures, ensure_ascii=False) if failures else "none")
