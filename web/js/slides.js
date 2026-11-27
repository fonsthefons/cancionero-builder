// Session slides: the session's lyrics (no chords) as big text on letter-landscape
// pages, one slide per page, to save as a PDF and import into PowerPoint / Slides.

const SLIDE_PAD = 0.4 * 96; // page margin in CSS px (1in = 96px)
// 10 lines at line-height 1.2 fill the page: the smallest text a lyric slide may use.
const SLIDE_MIN = ((8.5 - 0.8) * 96) / (10 * 1.2);
const SLIDE_MAX = SLIDE_MIN * 2.5; // a short song must not turn into a few huge words

// A song's lyrics, one array of {text, bold} per verse. Chord lines are dropped,
// and so are the "Intro: G D" label lines (their chords are inside the line).
function slideVerses(id) {
    return [...document.getElementById(id).querySelectorAll(".lyrics > .verse")].map((verse) =>
        [...verse.children].flatMap((el) => {
            if (el.classList.contains("chord-inline") || el.querySelector(".chord-inline")) return [];
            const text = el.matches(".line-pair, .lyric-line") ? lyricText(el) : "";
            return text.trim() ? [{ text: text.trim(), bold: el.classList.contains("bold") }] : [];
        })
    ).filter((lines) => lines.length);
}

function slideElement(verses, extraClass = "") {
    const slide = document.createElement("section");
    slide.className = "slide " + extraClass;
    slide.append(...verses.map((lines) => {
        const verse = Object.assign(document.createElement("div"), { className: "slide-verse" });
        verse.append(...lines.map(({ text, bold }) =>
            Object.assign(document.createElement("div"), { className: bold ? "slide-line bold" : "slide-line", textContent: text })));
        return verse;
    }));
    return slide;
}

// Does everything sit inside the page margins? (Checked on the children, not
// with scrollWidth/scrollHeight of the slide, which ignore the padding.)
function slideFits(slide) {
    const page = slide.getBoundingClientRect();
    return [...slide.children].every((verse) => verse.scrollWidth <= verse.clientWidth)
        && slide.lastElementChild.getBoundingClientRect().bottom <= page.bottom - SLIDE_PAD + 0.5;
}

// Measure off screen in a real slide (same CSS, so the same line breaks as in print).
function slideProbe(verses, extraClass) {
    const probe = slideElement(verses, extraClass);
    Object.assign(probe.style, { position: "fixed", left: "-10000px", top: "0" });
    document.body.append(probe);
    return probe;
}

// A page whose text would come out smaller than this is split: merely fitting at
// SLIDE_MIN made a dense 8-line verse look tiny next to the other pages.
const SLIDE_GOOD = SLIDE_MIN * 1.25;

function slideSize(verses) {
    const probe = slideProbe(verses);
    const size = slideFit(probe);
    probe.remove();
    return size;
}

// Whole verses per page while the text stays at least SLIDE_GOOD; a verse that
// is smaller on a page of its own is cut into the fewest even parts that reach it.
function slidePages(verses) {
    const pages = [];
    let page = [];
    for (const verse of verses) {
        if (page.length && slideSize([...page, verse]) >= SLIDE_GOOD) { page.push(verse); continue; }
        if (page.length) pages.push(page);
        let parts;
        for (let n = 1; n <= verse.length; n++) {
            parts = Array.from({ length: n }, (_, i) =>
                verse.slice(Math.round((i * verse.length) / n), Math.round(((i + 1) * verse.length) / n)));
            if (parts.every((part) => slideSize([part]) >= SLIDE_GOOD)) break;
        }
        pages.push(...parts.slice(0, -1).map((part) => [part]));
        page = [parts.at(-1)];
    }
    if (page.length) pages.push(page);
    return pages;
}

// The largest text that fits, set on the slide: on one line per lyric line if
// that is still at least SLIDE_GOOD, otherwise wrapped (a ~40-character line
// can't pass ~62px on one line, so bigger text means wrapping it).
function slideFit(slide) {
    const largest = () => {
        let low = 0, high = SLIDE_MAX;
        for (let i = 0; i < 12; i++) {
            const size = (low + high) / 2;
            slide.style.fontSize = size + "px";
            if (slideFits(slide)) low = size; else high = size;
        }
        return low;
    };
    slide.style.whiteSpace = "nowrap";
    let size = largest();
    if (size < SLIDE_GOOD) {
        slide.style.whiteSpace = "normal";
        size = largest();
    }
    slide.style.fontSize = size + "px";
    return size;
}

function slideSized(verses, extraClass = "") {
    const slide = slideProbe(verses, extraClass);
    slideFit(slide);
    Object.assign(slide.style, { position: "", left: "", top: "" });
    return slide;
}

onAction("session-slides", () => {
    setDrawerOpen(false);
    const slides = document.createElement("div");
    slides.className = "slides";
    // A psalm's fórmula comes first, then the psalm's own verses.
    for (const id of session) {
        const formula = sessionFormula(id);
        slides.append(slideSized([[{ text: songTitle(id), bold: true }]], "slide-title"));
        for (const song of formula ? [formula, id] : [id]) {
            slides.append(...slidePages(slideVerses(song)).map((page) => slideSized(page)));
        }
    }
    document.body.append(slides);

    // Letter landscape without margins, only while the slides are printed.
    const pageStyle = Object.assign(document.createElement("style"), {
        id: "slides-page",
        textContent: "@page { size: letter landscape; margin: 0 }",
    });
    document.head.append(pageStyle);
    document.body.dataset.slides = "";

    // afterprint also fires for the browser's own print preview being closed.
    window.addEventListener("afterprint", () => {
        slides.remove();
        pageStyle.remove();
        delete document.body.dataset.slides;
    }, { once: true });
    window.print();
});
