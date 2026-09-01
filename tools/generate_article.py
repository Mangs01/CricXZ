"""Generate a new CricXZ article safely from reviewed article-data JSON."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as xml_escape

sys.dont_write_bytecode = True

from validate_article_data import Finding, validate


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent

TEMPLATE_PATH = REPOSITORY_ROOT / "tools" / "templates" / "article-template.html.tpl"
NEWS_PATH = REPOSITORY_ROOT / "pages" / "news.html"
SEARCH_PATH = REPOSITORY_ROOT / "assets" / "js" / "search-data.js"
SITEMAP_PATH = REPOSITORY_ROOT / "sitemap.xml"
HOMEPAGE_PATH = REPOSITORY_ROOT / "index.html"
ARTICLE_DIRECTORY = REPOSITORY_ROOT / "articles"
IMAGE_DIRECTORY = REPOSITORY_ROOT / "assets" / "images" / "articles"

SITE_URL = "https://cricxz.com"
AUTHOR_NAME = "CricXZ Sports Desk"

ARTICLE_TYPE_LABELS = {
    "news": "News",
    "match-report": "Match Report",
    "rankings": "Rankings",
    "squad": "Squad",
    "feature": "Feature",
}

MARKERS = {
    "news": (
        "<!-- CRICXZ:NEWS-CARDS:START -->",
        "<!-- CRICXZ:NEWS-CARDS:END -->",
    ),
    "search": (
        "// CRICXZ:NEWS-ARTICLES:START",
        "// CRICXZ:NEWS-ARTICLES:END",
    ),
    "sitemap": (
        "<!-- CRICXZ:ARTICLE-URLS:START -->",
        "<!-- CRICXZ:ARTICLE-URLS:END -->",
    ),
    "homepage": (
        "<!-- CRICXZ:HOMEPAGE-NEWS:START -->",
        "<!-- CRICXZ:HOMEPAGE-NEWS:END -->",
    ),
}

TOKEN_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
H1_RE = re.compile(r"<h1(?:\s|>)", re.IGNORECASE)
TITLE_RE = re.compile(r"<title(?:\s|>)", re.IGNORECASE)
CANONICAL_RE = re.compile(
    r'<link\s+rel=["\']canonical["\']',
    re.IGNORECASE,
)
JSONLD_RE = re.compile(
    r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
LOCALHOST_RE = re.compile(r"localhost|127\.0\.0\.1|::1", re.IGNORECASE)

DEVELOPER_HEADER_RE = re.compile(
    r"<!DOCTYPE html>\s*<html lang=\"en\">\s*<!--.*?-->\s*",
    re.DOTALL,
)

OPTIONAL_BLOCKS = {
    "updated_meta": (
        "<!-- OPTIONAL UPDATED META: only after a genuine editorial/factual update. -->",
        "<!-- END OPTIONAL UPDATED META -->",
    ),
    "updated_date": (
        "<!-- OPTIONAL UPDATED DATE: omit when publication and modification dates match. -->",
        "<!-- END OPTIONAL UPDATED DATE -->",
    ),
    "article_type": (
        "<!-- OPTIONAL ARTICLE TYPE: remove when it adds no useful context. -->",
        "<!-- END OPTIONAL ARTICLE TYPE -->",
    ),
    "hero_caption": (
        "<!-- OPTIONAL HERO CAPTION: remove when no meaningful caption exists. -->",
        "<!-- END OPTIONAL HERO CAPTION -->",
    ),
    "source_cutoff": (
        "<!-- OPTIONAL FACTUAL CUTOFF: for evolving matches, rankings, squads,\n"
        "             injuries/status, or other rapidly changing information. -->",
        "<!-- END OPTIONAL FACTUAL CUTOFF -->",
    ),
    "related": (
        "<!-- OPTIONAL RELATED CONTENT: manually curate; remove section when unused. -->",
        "<!-- END OPTIONAL RELATED CONTENT -->",
    ),
}


class GeneratorError(Exception):
    """Expected generator blocker or write failure."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely generate one new CricXZ article."
    )
    parser.add_argument(
        "article_data",
        type=Path,
        help="path to one reviewed article-data JSON file",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and preview changes without writing; this is the default",
    )
    mode.add_argument(
        "--write",
        action="store_true",
        help="write the planned article and integration changes",
    )

    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"file does not exist: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"path is not a file: {path}")

    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read valid JSON from {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise TypeError(f"top-level JSON value must be an object: {path}")

    return data


def findings_summary(findings: list[Finding]) -> tuple[int, int]:
    errors = sum(level == "ERROR" for level, _, _ in findings)
    warnings = sum(level == "WARNING" for level, _, _ in findings)
    return errors, warnings


def require_string(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise GeneratorError(f"{field} must be a non-empty string.")
    return value


def parse_iso_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise GeneratorError(f"Invalid ISO 8601 datetime: {value}") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GeneratorError(f"Datetime requires timezone: {value}")

    return parsed


def visible_date(value: str) -> str:
    parsed = parse_iso_datetime(value)
    months = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}"


def text_escape(value: str) -> str:
    return html.escape(value, quote=False)


def attr_escape(value: str) -> str:
    return html.escape(value, quote=True)


def json_script_dumps(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, indent=2)
    rendered = rendered.replace("<", "\\u003c")
    rendered = rendered.replace("\u2028", "\\u2028")
    rendered = rendered.replace("\u2029", "\\u2029")
    return rendered


def remove_block(template: str, start: str, end: str) -> str:
    start_pos = template.find(start)
    end_pos = template.find(end)

    if start_pos == -1 or end_pos == -1 or end_pos < start_pos:
        raise GeneratorError(
            f"Template optional block markers are missing or malformed: {start}"
        )

    end_pos += len(end)

    if end_pos < len(template) and template[end_pos] == "\n":
        end_pos += 1

    return template[:start_pos] + template[end_pos:]


def strip_block_markers(template: str, start: str, end: str) -> str:
    if template.count(start) != 1 or template.count(end) != 1:
        raise GeneratorError(
            f"Template optional block markers are missing or duplicated: {start}"
        )
    if template.find(start) > template.find(end):
        raise GeneratorError(
            f"Template optional block markers are reversed: {start}"
        )

    return template.replace(start, "").replace(end, "")


def remove_developer_header(template: str) -> str:
    match = DEVELOPER_HEADER_RE.match(template)
    if not match:
        raise GeneratorError("Template developer header could not be identified.")

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        + template[match.end():]
    )


