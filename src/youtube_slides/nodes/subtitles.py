import datetime
from dateutil import parser
from typing import Dict

from youtube_slides.io import YouTubeData


def _parse_subtitles(subtitles: str):
    timings = {}
    last_was_timing = False
    timing = None
    last_saved_line = None
    for l in subtitles.split("\n"):
        if "-->" in l:
            timing = l.split(" --> ")[0]
            last_was_timing = True
        elif last_was_timing:
            if last_saved_line != l:
                timings[timing] = l
                last_saved_line = l
            last_was_timing = False
    return timings


def _aggregate_subtitles(parsed_subtitles: Dict, time_segment_seconds: int):
    aggregated_subtitles = {}
    current_tt_agg = None
    current_subtitles = []
    tt = None
    for subtitle_time, subtitle_line in parsed_subtitles.items():
        tt = parser.parse(subtitle_time)

        if current_tt_agg is None:
            current_tt_agg = tt
            current_subtitles = [subtitle_line]
            continue

        time_diff = tt - current_tt_agg
        if time_diff.seconds > time_segment_seconds:
            aggregated_subtitles[tt.strftime("%H:%M:%S")] = current_subtitles
            current_tt_agg = tt
            current_subtitles = [subtitle_line]
            continue

        current_subtitles.append(subtitle_line)

    if tt is not None:
        aggregated_subtitles[tt.strftime("%H:%M:%S")] = current_subtitles

    return aggregated_subtitles


def key_subtitles(videos: Dict[str, YouTubeData], time_segment_seconds: int):
    keyed_subtitles = {}
    for vid, video in videos.items():
        parsed = _parse_subtitles(video.subtitles)
        keyed = _aggregate_subtitles(parsed, time_segment_seconds)
        keyed_subtitles[vid] = keyed
    return keyed_subtitles
