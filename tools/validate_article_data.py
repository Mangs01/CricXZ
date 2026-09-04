"""Validate CricXZ article data without modifying files or using the network."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIRECTORY = REPOSITORY_ROOT / "assets" / "images" / "articles"

REQUIRED_FIELDS = {
    "slug", "seoTitle", "headline", "metaDescription", "categoryLabel",
    "filterCategories", "articleType", "deck", "publicationDatetime",
    "heroImageFilename", "heroImageAlt", "heroImageWidth", "heroImageHeight",
    "articleBodyHtml", "sources",
}
OPTIONAL_FIELDS = {
    "modifiedDatetime", "heroImageCaption", "sourceCutoff", "relatedArticles",
    "cardHeadline", "cardSummary", "homepageFeatured",
}
DERIVED_FIELDS = {
    "canonicalUrl", "articlePath", "heroImagePath", "heroImageUrl", "ogUrl",
    "ogImage", "ogTitle", "ogDescription", "ogImageAlt",
    "schemaMainEntityOfPage", "schemaImage", "searchUrl", "sitemapLoc",
    "publicationDateVisible", "modifiedDateVisible", "publisherName",
    "publisherUrl", "robots", "ogType", "siteName", "searchType", "authorName",
}
ALLOWED_CATEGORIES = {"india", "ipl", "icc", "test", "odi"}
ALLOWED_ARTICLE_TYPES = {"news", "match-report", "rankings", "squad", "feature"}
TEMPORARY_SLUG_WORDS = {"latest", "breaking"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RELATED_URL_RE = re.compile(r"^(?:articles|pages)/[a-z0-9]+(?:-[a-z0-9]+)*\.html$")
H1_RE = re.compile(r"<\s*h1(?:\s|>)", re.IGNORECASE)
UNSAFE_BODY_PATTERNS = (
    ("script element", re.compile(r"<\s*script\b", re.IGNORECASE)),
    ("onerror handler", re.compile(r"\bonerror\s*=", re.IGNORECASE)),
    ("onclick handler", re.compile(r"\bonclick\s*=", re.IGNORECASE)),
    ("onload handler", re.compile(r"\bonload\s*=", re.IGNORECASE)),
    ("javascript URL", re.compile(r"javascript\s*:", re.IGNORECASE)),
)
LOCALHOST_RE = re.compile(r"localhost|127\.0\.0\.1|::1", re.IGNORECASE)

Finding = tuple[str, str, str]


def add(findings: list[Finding], level: str, code: str, message: str) -> None:
    findings.append((level, code, message))


def parse_datetime(value: Any, field: str, findings: list[Finding]) -> datetime | None:
    if not isinstance(value, str):
        add(findings, "ERROR", "DATETIME_INVALID", f"{field} must be an ISO 8601 string.")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        add(findings, "ERROR", "DATETIME_INVALID", f"{field} is not a valid ISO 8601 date-time.")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        add(findings, "ERROR", "DATETIME_TIMEZONE_REQUIRED", f"{field} must include an explicit timezone.")
        return None
    return parsed


def iter_strings(value: Any, path: str = "$") -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key in sorted(value, key=str):
            yield from iter_strings(value[key], f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from iter_strings(item, f"{path}[{index}]")


def validate_sources(value: Any, findings: list[Finding]) -> None:
    if not isinstance(value, list) or not value:
        add(findings, "ERROR", "SOURCES_INVALID", "sources must be a non-empty list.")
        return
    for index, source in enumerate(value):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            add(findings, "ERROR", "SOURCE_INVALID", f"{prefix} must be an object.")
            continue
        label = source.get("label")
        url = source.get("url")
        if not isinstance(label, str) or not label.strip():
            add(findings, "ERROR", "SOURCE_LABEL_INVALID", f"{prefix}.label must be a non-empty string.")
        if not isinstance(url, str) or not url.strip():
            add(findings, "ERROR", "SOURCE_URL_INVALID", f"{prefix}.url must be a non-empty HTTPS URL.")
            continue
        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
        except ValueError:
            parsed = None
            hostname = None
        if parsed is None or parsed.scheme.lower() != "https" or not hostname:
            add(findings, "ERROR", "SOURCE_URL_INVALID", f"{prefix}.url must parse as HTTPS with a hostname.")
        elif LOCALHOST_RE.search(hostname):
            add(findings, "ERROR", "SOURCE_URL_LOCALHOST", f"{prefix}.url must not use a localhost address.")


def validate_related(value: Any, findings: list[Finding]) -> None:
    if not isinstance(value, list):
        add(findings, "ERROR", "RELATED_ARTICLES_INVALID", "relatedArticles must be a list when present.")
        return
    for index, item in enumerate(value):
        prefix = f"relatedArticles[{index}]"
        if not isinstance(item, dict):
            add(findings, "ERROR", "RELATED_ARTICLE_INVALID", f"{prefix} must be an object.")
            continue
        title = item.get("title")
        url = item.get("url")
        if not isinstance(title, str) or not title.strip():
            add(findings, "ERROR", "RELATED_TITLE_INVALID", f"{prefix}.title must be a non-empty string.")
        if not isinstance(url, str) or not RELATED_URL_RE.fullmatch(url):
            add(findings, "ERROR", "RELATED_URL_INVALID", f"{prefix}.url must be a safe articles/ or pages/ HTML path.")
            continue
        target = (REPOSITORY_ROOT / Path(url)).resolve()
        try:
            target.relative_to(REPOSITORY_ROOT)
        except ValueError:
            add(findings, "ERROR", "RELATED_URL_INVALID", f"{prefix}.url resolves outside the repository.")
            continue
        if not target.is_file():
            add(findings, "ERROR", "RELATED_FILE_MISSING", f"{prefix}.url does not reference an existing file: {url}")


def validate(data: dict[str, Any], allow_missing_image: bool) -> list[Finding]:
    findings: list[Finding] = []

    for field in sorted(REQUIRED_FIELDS - data.keys()):
        add(findings, "ERROR", "REQUIRED_FIELD_MISSING", f"Required field is missing: {field}")

    for field in sorted(data.keys() & DERIVED_FIELDS):
        add(findings, "ERROR", "DERIVED_FIELD_PRESENT", f"Derived field must not be stored: {field}")
    allowed_fields = REQUIRED_FIELDS | OPTIONAL_FIELDS | DERIVED_FIELDS
    for field in sorted(data.keys() - allowed_fields):
        add(findings, "ERROR", "UNKNOWN_FIELD", f"Unknown top-level field: {field}")

    required_text_fields = (
        "seoTitle",
        "headline",
        "metaDescription",
        "categoryLabel",
        "deck",
        "heroImageAlt",
    )

    for field in required_text_fields:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            add(
                findings,
                "ERROR",
                "TEXT_FIELD_INVALID",
                f"{field} must be a non-empty string.",
            )

    optional_text_fields = (
        "heroImageCaption",
        "sourceCutoff",
        "cardHeadline",
        "cardSummary",
    )

    for field in optional_text_fields:
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                add(
                    findings,
                    "ERROR",
                    "OPTIONAL_TEXT_FIELD_INVALID",
                    f"{field} must be a non-empty string when present.",
                )

    slug = data.get("slug")
    if not isinstance(slug, str) or not SLUG_RE.fullmatch(slug):
        add(findings, "ERROR", "SLUG_INVALID", "slug must be lowercase alphanumeric segments separated by hyphens.")
    else:
        for word in sorted(TEMPORARY_SLUG_WORDS & set(slug.split("-"))):
            add(findings, "WARNING", "SLUG_TEMPORARY_WORD", f"slug contains temporary segment: {word}")

    categories = data.get("filterCategories")
    if not isinstance(categories, list) or not categories:
        add(findings, "ERROR", "FILTER_CATEGORIES_INVALID", "filterCategories must be a non-empty list.")
    else:
        invalid = sorted({repr(item) for item in categories if not isinstance(item, str) or item not in ALLOWED_CATEGORIES})
        if invalid:
            add(findings, "ERROR", "FILTER_CATEGORY_INVALID", f"Unsupported filterCategories values: {', '.join(invalid)}")
        if len(categories) != len({repr(item) for item in categories}):
            add(findings, "ERROR", "FILTER_CATEGORY_DUPLICATE", "filterCategories must not contain duplicates.")

    article_type = data.get("articleType")
    if not isinstance(article_type, str) or article_type not in ALLOWED_ARTICLE_TYPES:
        add(findings, "ERROR", "ARTICLE_TYPE_INVALID", "articleType is not an approved value.")

    publication = parse_datetime(data.get("publicationDatetime"), "publicationDatetime", findings)
    modified = None
    if "modifiedDatetime" in data:
        modified = parse_datetime(data["modifiedDatetime"], "modifiedDatetime", findings)
    if publication is not None and modified is not None and modified <= publication:
        add(findings, "ERROR", "MODIFIED_DATETIME_ORDER", "modifiedDatetime must be strictly later than publicationDatetime.")

    filename = data.get("heroImageFilename")
    if not isinstance(filename, str):
        add(findings, "ERROR", "HERO_FILENAME_INVALID", "heroImageFilename must be a local filename string.")
    else:
        unsafe_filename = Path(filename).is_absolute() or "/" in filename or "\\" in filename or ".." in filename or "://" in filename
        expected = re.compile(rf"^{re.escape(slug)}-cricxz\.(?:webp|jpg|jpeg|png)$") if isinstance(slug, str) else None
        if unsafe_filename or expected is None or not expected.fullmatch(filename):
            add(findings, "ERROR", "HERO_FILENAME_MISMATCH", "heroImageFilename must exactly match <slug>-cricxz.<supported-extension>.")
        image_path = IMAGE_DIRECTORY / filename
        if not image_path.is_file():
            if allow_missing_image:
                add(findings, "WARNING", "HERO_IMAGE_MISSING_ALLOWED", f"Hero image is missing but allowed: {image_path}")
            else:
                add(findings, "ERROR", "HERO_IMAGE_MISSING", f"Hero image file is missing: {image_path}")


    for field in ("heroImageWidth", "heroImageHeight"):
        value = data.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            add(findings, "ERROR", "IMAGE_DIMENSION_INVALID", f"{field} must be a positive integer.")

    body = data.get("articleBodyHtml")
    if not isinstance(body, str) or not body.strip():
        add(findings, "ERROR", "ARTICLE_BODY_INVALID", "articleBodyHtml must be a non-empty string.")
    else:
        if H1_RE.search(body):
            add(findings, "ERROR", "ARTICLE_BODY_H1", "articleBodyHtml must not contain an H1 element.")
        for label, pattern in UNSAFE_BODY_PATTERNS:
            if pattern.search(body):
                add(findings, "ERROR", "ARTICLE_BODY_UNSAFE", f"articleBodyHtml contains a prohibited {label} pattern.")

    for path, value in iter_strings(data):
        if LOCALHOST_RE.search(value):
            add(findings, "ERROR", "LOCALHOST_VALUE", f"Localhost value found at {path}.")

    validate_sources(data.get("sources"), findings)
    if "relatedArticles" in data:
        validate_related(data["relatedArticles"], findings)

    if "homepageFeatured" in data and not isinstance(data["homepageFeatured"], bool):
        add(findings, "ERROR", "HOMEPAGE_FEATURED_INVALID", "homepageFeatured must be Boolean when present.")

    meta_description = data.get("metaDescription")
    if isinstance(meta_description, str) and not 120 <= len(meta_description) <= 170:
        add(findings, "WARNING", "META_DESCRIPTION_LENGTH", f"metaDescription length is {len(meta_description)}; recommended range is 120-170.")
    if article_type in {"match-report", "rankings", "squad"}:
        cutoff = data.get("sourceCutoff")
        if not isinstance(cutoff, str) or not cutoff.strip():
            add(findings, "WARNING", "SOURCE_CUTOFF_RECOMMENDED", f"sourceCutoff is recommended for articleType {article_type}.")

    return sorted(findings, key=lambda finding: (finding[0] != "ERROR", finding[1], finding[2]))


def print_report(path: Path, findings: list[Finding]) -> int:
    errors = sum(level == "ERROR" for level, _, _ in findings)
    warnings = sum(level == "WARNING" for level, _, _ in findings)
    print("CRICXZ ARTICLE DATA VALIDATOR")
    print(f"\nFile: {path}")
    print(f"\nERRORS: {errors}")
    print(f"WARNINGS: {warnings}")
    if findings:
        print()
        for level, code, message in findings:
            print(f"[{level}] {code}: {message}")
    print(f"\nRESULT: {'FAIL' if errors else 'PASS'}")
    return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one CricXZ article-data JSON file.")
    parser.add_argument("article_data", type=Path, help="path to one article-data JSON file")
    parser.add_argument(
        "--allow-missing-image",
        action="store_true",
        help="downgrade a missing hero image from an error to a warning",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path: Path = args.article_data
    if not path.exists():
        print(f"Input error: file does not exist: {path}", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"Input error: path is not a file: {path}", file=sys.stderr)
        return 2
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"Input error: could not read valid JSON from {path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print(f"Input error: top-level JSON value must be an object: {path}", file=sys.stderr)
        return 2
    return print_report(path, validate(data, args.allow_missing_image))


if __name__ == "__main__":
    raise SystemExit(main())