def render_sources(sources: list[dict[str, Any]]) -> str:
    rendered: list[str] = []

    for source in sources:
        label = source["label"]
        url = source["url"]

        rendered.append(
            '            <li>\n'
            f'              <a href="{attr_escape(url)}" '
            'rel="noopener noreferrer">'
            f"{text_escape(label)}</a>\n"
            "            </li>"
        )

    return "\n".join(rendered)


def related_href(url: str) -> str:
    if url.startswith("articles/"):
        return url[len("articles/"):]
    if url.startswith("pages/"):
        return "../" + url
    raise GeneratorError(f"Unsupported related article path: {url}")


def render_related(items: list[dict[str, Any]]) -> str:
    rendered: list[str] = []

    for item in items:
        href = related_href(item["url"])
        title = text_escape(item["title"])
        summary = item.get("summary")

        lines = [
            f'        <a href="{attr_escape(href)}" class="related-card">',
            f"          <h3>{title}</h3>",
        ]

        if isinstance(summary, str) and summary.strip():
            lines.append(f"          <p>{text_escape(summary)}</p>")

        lines.extend(
            [
                "          <span>Read More &rarr;</span>",
                "        </a>",
            ]
        )
        rendered.append("\n".join(lines))

    return "\n".join(rendered)


def build_json_ld(
    data: dict[str, Any],
    canonical_url: str,
    hero_image_url: str,
    effective_modified: str,
) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": data["headline"],
        "description": data["metaDescription"],
        "image": {
            "@type": "ImageObject",
            "url": hero_image_url,
            "width": data["heroImageWidth"],
            "height": data["heroImageHeight"],
        },
        "datePublished": data["publicationDatetime"],
        "dateModified": effective_modified,
        "author": {
            "@type": "Organization",
            "name": AUTHOR_NAME,
            "url": f"{SITE_URL}/",
        },
        "publisher": {
            "@type": "Organization",
            "name": "CricXZ",
            "url": f"{SITE_URL}/",
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": canonical_url,
        },
    }


def replace_json_ld(template: str, payload: dict[str, Any]) -> str:
    matches = list(JSONLD_RE.finditer(template))
    if len(matches) != 1:
        raise GeneratorError(
            f"Template must contain exactly one JSON-LD block; found {len(matches)}."
        )

    json_text = json_script_dumps(payload)
    replacement = (
        '<script type="application/ld+json">\n'
        + json_text
        + "\n  </script>"
    )

    match = matches[0]
    return template[:match.start()] + replacement + template[match.end():]


