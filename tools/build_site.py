#!/usr/bin/env python3
"""Generate the static site's full HTML pages from content/ fragments.

Plain string templating, no dependencies, no server. Run this after editing
anything in content/ or after pulling new posts with lw_extract.py into
content/bci_cognition_enhancement/:

    python3 tools/build_site.py

Site structure:
    content/                       fragments (just the inner body content)
    index.html, timeline.html, writing.html, bci_cognition_enhancement/*.html
                                    generated full pages (safe to overwrite)
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")

SITE_NAME = "Elliot Callender"

NAV = [
    ("Home", "index.html"),
    ("Writing", "writing.html"),
    ("Timeline", "timeline.html"),
]

# sequence key -> (title, teaser, [(slug, title), ...]) in reading order
SEQUENCES = {
    "bci_cognition_enhancement": {
        "title": "BCI Cognition Enhancement",
        "teaser": "What technologies would create superintelligent humans?",
        "chapters": [
            ("bci-cognition-enhancement-is-possible", "BCI Cognition Enhancement is Possible"),
            ("not-prosthetics", "Not Prosthetics"),
            ("just-add-neurons", "Just Add Neurons"),
            ("beyond-hardcoded-evolutionary-psychology", "Beyond Hardcoded Evolutionary Psychology"),
            ("aligning-superintelligent-humans", "Aligning Superintelligent Humans"),
            ("working-memory-expansion", "Working Memory Expansion"),
            ("accelerated-skill-learning-via-dream-engineering-and", "Accelerated Skill Learning via Dream Engineering and Biofeedback"),
            ("telepathy-is-algorithmically-easy", "Telepathy Is (Algorithmically) Easy"),
            ("long-term-implants-need-to-be-stretchy", "Long-Term Implants Need To Be Stretchy"),
        ],
    },
}

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<link rel="stylesheet" href="{rel}styles.css">
</head>
<body>
<header>
<h1>{site_name}</h1>
<nav>
{nav}
</nav>
</header>
<hr>
<main>
{heading}{content}
{prevnext}</main>
<script src="{rel}js/footnotes.js" defer></script>
</body>
</html>
"""


def read_fragment(*parts: str) -> str:
    with open(os.path.join(CONTENT, *parts)) as f:
        return f.read().strip()


def render_nav(rel: str, current: str) -> str:
    links = []
    for label, href in NAV:
        target = rel + href
        if href == current:
            links.append(f"<strong>{label}</strong>")
        else:
            links.append(f'<a href="{target}">{label}</a>')
    return "\n".join(links)


def render_page(title: str, content: str, rel: str, current: str,
                 heading: str = "", prevnext: str = "") -> str:
    return PAGE.format(
        title=f"{title} — {SITE_NAME}" if title else SITE_NAME,
        rel=rel,
        site_name=SITE_NAME,
        nav=render_nav(rel, current),
        heading=heading,
        content=content,
        prevnext=prevnext,
    )


def write(path: str, html: str) -> None:
    full_path = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
    with open(full_path, "w") as f:
        f.write(html)
    print(f"wrote {path}")


def build_home() -> None:
    content = read_fragment("bio.html")
    html = render_page("", content, rel="", current="index.html")
    write("index.html", html)


def build_timeline() -> None:
    content = read_fragment("timeline.html")
    html = render_page("Timeline", content, rel="", current="timeline.html",
                        heading="<h2>Timeline</h2>\n")
    write("timeline.html", html)


def build_writing() -> None:
    items = []
    for key, seq in SEQUENCES.items():
        items.append(
            f'<li><a href="{key}/index.html">{seq["title"]}</a>'
            f'<div class="desc">{seq["teaser"]}</div></li>'
        )
    content = '<ul class="sequences">\n' + "\n".join(items) + "\n</ul>"
    html = render_page("Writing", content, rel="", current="writing.html",
                        heading="<h2>Writing</h2>\n")
    write("writing.html", html)


def build_sequence(key: str, seq: dict) -> None:
    cover = read_fragment(key, "cover.html")
    chapter_links = "\n".join(
        f'<li><a href="{slug}.html">{title}</a></li>'
        for slug, title in seq["chapters"]
    )
    content = cover + f'\n<ol class="chapters">\n{chapter_links}\n</ol>'
    html = render_page(seq["title"], content, rel="../", current="writing.html",
                        heading=f"<h2>{seq['title']}</h2>\n")
    write(f"{key}/index.html", html)

    chapters = seq["chapters"]
    for i, (slug, title) in enumerate(chapters):
        body = read_fragment(key, f"{slug}.html")
        prev_link = (
            f'<a href="{chapters[i-1][0]}.html">← {chapters[i-1][1]}</a>'
            if i > 0 else "<span></span>"
        )
        next_link = (
            f'<a href="{chapters[i+1][0]}.html">{chapters[i+1][1]} →</a>'
            if i < len(chapters) - 1 else "<span></span>"
        )
        prevnext = (
            f'<div class="prevnext">{prev_link}{next_link}</div>\n'
            f'<footer><a href="index.html">↑ {seq["title"]}</a></footer>\n'
        )
        html = render_page(title, body, rel="../", current="writing.html",
                            heading=f"<h2>{title}</h2>\n", prevnext=prevnext)
        write(f"{key}/{slug}.html", html)


def main() -> None:
    build_home()
    build_timeline()
    build_writing()
    for key, seq in SEQUENCES.items():
        build_sequence(key, seq)


if __name__ == "__main__":
    main()
