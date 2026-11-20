from app.services.m3u_import_service import parse_m3u


def test_parse_m3u_preserves_live_metadata_and_urls():
    playlist = """#EXTM3U
#EXTINF:-1 tvg-id="news.1" tvg-logo="https://img.test/news.png" group-title="News",News One
https://stream.test/live/news.m3u8
"""
    parsed = parse_m3u(playlist)
    assert len(parsed["live_streams"]) == 1
    item = parsed["live_streams"][0]
    assert item["name"] == "News One"
    assert item["epg_channel_id"] == "news.1"
    assert item["stream_icon"] == "https://img.test/news.png"
    assert item["direct_source"] == "https://stream.test/live/news.m3u8"
    assert parsed["live_categories"][0]["category_name"] == "News"


def test_parse_m3u_classifies_movie_by_group_and_extension():
    playlist = """#EXTM3U
#EXTINF:-1 group-title="Movies",A Movie
https://stream.test/movie/a-movie.mp4
#EXTINF:-1 group-title="Documentaries",A documentary
https://stream.test/vod/doc.mkv
"""
    parsed = parse_m3u(playlist)
    assert len(parsed["vod_streams"]) == 2
    assert {item["name"] for item in parsed["vod_streams"]} == {"A Movie", "A documentary"}


def test_parse_m3u_does_not_misclassify_ts_live_channels_as_vod():
    playlist = """#EXTM3U
#EXTINF:-1 group-title="News",News Channel
https://stream.test/live/news.ts
"""
    parsed = parse_m3u(playlist)
    assert len(parsed["live_streams"]) == 1
    assert parsed["vod_streams"] == []


def test_parse_m3u_classifies_explicit_series_metadata():
    playlist = """#EXTM3U
#EXTINF:-1 tvg-type="series" group-title="Drama",Example Series
https://stream.test/series/example/episode1.mp4
"""
    parsed = parse_m3u(playlist)
    assert len(parsed["series"]) == 1
    assert parsed["series"][0]["name"] == "Example Series"
    assert parsed["series"][0]["direct_source"].endswith("episode1.mp4")


def test_parse_m3u_ignores_comments_and_unpaired_urls():
    parsed = parse_m3u("#EXTM3U\n#EXTVLCOPT:http-user-agent=Player\nhttps://stream.test/unpaired.ts\n")
    assert parsed["live_streams"] == []
    assert parsed["vod_streams"] == []