def render_article(data: dict[str, Any], derived: dict[str, Any]) -> str:
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GeneratorError(f"Could not read article template: {exc}") from exc

    template = template.replace("\r\n", "\n").replace("\r", "\n")
    template = remove_developer_header(template)

    if data.get("modifiedDatetime"):
        template = strip_block_markers(
            template,
            *OPTIONAL_BLOCKS["updated_meta"],
        )
        template = strip_block_markers(
            template,
            *OPTIONAL_BLOCKS["updated_date"],
        )
    else:
        template = remove_block(
            template,
            *OPTIONAL_BLOCKS["updated_meta"],
        )
        template = remove_block(
            template,
            *OPTIONAL_BLOCKS["updated_date"],
        )

    template = strip_block_markers(
        template,
        *OPTIONAL_BLOCKS["article_type"],
    )

    if data.get("heroImageCaption"):
        template = strip_block_markers(
            template,
            *OPTIONAL_BLOCKS["hero_caption"],
        )
    else:
        template = remove_block(
            template,
            *OPTIONAL_BLOCKS["hero_caption"],
        )

    if data.get("sourceCutoff"):
        template = strip_block_markers(
            template,
            *OPTIONAL_BLOCKS["source_cutoff"],
        )
    else:
        template = remove_block(
            template,
            *OPTIONAL_BLOCKS["source_cutoff"],
        )

    related = data.get("relatedArticles") or []
    if related:
        template = strip_block_markers(
            template,
            *OPTIONAL_BLOCKS["related"],
        )
    else:
        template = remove_block(
            template,
            *OPTIONAL_BLOCKS["related"],
        )

    json_ld = build_json_ld(
        data,
        derived["canonical_url"],
        derived["hero_image_url"],
        derived["effective_modified"],
    )
    template = replace_json_ld(template, json_ld)

    # Tokens used in both HTML text and attribute contexts need
    # explicit attribute-safe replacement before the one-pass renderer.
    template = template.replace(
        'content="{{SEO_TITLE}} | CricXZ"',
        f'content="{attr_escape(data["seoTitle"])} | CricXZ"',
    )
    template = template.replace(
        'content="{{CATEGORY}}"',
        f'content="{attr_escape(data["categoryLabel"])}"',
    )
    template = template.replace(
        'content="{{AUTHOR_NAME}}"',
        f'content="{attr_escape(AUTHOR_NAME)}"',
    )

    raw_values = {
        "{{ARTICLE_BODY}}": data["articleBodyHtml"],
        "{{SOURCE_LIST}}": render_sources(data["sources"]),
        "{{RELATED_CONTENT}}": render_related(related),
    }

    text_values = {
        "{{SEO_TITLE}}": text_escape(data["seoTitle"]),
        "{{CATEGORY}}": text_escape(data["categoryLabel"]),
        "{{ARTICLE_TYPE}}": text_escape(derived["article_type_label"]),
        "{{ARTICLE_HEADLINE}}": text_escape(data["headline"]),
        "{{ARTICLE_DECK}}": text_escape(data["deck"]),
        "{{PUBLICATION_DATE_VISIBLE}}": text_escape(
            derived["publication_date_visible"]
        ),
        "{{MODIFIED_DATE_VISIBLE}}": text_escape(
            derived["modified_date_visible"]
        ),
        "{{AUTHOR_NAME}}": text_escape(AUTHOR_NAME),
        "{{HERO_IMAGE_CAPTION}}": text_escape(
            data.get("heroImageCaption", "")
        ),
        "{{SOURCE_CUTOFF}}": text_escape(data.get("sourceCutoff", "")),
    }

    attribute_values = {
        "{{META_DESCRIPTION}}": attr_escape(data["metaDescription"]),
        "{{CANONICAL_URL}}": attr_escape(derived["canonical_url"]),
        "{{PUBLICATION_DATETIME}}": attr_escape(
            data["publicationDatetime"]
        ),
        "{{MODIFIED_DATETIME}}": attr_escape(
            derived["effective_modified"]
        ),
        "{{HERO_IMAGE_PATH}}": attr_escape(derived["hero_image_article_path"]),
        "{{HERO_IMAGE_URL}}": attr_escape(derived["hero_image_url"]),
        "{{HERO_IMAGE_ALT}}": attr_escape(data["heroImageAlt"]),
        "{{HERO_IMAGE_WIDTH}}": str(data["heroImageWidth"]),
        "{{HERO_IMAGE_HEIGHT}}": str(data["heroImageHeight"]),
    }

    replacements: dict[str, str] = {}
    replacements.update(text_values)
    replacements.update(attribute_values)
    replacements.update(raw_values)

    original_template = template

    def token_callback(match: re.Match[str]) -> str:
        token = match.group(0)
        if token not in replacements:
            raise GeneratorError(f"Unknown or unresolved template token: {token}")
        return replacements[token]

    rendered = TOKEN_RE.sub(token_callback, original_template)

    if TOKEN_RE.search(rendered):
        raise GeneratorError("Rendered article contains unresolved template tokens.")

    return rendered.rstrip() + "\n"


