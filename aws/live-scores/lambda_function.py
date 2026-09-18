"""CricXZ live-scores backend.

One Lambda serves two purposes:
* EventBridge schedule: refresh CricketData and write a sanitized S3 cache.
* API Gateway HTTP request: return the cache without spending a provider hit.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import boto3


API_BASE_URL = "https://api.cricapi.com/v1/currentMatches"
CACHE_KEY = "live-scores/current.json"
MAX_MATCHES = 50

s3 = boto3.client("s3")


def _json_response(status_code: int, payload: dict[str, Any]) -> dict[str, Any]:
    allowed_origin = os.environ.get("ALLOWED_ORIGIN", "https://cricxz.com")
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "public, max-age=60, stale-if-error=1200",
            "Access-Control-Allow-Origin": allowed_origin,
            "Vary": "Origin",
            "X-Content-Type-Options": "nosniff",
        },
        "body": json.dumps(payload, separators=(",", ":"), ensure_ascii=False),
    }


def _sanitize_score(score: Any) -> list[dict[str, Any]]:
    if not isinstance(score, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for innings in score[:4]:
        if not isinstance(innings, dict):
            continue
        cleaned.append(
            {
                "r": innings.get("r"),
                "w": innings.get("w"),
                "o": innings.get("o"),
                "inning": str(innings.get("inning") or "")[:120],
            }
        )
    return cleaned


def _sanitize_match(match: Any) -> dict[str, Any] | None:
    if not isinstance(match, dict):
        return None
    teams = match.get("teams")
    if not isinstance(teams, list) or len(teams) < 2:
        return None
    return {
        "id": str(match.get("id") or "")[:100],
        "name": str(match.get("name") or "Cricket match")[:200],
        "matchType": str(match.get("matchType") or "")[:20],
        "status": str(match.get("status") or "Match information unavailable")[:300],
        "venue": str(match.get("venue") or "")[:160],
        "date": str(match.get("date") or "")[:40],
        "dateTimeGMT": str(match.get("dateTimeGMT") or "")[:50],
        "teams": [str(teams[0])[:100], str(teams[1])[:100]],
        "score": _sanitize_score(match.get("score")),
        "matchStarted": match.get("matchStarted") is True,
        "matchEnded": match.get("matchEnded") is True,
    }


def _fetch_provider() -> dict[str, Any]:
    api_key = os.environ.get("CRICKETDATA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("CRICKETDATA_API_KEY is not configured")

    query = urlencode({"apikey": api_key, "offset": 0})
    request = Request(
        f"{API_BASE_URL}?{query}",
        headers={"Accept": "application/json", "User-Agent": "CricXZ-LiveScores/1.0"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(1_500_000)
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("CricketData request failed") from exc

    provider = json.loads(raw.decode("utf-8"))
    if provider.get("status") != "success" or not isinstance(provider.get("data"), list):
        raise RuntimeError("CricketData returned an invalid response")

    matches = []
    for item in provider["data"][:MAX_MATCHES]:
        cleaned = _sanitize_match(item)
        if cleaned:
            matches.append(cleaned)

    info = provider.get("info") if isinstance(provider.get("info"), dict) else {}
    return {
        "status": "success",
        "data": matches,
        "meta": {
            "cachedAt": datetime.now(timezone.utc).isoformat(),
            "source": "CricketData.org",
            "hitsUsed": info.get("hitsUsed"),
            "hitsLimit": info.get("hitsLimit"),
        },
    }


def _write_cache(payload: dict[str, Any]) -> None:
    bucket = os.environ["CACHE_BUCKET"]
    s3.put_object(
        Bucket=bucket,
        Key=CACHE_KEY,
        Body=json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"),
        ContentType="application/json; charset=utf-8",
        CacheControl="no-store",
        ServerSideEncryption="AES256",
    )


def _read_cache() -> dict[str, Any]:
    bucket = os.environ["CACHE_BUCKET"]
    result = s3.get_object(Bucket=bucket, Key=CACHE_KEY)
    return json.loads(result["Body"].read().decode("utf-8"))


def _is_schedule_event(event: Any) -> bool:
    return isinstance(event, dict) and event.get("source") == "aws.events"


def lambda_handler(event: Any, context: Any) -> dict[str, Any]:
    del context
    if _is_schedule_event(event):
        payload = _fetch_provider()
        _write_cache(payload)
        return {"refreshed": True, "matchCount": len(payload["data"])}

    try:
        payload = _read_cache()
        return _json_response(200, payload)
    except Exception:
        return _json_response(
            503,
            {
                "status": "error",
                "data": [],
                "message": "Live scores are temporarily unavailable.",
            },
        )
