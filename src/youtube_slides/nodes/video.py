import os
import tempfile
from typing import Dict, List, Tuple

import cv2
from skimage.measure import compare_ssim
from PIL import Image
from dateutil.parser import parse

from youtube_slides.io import YouTubeData


def capture_frames(videos: Dict[str, YouTubeData],
                   keyed_subtitles: Dict[str, Dict],
                   processed_video_times: Dict[str, List]
                   ) -> Tuple[Dict[str, Dict[str, Image.Image]], Dict[str, List]]:
    captured_frames = {}
    new_processed_video_times = {}
    for vid, video in videos.items():
        times_already_processed = processed_video_times.get(vid, [])
        times_to_process = list(sorted(list(set(keyed_subtitles[vid].keys()) - set(times_already_processed))))
        video_frames = _capture_frames(video.video_filepath, times_to_process)
        newly_processed_times = list(video_frames.keys())
        new_processed_video_times[vid] = list(
            sorted(list(set(times_to_process + times_already_processed + newly_processed_times)))
        )
        captured_frames[vid] = video_frames
    return captured_frames, new_processed_video_times


def _capture_frames(video_filepath: str, aggregate_times: List[str]) -> Dict[str, Image.Image]:
    temp_dir = tempfile.mkdtemp()

    screenshots = {}

    prev_gray_scale_frame = None

    for raw_timing in aggregate_times:
        timing = parse(raw_timing)
        seconds = timing.second + timing.minute * 60 + timing.hour * 60 * 60

        cap = cv2.VideoCapture(video_filepath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 60

        target_frame = int(fps * seconds)
        target_path = os.path.join(temp_dir, f"{target_frame}.png")

        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

        while True:
            success, frame = cap.read()

            if frame is not None:
                cv2.imwrite(target_path, frame)
                wrote_successfully = True
                break

        is_10percent_different_from_last_frame = True
        if frame is not None:
            if prev_gray_scale_frame is None:
                prev_gray_scale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                current_gray_scale_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                (score, _) = compare_ssim(current_gray_scale_frame, prev_gray_scale_frame, full=True)
                is_10percent_different_from_last_frame = score <= 0.9
                prev_gray_scale_frame = current_gray_scale_frame

        if wrote_successfully and is_10percent_different_from_last_frame:
            image = Image.open(target_path)
            screenshots[raw_timing] = image
        else:
            screenshots[raw_timing] = None

        cv2.destroyAllWindows()
        cap.release()

    return screenshots