def derive(data: dict[str, Any]) -> dict[str, Any]:
    slug = data["slug"]
    filename = data["heroImageFilename"]

    publication = data["publicationDatetime"]
    effective_modified = data.get("modifiedDatetime") or publication

    return {
        "article_relative": f"articles/{slug}.html",
        "article_path": ARTICLE_DIRECTORY / f"{slug}.html",
        "canonical_url": f"{SITE_URL}/articles/{slug}.html",
        "hero_image_fs": IMAGE_DIRECTORY / filename,
        "hero_image_article_path": f"../assets/images/articles/{filename}",
        "hero_image_url": f"{SITE_URL}/assets/images/articles/{filename}",
        "news_url": f"../articles/{slug}.html",
        "news_image": f"../assets/images/articles/{filename}",
        "search_url": f"articles/{slug}.html",
        "sitemap_loc": f"{SITE_URL}/articles/{slug}.html",
        "homepage_url": f"articles/{slug}.html",
        "homepage_image": f"assets/images/articles/{filename}",
        "publication_date_visible": visible_date(publication),
        "effective_modified": effective_modified,
        "modified_date_visible": visible_date(effective_modified),
        "sitemap_lastmod": parse_iso_datetime(
            effective_modified
        ).date().isoformat(),
        "article_type_label": ARTICLE_TYPE_LABELS[data["articleType"]],
        "card_headline": data.get("cardHeadline") or data["headline"],
        "card_summary": data.get("cardSummary") or data["deck"],
        "categories": " ".join(data["filterCategories"]),
        "homepage_featured": data.get("homepageFeatured", False),
    }


def render_news_card(data: dict[str, Any], d: dict[str, Any]) -> str:
    return (
        f'<a href="{attr_escape(d["news_url"])}" class="news-card" '
        f'data-category="{attr_escape(d["categories"])}">\n'
        f'  <img src="{attr_escape(d["news_image"])}" '
        f'alt="{attr_escape(data["heroImageAlt"])}">\n'
        '  <div class="news-content">\n'
        f'    <span class="news-tag">{text_escape(data["categoryLabel"])}</span>\n'
        f'    <h3>{text_escape(d["card_headline"])}</h3>\n'
        f'    <p>{text_escape(d["card_summary"])}</p>\n'
        '    <span class="read-more">Read More &rarr;</span>\n'
        "  </div>\n"
        "</a>"
    )


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_search_entry(d: dict[str, Any]) -> str:
    return (
        "{\n"
        f"    title: {js_string(d['card_headline'])},\n"
        '    type: "News",\n'
        f"    url: {js_string(d['search_url'])}\n"
        "},"
    )


def render_sitemap_entry(d: dict[str, Any]) -> str:
    return (
        "<url>\n"
        f"  <loc>{xml_escape(d['sitemap_loc'])}</loc>\n"
        f"  <lastmod>{xml_escape(d['sitemap_lastmod'])}</lastmod>\n"
        "</url>"
    )


def render_homepage_card(
    data: dict[str, Any],
    d: dict[str, Any],
) -> str:
    return (
        '<div class="news-card">\n'
        f'  <img src="{attr_escape(d["homepage_image"])}" '
        f'alt="{attr_escape(data["heroImageAlt"])}">\n'
        f'  <h3>{text_escape(d["card_headline"])}</h3>\n'
        f'  <p>{text_escape(d["card_summary"])}</p>\n'
        f'  <a href="{attr_escape(d["homepage_url"])}">'
        'Read More &rarr;</a>\n'
        '</div>'
    )


def read_utf8_bytes(path: Path) -> bytes:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise GeneratorError(f"Could not read target {path}: {exc}") from exc

    if raw.startswith(b"\xef\xbb\xbf"):
        raise GeneratorError(f"UTF-8 BOM is not supported for target: {path}")

    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GeneratorError(f"Target is not valid UTF-8: {path}") from exc

    return raw


def validate_marker(text: str, marker_key: str) -> tuple[str, str]:
    start, end = MARKERS[marker_key]

    if text.count(start) != 1 or text.count(end) != 1:
        raise GeneratorError(
            f"{marker_key} marker pair must appear exactly once."
        )

    if text.find(start) > text.find(end):
        raise GeneratorError(f"{marker_key} marker pair is reversed.")

    return start, end


def marker_newline(raw: bytes, start: str) -> bytes:
    marker = start.encode("utf-8")
    pos = raw.find(marker)

    if pos == -1:
        raise GeneratorError(f"Could not locate insertion marker: {start}")

    after = pos + len(marker)

    if raw[after:after + 2] == b"\r\n":
        return b"\r\n"
    if raw[after:after + 1] == b"\n":
        return b"\n"
    if raw[after:after + 1] == b"\r":
        return b"\r"

    before = raw[:pos]
    crlf = before.rfind(b"\r\n")
    lf = before.rfind(b"\n")

    if crlf >= lf - 1 and crlf != -1:
        return b"\r\n"

    return b"\n"


