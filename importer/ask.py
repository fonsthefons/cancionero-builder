"""Asking questions in the terminal, and picking tags."""

from builder.tags import add_to_tags_file, label_for
from builder.text import slug

END_MARK = "END"


def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        print()
        answer = ""
    return answer or (default or "")


def ask_yes(prompt, default=False):
    answer = ask(f"{prompt} ({'Y/n' if default else 'y/N'})").lower()
    return default if not answer else answer.startswith(("y", "s"))


def ask_number(prompt, count, default=None, allow_zero=False):
    """A number between 1 and count (0 too if allow_zero); None if left empty without default."""
    low = 0 if allow_zero else 1
    while True:
        answer = ask(prompt, str(default) if default else None)
        if not answer:
            return None
        if answer.isdigit() and low <= int(answer) <= count:
            return int(answer)
        print(f"Please type a number between {low} and {count}.")


def read_pasted(what="the song (chords above the lyrics)"):
    print(f"Paste {what}. When done, type {END_MARK} on its own line (or press Ctrl-D):")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == END_MARK:
            break
        lines.append(line)
    return "\n".join(lines)


def ask_chord_line(line):
    return ask_yes(f'Is this a line of chords?  "{line.strip()}"', default=True)


# ---------- tags ----------

def parse_tag_answer(answer, choices):
    """'1 3, Navidad, Misa/Comunión' -> [(tag id, sub id or None, new tag label, new sub label)]
    or a string saying what's wrong. Numbers pick from `choices`; other text is a
    new tag ("Tag") or subtag ("Tag/Subtag")."""
    picked = []
    for part in answer.split(","):
        part = part.strip()
        if not part:
            continue
        words = part.split()
        if all(word.isdigit() for word in words):
            for word in words:
                if not 1 <= int(word) <= len(choices):
                    return f"there is no tag number {word}"
                tag_id, sub_id, _ = choices[int(word) - 1]
                picked.append((tag_id, sub_id, None, None))
            continue
        tag_text, _, sub_text = part.partition("/")
        tag_text, sub_text = tag_text.strip(), sub_text.strip()
        if not slug(tag_text) or (sub_text and not slug(sub_text)):
            return f'"{part}" isn\'t a tag name (use letters or digits)'
        picked.append((slug(tag_text), slug(sub_text) or None, label_for(tag_text), label_for(sub_text) if sub_text else None))
    return picked


def ask_tags(book, taxonomy, suggested=None):
    """Tags for a song: picked by number, or new ones typed in (added to the book's
    tags.yaml unless they're there already). Enter takes the suggested tag
    (e.g. the song's language). Returns {tag id: [subtag ids]}."""
    choices = taxonomy.choices()
    if book.strict_tags:  # only what tags.yaml allows: flat tags and subtags
        choices = [c for c in choices if c[1] is not None or taxonomy.tags[c[0]].is_flat]
    print("\nTags:")
    for number, (_, _, label) in enumerate(choices, start=1):
        print(f"  {number:2}  {label}")
    if not choices:
        print("  (none yet)")
    if not book.strict_tags:
        print("Pick numbers, and/or type new tags as  Tag  or  Tag/Subtag  (separate with commas).")
    default = next((str(n) for n, (tag_id, sub_id, _) in enumerate(choices, start=1)
                    if tag_id == suggested and sub_id is None), None)
    if suggested and not default and not book.strict_tags:
        default = label_for(suggested)
    while True:
        answer = ask("Tags (- for none)", default)
        if answer == "-":
            answer = ""
        picked = parse_tag_answer(answer, choices)
        if isinstance(picked, str):
            print(f"Sorry, {picked}.")
            continue
        new = [p for p in picked if p[2] is not None and (p[0] not in taxonomy.tags or (
            p[1] and p[1] not in taxonomy.tags[p[0]].subtags))]
        if new and book.strict_tags:
            print("This book only takes the tags listed (book.yaml strict_tags); pick numbers.")
            continue
        break

    tags = {}
    for tag_id, sub_id, tag_label, sub_label in picked:
        subtags = tags.setdefault(tag_id, [])
        if sub_id and sub_id not in subtags:
            subtags.append(sub_id)
        if tag_label is not None:
            existing = taxonomy.tags.get(tag_id)
            known_sub = sub_id is None or (existing is not None and sub_id in existing.subtags_in_file)
            if existing is None or not existing.in_file or not known_sub:
                add_to_tags_file(book.tags_file, tag_id, existing.label if existing else tag_label,
                                 sub_id, sub_label)
                print(f"New tag {tag_label + (' / ' + sub_label if sub_label else '')} added to tags.yaml.")
    return tags
