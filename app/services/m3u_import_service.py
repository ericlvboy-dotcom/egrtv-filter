"""Parser for remote M3U sources.

The parser deliberately treats ambiguous entries as live TV.  Movie and
series classification is based only on explicit metadata, group names, or
recognisable VOD file extensions; it never guesses from a channel title.
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

_ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
_VOD_EXTENSIONS = (".mp4", ".mkv", ".avi", ".mov", ".m4v", ".wmv")
_MOVIE_WORDS = ("movie", "movies", "vod", "film", "films")
_SERIES_WORDS = ("series", "tv shows", "tv-shows", "episodes")
_TRACKING_HEADERS = ("#EXTINF:",)


def _stable_id(value: str) -> str:
    return str((int(hashlib.sha1(value.encode("utf-8", "replace")).hexdigest()[:8], 16) % 9_000_000) + 1)


def _content_type(attrs: dict[str, str], group: str, url: str) -> str:
    explicit = (attrs.get("tvg-type") or attrs.get("type") or "").strip().lower()
    group_lower = group.lower()
    path = urlsplit(url).path.lower()
    if explicit in {"series", "episode", "tvshow", "tv_show"}:
        return "series"
    if explicit in {"movie", "vod", "film"}:
        return "vod"
    if any(word in group_lower for word in _SERIES_WORDS):
        return "series"
    if any(word in group_lower for word in _MOVIE_WORDS):
        return "vod"
    if path.endswith(_VOD_EXTENSIONS):
        return "vod"
    return "live"


def parse_m3u(text: str) -> dict[str, list[dict]]:
    """Convert M3U entries to XtreamFilter's six cache collections."""
    result = {
        "live_categories": [], "vod_categories": [], "series_categories": [],
        "live_streams": [], "vod_streams": [], "series": [],
    }
    categories: dict[str, dict[str, str]] = {
        "live": {}, "vod": {}, "series": {},
    }
    pending: dict[str, str] = {}
    pending_name = ""

    for raw_line in text.lstrip("\ufeff").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            metadata, separator, title = line.partition(",")
            pending = dict(_ATTR_RE.findall(metadata))
            pending_name = title.strip() if separator else pending.get("tvg-name", "").strip()
            continue
        if line.startswith("#"):
            continue
        if not pending and not pending_name:
            continue

        url = line
        name = pending_name or pending.get("tvg-name") or url
        group = pending.get("group-title", "").strip() or "Uncategorised"
        kind = _content_type(pending, group, url)
        category_id = _stable_id(kind + ":" + group)
        categories[kind].setdefault(category_id, group)
        item_id = _stable_id(url)
        logo = pending.get("tvg-logo", "")
        tvg_id = pending.get("tvg-id", "")

        if kind == "live":
            item = {
                "num": len(result["live_streams"]) + 1,
                "name": name, "stream_type": "live",
                "stream_id": item_id, "stream_icon": logo,
                "epg_channel_id": tvg_id, "category_id": category_id,
                "direct_source": url, "container_extension": "ts",
            }
            result["live_streams"].append(item)
        elif kind == "vod":
            path = urlsplit(url).path
            extension = path.rsplit(".", 1)[-1].lower() if "." in path else "mp4"
            item = {
                "num": len(result["vod_streams"]) + 1,
                "name": name, "stream_type": "movie",
                "stream_id": item_id, "stream_icon": logo,
                "category_id": category_id, "direct_source": url,
                "container_extension": extension,
            }
            result["vod_streams"].append(item)
        else:
            result["series"].append({
                "num": len(result["series"]) + 1,
                "name": name, "series_id": item_id, "cover": logo,
                "category_id": category_id, "direct_source": url,
                "plot": "Imported from M3U; episode metadata is provider-dependent.",
            })
        pending = {}
        pending_name = ""

    for kind, mapping in categories.items():
        result[f"{kind}_categories"] = [
            {"category_id": category_id, "category_name": name}
            for category_id, name in mapping.items()
        ]
    return result