def insert_after_marker(
    raw: bytes,
    marker_key: str,
    generated: str,
) -> bytes:
    text = raw.decode("utf-8")
    start, _ = validate_marker(text, marker_key)

    marker_bytes = start.encode("utf-8")
    pos = raw.find(marker_bytes)
    end = pos + len(marker_bytes)

    newline = marker_newline(raw, start)
    normalized = generated.replace("\r\n", "\n").replace("\r", "\n")
    generated_bytes = normalized.replace(
        "\n", newline.decode("ascii")
    ).encode("utf-8")

    return raw[:end] + newline + generated_bytes + raw[end:]


def assert_safe_path(path: Path, allowed_parent: Path) -> None:
    resolved = path.resolve()
    parent = allowed_parent.resolve()

    try:
        resolved.relative_to(parent)
    except ValueError as exc:
        raise GeneratorError(
            f"Planned path resolves outside approved location: {path}"
        ) from exc


def check_duplicates(
    data: dict[str, Any],
    d: dict[str, Any],
    originals: dict[Path, bytes],
) -> dict[str, str]:
    result: dict[str, str] = {}

    if d["article_path"].exists():
        raise GeneratorError(
            f"Article output already exists: {d['article_relative']}"
        )
    result["Article file"] = "CLEAR"

    news = originals[NEWS_PATH].decode("utf-8")
    search = originals[SEARCH_PATH].decode("utf-8")
    sitemap = originals[SITEMAP_PATH].decode("utf-8")
    homepage = originals[HOMEPAGE_PATH].decode("utf-8")

    existing_article_files = sorted(
        ARTICLE_DIRECTORY.glob("*.html"),
        key=lambda path: str(path).lower(),
    )

    for article_file in existing_article_files:
        try:
            article_text = article_file.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise GeneratorError(
                f"Could not read existing article as UTF-8: {article_file}"
            ) from exc

        if d["canonical_url"] in article_text:
            raise GeneratorError(
                f"Canonical URL already exists in article file: "
                f"{article_file.relative_to(REPOSITORY_ROOT)}"
            )


    combined = "\n".join((news, search, sitemap, homepage))

    if d["canonical_url"] in combined:
        raise GeneratorError(
            f"Canonical URL already exists in publishing targets: "
            f"{d['canonical_url']}"
        )
    result["Canonical URL"] = "CLEAR"

    if d["news_url"] in news:
        raise GeneratorError(f"News URL already exists: {d['news_url']}")
    result["News URL"] = "CLEAR"

    if d["search_url"] in search:
        raise GeneratorError(f"Search URL already exists: {d['search_url']}")
    result["Search URL"] = "CLEAR"

    if d["sitemap_loc"] in sitemap:
        raise GeneratorError(f"Sitemap location already exists: {d['sitemap_loc']}")
    result["Sitemap loc"] = "CLEAR"

    if d["homepage_featured"]:
        if d["homepage_url"] in homepage:
            raise GeneratorError(
                f"Homepage URL already exists: {d['homepage_url']}"
            )
        result["Homepage URL"] = "CLEAR"
    else:
        result["Homepage URL"] = "NOT APPLICABLE"

    return result


def extract_json_ld(article: str) -> dict[str, Any]:
    matches = JSONLD_RE.findall(article)
    if len(matches) != 1:
        raise GeneratorError(
            f"Rendered article must contain exactly one JSON-LD block; "
            f"found {len(matches)}."
        )

    try:
        value = json.loads(matches[0])
    except json.JSONDecodeError as exc:
        raise GeneratorError(f"Rendered JSON-LD is invalid: {exc}") from exc

    if not isinstance(value, dict):
        raise GeneratorError("Rendered JSON-LD must be an object.")

    return value


