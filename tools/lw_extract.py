#!/usr/bin/env python3
"""Pull LessWrong post(s) into barebones HTML fragments.

Usage:
    python3 lw_extract.py <lesswrong-post-url-or-id> [output.html]
    python3 lw_extract.py <links.csv> [output-dir]

Queries the LessWrong GraphQL API for each post's rendered HTML, then
rewrites it into the same plain <p>/<a>/<i> style used elsewhere on this
site: no classes, no wrapper divs, footnotes renumbered sequentially with
plain anchor back-links.

For a single post: if no output path is given, the fragment is printed
to stdout.

For a CSV of posts: pass a path ending in .csv, one LessWrong URL (or
post id) per line -- extra columns are ignored, blank lines and lines
starting with # are skipped. Each post is written to <output-dir>/<slug>.html
(output-dir defaults to the current directory). Failures on individual
rows are reported but don't stop the rest of the batch.
"""
import csv
import os
import re
import sys
import json
import urllib.request

from bs4 import BeautifulSoup, NavigableString, Tag

GRAPHQL_URL = "https://www.lesswrong.com/graphql"

QUERY = """
query GetPost($id: String!) {
  post(input: {selector: {_id: $id}}) {
    result {
      _id
      title
      slug
      contents { html }
    }
  }
}
"""


def extract_post_id(url_or_id: str) -> str:
    # regular post: /posts/<id>/<slug>
    # sequence post: /s/<seqId>/p/<id>
    match = re.search(r"lesswrong\.com/(?:posts/|s/[A-Za-z0-9]+/p/)([A-Za-z0-9]+)", url_or_id)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", url_or_id):
        return url_or_id
    raise ValueError(f"Could not extract a post id from {url_or_id!r}")


def fetch_post(post_id: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"id": post_id}}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    result = data["data"]["post"]["result"]
    if result is None:
        raise RuntimeError(f"No post found for id {post_id!r}")
    return result


def renumber_footnotes(soup: BeautifulSoup) -> None:
    """Replace LessWrong's random-id footnotes with sequential 1..N ones.

    A footnote can be cited more than once (LessWrong reuses one footnote-content
    item across multiple inline refs, e.g. in tables); those refs share a single
    footnote number and the footnote gets one back-link per occurrence.
    """
    refs = soup.select("span.footnote-reference")
    items = soup.select("ol.footnotes > li.footnote-item")
    items_by_id = {item.get("id"): item for item in items}

    def target_of(ref: Tag):
        link = ref.find("a")
        return link["href"].lstrip("#") if link and link.has_attr("href") else None

    canonical: dict[str, int] = {}
    for target in map(target_of, refs):
        if target and target not in canonical:
            canonical[target] = len(canonical) + 1

    occurrence_count: dict[str, int] = {}
    for ref in refs:
        target = target_of(ref)
        n = canonical.get(target)
        if n is None:
            continue
        occurrence_count[target] = occurrence_count.get(target, 0) + 1
        occ = occurrence_count[target]
        ref_id = f"fnref{n}" if occ == 1 else f"fnref{n}-{occ}"

        new_sup = soup.new_tag("sup")
        new_a = soup.new_tag("a", href=f"#fn{n}", id=ref_id)
        new_a.string = str(n)
        new_sup.append(new_a)
        ref.replace_with(new_sup)

    old_ol = soup.select_one("ol.footnotes")
    if old_ol is None:
        return

    new_ol = soup.new_tag("ol")
    for old_id, n in sorted(canonical.items(), key=lambda kv: kv[1]):
        item = items_by_id.get(old_id)
        if item is None:
            continue
        content = item.select_one("div.footnote-content")
        back_link = item.select_one("span.footnote-back-link")
        if back_link:
            back_link.decompose()

        new_li = soup.new_tag("li", id=f"fn{n}")
        if content:
            for child in list(content.children):
                new_li.append(child.extract())
        for occ in range(1, occurrence_count.get(old_id, 1) + 1):
            ref_id = f"fnref{n}" if occ == 1 else f"fnref{n}-{occ}"
            back = soup.new_tag("a", href=f"#{ref_id}")
            back.string = " ↩"
            new_li.append(back)
        new_ol.append(new_li)

    old_ol.replace_with(new_ol)


ALLOWED_ATTRS = {
    "a": {"href", "id"},
    "li": {"id"},
    "img": {"src", "alt"},
}


def strip_attrs(soup: BeautifulSoup) -> None:
    for tag in soup.find_all(True):
        allowed = ALLOWED_ATTRS.get(tag.name, set())
        for attr in list(tag.attrs):
            if attr not in allowed:
                del tag[attr]


def unwrap_tags(soup: BeautifulSoup, names) -> None:
    for name in names:
        for tag in soup.find_all(name):
            tag.unwrap()


def clean_html(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")

    renumber_footnotes(soup)

    # figures just wrap a single img; drop the wrapper
    unwrap_tags(soup, ["figure", "u", "s"])

    strip_attrs(soup)

    # collapse stray spans left over after footnote handling
    for span in soup.find_all("span"):
        span.unwrap()

    for text_node in soup.find_all(string=re.compile("\xa0")):
        text_node.replace_with(NavigableString(text_node.replace("\xa0", " ")))

    top_level = [c for c in soup.contents if isinstance(c, Tag) or str(c).strip()]
    lines = []
    for node in top_level:
        s = str(node).strip()
        if s:
            lines.append(s)
    return "\n\n".join(lines) + "\n"


def read_csv_links(path: str) -> list:
    links = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            cell = row[0].strip()
            if not cell or cell.startswith("#"):
                continue
            links.append(cell)
    return links


def extract_one(url_or_id: str, output_path: str = None) -> None:
    post_id = extract_post_id(url_or_id)
    post = fetch_post(post_id)
    fragment = clean_html(post["contents"]["html"])

    print(f"Title: {post['title']}", file=sys.stderr)
    print(f"Slug: {post['slug']}", file=sys.stderr)

    if output_path:
        with open(output_path, "w") as f:
            f.write(fragment)
        print(f"Wrote {output_path}", file=sys.stderr)
    else:
        print(fragment)


def extract_batch(csv_path: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    links = read_csv_links(csv_path)
    failures = []
    for i, link in enumerate(links, start=1):
        print(f"[{i}/{len(links)}] {link}", file=sys.stderr)
        try:
            post_id = extract_post_id(link)
            post = fetch_post(post_id)
            fragment = clean_html(post["contents"]["html"])
            out_path = os.path.join(output_dir, f"{post['slug']}.html")
            with open(out_path, "w") as f:
                f.write(fragment)
            print(f"  -> {out_path} ({post['title']})", file=sys.stderr)
        except Exception as exc:
            print(f"  FAILED: {exc}", file=sys.stderr)
            failures.append(link)

    if failures:
        print(f"\n{len(failures)} of {len(links)} failed:", file=sys.stderr)
        for link in failures:
            print(f"  {link}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    arg = sys.argv[1]
    if arg.lower().endswith(".csv"):
        output_dir = sys.argv[2] if len(sys.argv) >= 3 else "."
        extract_batch(arg, output_dir)
    else:
        output_path = sys.argv[2] if len(sys.argv) >= 3 else None
        extract_one(arg, output_path)


if __name__ == "__main__":
    main()