def article_sanity(
    article: str,
    data: dict[str, Any],
    d: dict[str, Any],
) -> None:
    if len(H1_RE.findall(article)) != 1:
        raise GeneratorError("Rendered article must contain exactly one H1.")

    if len(TITLE_RE.findall(article)) != 1:
        raise GeneratorError("Rendered article must contain exactly one title.")

    if len(CANONICAL_RE.findall(article)) != 1:
        raise GeneratorError(
            "Rendered article must contain exactly one canonical link."
        )

    if TOKEN_RE.search(article):
        raise GeneratorError("Rendered article contains unresolved template token.")

    if "CricXZ V1 article template: developer source" in article:
        raise GeneratorError("Template developer header remains in article.")

    if "<!-- OPTIONAL " in article or "<!-- END OPTIONAL " in article:
        raise GeneratorError("Optional template-control comments remain.")

    if LOCALHOST_RE.search(article):
        raise GeneratorError("Rendered article contains localhost data.")

    canonical = (
        f'<link rel="canonical" href="{attr_escape(d["canonical_url"])}">'
    )
    if canonical not in article:
        raise GeneratorError("Rendered canonical link does not match derived URL.")

    expected_og = (
        f'<meta property="og:url" content="{attr_escape(d["canonical_url"])}">'
    )
    if expected_og not in article:
        raise GeneratorError("Rendered og:url does not match canonical.")

    if "../pages/news.html" not in article or "Back to All News" not in article:
        raise GeneratorError("Back to All News link is missing.")

    if 'class="article-sources"' not in article:
        raise GeneratorError("Required sources section is missing.")

    if (
        f'src="{attr_escape(d["hero_image_article_path"])}"'
        not in article
    ):
        raise GeneratorError("Hero image path is inconsistent.")

    json_ld = extract_json_ld(article)

    if json_ld.get("mainEntityOfPage", {}).get("@id") != d["canonical_url"]:
        raise GeneratorError("JSON-LD mainEntityOfPage is inconsistent.")

    image = json_ld.get("image")
    if not isinstance(image, dict):
        raise GeneratorError("JSON-LD image must be an ImageObject.")

    if image.get("url") != d["hero_image_url"]:
        raise GeneratorError("JSON-LD hero image URL is inconsistent.")

    if image.get("width") != data["heroImageWidth"]:
        raise GeneratorError("JSON-LD image width is inconsistent.")

    if image.get("height") != data["heroImageHeight"]:
        raise GeneratorError("JSON-LD image height is inconsistent.")

    if json_ld.get("datePublished") != data["publicationDatetime"]:
        raise GeneratorError("JSON-LD datePublished is inconsistent.")

    if json_ld.get("dateModified") != d["effective_modified"]:
        raise GeneratorError("JSON-LD dateModified is inconsistent.")

    author = json_ld.get("author")
    if not isinstance(author, dict) or author.get("name") != AUTHOR_NAME:
        raise GeneratorError("JSON-LD author is inconsistent.")

    if f"By {text_escape(AUTHOR_NAME)}" not in article:
        raise GeneratorError("Visible article author is inconsistent.")

    body = data["articleBodyHtml"]
    if article.count(body) != 1:
        raise GeneratorError(
            "Raw articleBodyHtml was not preserved exactly once."
        )


def integration_sanity(
    outputs: dict[Path, bytes],
    originals: dict[Path, bytes],
    d: dict[str, Any],
) -> None:
    news = outputs[NEWS_PATH].decode("utf-8")
    search = outputs[SEARCH_PATH].decode("utf-8")
    sitemap = outputs[SITEMAP_PATH].decode("utf-8")

    validate_marker(news, "news")
    validate_marker(search, "search")
    validate_marker(sitemap, "sitemap")

    if news.count(d["news_url"]) != 1:
        raise GeneratorError("Generated News URL must appear exactly once.")

    if search.count(d["search_url"]) != 1:
        raise GeneratorError("Generated search URL must appear exactly once.")

    if sitemap.count(d["sitemap_loc"]) != 1:
        raise GeneratorError("Generated sitemap location must appear exactly once.")

    if "const searchData = [" not in search or "];" not in search:
        raise GeneratorError("Search-data array structure appears damaged.")

    try:
        import xml.etree.ElementTree as ET

        ET.fromstring(sitemap)
    except Exception as exc:
        raise GeneratorError(f"Generated sitemap XML is invalid: {exc}") from exc

    homepage_original = originals[HOMEPAGE_PATH]

    if d["homepage_featured"]:
        homepage = outputs[HOMEPAGE_PATH].decode("utf-8")
        validate_marker(homepage, "homepage")
        if homepage.count(d["homepage_url"]) != 1:
            raise GeneratorError(
                "Generated homepage URL must appear exactly once."
            )
    else:
        if outputs[HOMEPAGE_PATH] != homepage_original:
            raise GeneratorError(
                "Homepage changed even though homepageFeatured is false."
            )
        homepage = homepage_original.decode("utf-8")
        validate_marker(homepage, "homepage")
        if d["homepage_url"] in homepage:
            raise GeneratorError(
                "Generated article URL unexpectedly exists on homepage."
            )


def prepare_plan(
    data: dict[str, Any],
) -> tuple[
    dict[str, Any],
    dict[Path, bytes],
    dict[Path, bytes],
    dict[str, str],
]:
    d = derive(data)

    assert_safe_path(d["article_path"], ARTICLE_DIRECTORY)
    assert_safe_path(d["hero_image_fs"], IMAGE_DIRECTORY)

    if not d["hero_image_fs"].is_file():
        raise GeneratorError(
            f"Hero image file is missing: {d['hero_image_fs']}"
        )

    originals = {
        NEWS_PATH: read_utf8_bytes(NEWS_PATH),
        SEARCH_PATH: read_utf8_bytes(SEARCH_PATH),
        SITEMAP_PATH: read_utf8_bytes(SITEMAP_PATH),
        HOMEPAGE_PATH: read_utf8_bytes(HOMEPAGE_PATH),
    }

    for path, marker_key in (
        (NEWS_PATH, "news"),
        (SEARCH_PATH, "search"),
        (SITEMAP_PATH, "sitemap"),
        (HOMEPAGE_PATH, "homepage"),
    ):
        validate_marker(originals[path].decode("utf-8"), marker_key)

    duplicates = check_duplicates(data, d, originals)

    article = render_article(data, d)
    article_sanity(article, data, d)

    outputs = dict(originals)
    outputs[NEWS_PATH] = insert_after_marker(
        originals[NEWS_PATH],
        "news",
        render_news_card(data, d),
    )
    outputs[SEARCH_PATH] = insert_after_marker(
        originals[SEARCH_PATH],
        "search",
        render_search_entry(d),
    )
    outputs[SITEMAP_PATH] = insert_after_marker(
        originals[SITEMAP_PATH],
        "sitemap",
        render_sitemap_entry(d),
    )

    if d["homepage_featured"]:
        outputs[HOMEPAGE_PATH] = insert_after_marker(
            originals[HOMEPAGE_PATH],
            "homepage",
            render_homepage_card(data, d),
        )

    outputs[d["article_path"]] = article.encode("utf-8")

    integration_sanity(outputs, originals, d)

    if not d["homepage_featured"]:
        outputs.pop(HOMEPAGE_PATH)

    return d, originals, outputs, duplicates


def transaction_artifact_paths(
    targets: list[Path],
    transaction_id: str,
) -> tuple[dict[Path, Path], dict[Path, Path]]:
    temps: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}

    for target in targets:
        temps[target] = target.with_name(
            f".{target.name}.cricxz-{transaction_id}.tmp"
        )
        backups[target] = target.with_name(
            f".{target.name}.cricxz-{transaction_id}.bak"
        )

    return temps, backups


def write_and_sync(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def cleanup_paths(paths: list[Path]) -> list[str]:
    failures: list[str] = []

    for path in paths:
        if not path.exists():
            continue
        try:
            path.unlink()
        except OSError as exc:
            failures.append(f"{path}: {exc}")

    return failures


def find_stale_transaction_artifacts(
    targets: list[Path],
) -> list[Path]:
    stale: list[Path] = []

    for target in targets:
        patterns = (
            f".{target.name}.cricxz-*.tmp",
            f".{target.name}.cricxz-*.bak",
        )

        for pattern in patterns:
            stale.extend(target.parent.glob(pattern))

    return sorted(set(stale), key=lambda path: str(path).lower())


def transactional_write(
    outputs: dict[Path, bytes],
    originals: dict[Path, bytes],
) -> None:
    targets = list(outputs.keys())

    stale_artifacts = find_stale_transaction_artifacts(targets)
    if stale_artifacts:
        raise GeneratorError(
            "Stale transaction artifact(s) found. "
            "Resolve them before writing: "
            + ", ".join(str(path) for path in stale_artifacts)
        )

    transaction_id = uuid.uuid4().hex
    temps, backups = transaction_artifact_paths(targets, transaction_id)

    artifact_paths = list(temps.values()) + list(backups.values())
    collisions = [path for path in artifact_paths if path.exists()]
    if collisions:
        raise GeneratorError(
            "Transaction artifact already exists: "
            + ", ".join(str(path) for path in collisions)
        )

    prepared_temps: list[Path] = []
    installed: list[Path] = []
    backed_up: list[Path] = []

    try:
        for target in targets:
            write_and_sync(temps[target], outputs[target])
            prepared_temps.append(temps[target])

        for target in targets:
            if target in originals:
                os.replace(target, backups[target])
                backed_up.append(target)

            os.replace(temps[target], target)
            installed.append(target)

        for target, expected in outputs.items():
            try:
                actual = target.read_bytes()
            except OSError as exc:
                raise GeneratorError(
                    f"Could not verify installed target {target}: {exc}"
                ) from exc

            if actual != expected:
                raise GeneratorError(
                    f"Installed target does not match planned bytes: {target}"
                )

    except Exception as exc:
        rollback_errors: list[str] = []

        for target in reversed(installed):
            try:
                if target.exists():
                    target.unlink()
            except OSError as rollback_exc:
                rollback_errors.append(
                    f"Could not remove installed target {target}: "
                    f"{rollback_exc}"
                )

        for target in reversed(backed_up):
            backup = backups[target]
            if not backup.exists():
                rollback_errors.append(
                    f"Backup missing during rollback: {backup}"
                )
                continue

            try:
                os.replace(backup, target)
            except OSError as rollback_exc:
                rollback_errors.append(
                    f"Could not restore {target}: {rollback_exc}"
                )

        cleanup_errors = cleanup_paths(
            list(temps.values()) + list(backups.values())
        )
        rollback_errors.extend(
            f"Cleanup failure: {message}" for message in cleanup_errors
        )

        if rollback_errors:
            raise GeneratorError(
                "Write failed and rollback was incomplete. "
                f"Original error: {exc}. "
                + " | ".join(rollback_errors)
            ) from exc

        raise GeneratorError(
            f"Write failed; all completed changes were rolled back: {exc}"
        ) from exc

    cleanup_errors = cleanup_paths(list(backups.values()))
    cleanup_errors.extend(cleanup_paths(list(temps.values())))

    if cleanup_errors:
        raise GeneratorError(
            "Write succeeded, but transaction cleanup failed: "
            + " | ".join(cleanup_errors)
        )


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def print_validator(findings: list[Finding]) -> tuple[int, int]:
    errors, warnings = findings_summary(findings)

    print("\nVALIDATOR")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")
    print(f"Result: {'FAIL' if errors else 'PASS'}")

    for level, code, message in findings:
        print(f"[{level}] {code}: {message}")

    return errors, warnings


def print_plan(
    input_path: Path,
    d: dict[str, Any],
    duplicates: dict[str, str],
    outputs: dict[Path, bytes],
    warnings: int,
    mode: str,
) -> None:
    print("CRICXZ ARTICLE GENERATOR")
    print(f"\nMode: {mode}")
    print(f"Input: {input_path}")

    print("\nPLAN")
    print(f"Article: {d['article_relative']}")
    print(
        "Hero image: "
        f"assets/images/articles/{d['hero_image_fs'].name}"
    )
    print(f"Image exists: {'YES' if d['hero_image_fs'].is_file() else 'NO'}")
    print("News card: ADD")
    print("Search entry: ADD")
    print("Sitemap entry: ADD")
    print(
        "Homepage: "
        + ("ADD" if d["homepage_featured"] else "NO CHANGE")
    )

    print("\nDUPLICATES")
    for label, status in duplicates.items():
        print(f"{label}: {status}")
    print("Markers: READY")

    print("\nFILES THAT WOULD CHANGE" if mode == "DRY RUN" else "\nFILES CHANGED")
    planned = [
        d["article_path"],
        NEWS_PATH,
        SEARCH_PATH,
        SITEMAP_PATH,
    ]
    if d["homepage_featured"]:
        planned.append(HOMEPAGE_PATH)

    for path in planned:
        print(f"- {relative(path)}")

    print("\nBLOCKERS: 0")
    print(f"WARNINGS: {warnings}")
    print(
        "\nDECISION: "
        + ("READY TO WRITE" if mode == "DRY RUN" else "WRITE COMPLETE")
    )


def main() -> int:
    args = parse_args()
    input_path: Path = args.article_data
    mode = "WRITE" if args.write else "DRY RUN"

    print("CRICXZ ARTICLE GENERATOR")
    print(f"\nMode: {mode}")
    print(f"Input: {input_path}")

    try:
        data = load_json(input_path)
    except (FileNotFoundError, IsADirectoryError, ValueError, TypeError) as exc:
        print(f"\nInput error: {exc}", file=sys.stderr)
        return 2

    findings = validate(data, allow_missing_image=False)
    errors, warnings = print_validator(findings)

    if errors:
        print(f"\nBLOCKERS: {errors}")
        print(f"WARNINGS: {warnings}")
        print("\nDECISION: BLOCKED")
        return 1

    try:
        d, originals, outputs, duplicates = prepare_plan(data)
    except GeneratorError as exc:
        print(f"\n[BLOCKER] {exc}", file=sys.stderr)
        print("\nDECISION: BLOCKED")
        return 1
    except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        print(f"\n[BLOCKER] {exc}", file=sys.stderr)
        print("\nDECISION: BLOCKED")
        return 1

    if not args.write:
        print_plan(
            input_path,
            d,
            duplicates,
            outputs,
            warnings,
            "DRY RUN",
        )
        return 0

    try:
        transactional_write(outputs, originals)
    except GeneratorError as exc:
        print(f"\n[WRITE ERROR] {exc}", file=sys.stderr)
        print("\nDECISION: BLOCKED")
        return 1

    print_plan(
        input_path,
        d,
        duplicates,
        outputs,
        warnings,
        "WRITE",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())