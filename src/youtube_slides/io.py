import os
import subprocess
import yaml
from typing import Any, NamedTuple, List, Dict

from PIL import Image
from kedro.io import AbstractDataSet


class YouTubeData(NamedTuple):
    id: str
    title: str
    video_filepath: str
    description: str
    subtitles: str


class YouTubeDataSet(AbstractDataSet):

    def __init__(self, path, language="en"):
        self._path = os.path.expanduser(path)
        self._language = language
        self._data_dir = os.path.join(self._path, "data")

    def _save(self, urls: List[str]) -> None:
        for url in urls:
            vid = os.path.basename(url).split("=")[1]
            output_yaml_filepath = os.path.join(self._path, f"{vid}.yaml")
            video_data_dir = os.path.join(self._data_dir, vid)
            os.makedirs(video_data_dir, exist_ok=True)

            if os.path.exists(output_yaml_filepath):
                self._logger.info(f"Skipping {vid}. Already exists.")
                continue
            else:
                self._logger.info(f"Saving {vid}.")

            def ydl(*args):
                filename_format = "%(id)s.%(ext)s"
                return subprocess.check_output(
                    ["youtube-dl"] + list(args) + ["-o", filename_format, url],
                    cwd=video_data_dir,
                ).decode("utf8").strip()

            subs_list = ydl("--list-subs")

            def _check_if_language_available(raw_subs_list):
                possible_subtitles = raw_subs_list.split("Available subtitles ")
                if len(possible_subtitles) <= 1:
                    return False
                found_subtitles = possible_subtitles[1]
                for sub in found_subtitles.split("\n"):
                    if sub.strip().startswith(self._language):
                        return True
                else:
                    return False

            has_subs = _check_if_language_available(subs_list)

            title = ydl("--get-title")

            description_path = os.path.join(video_data_dir, f"{vid}.description")
            if os.path.exists(description_path):
                os.remove(description_path)

            if has_subs:
                write_output = ydl("--write-sub", "--write-description")
            else:
                write_output = ydl("--write-auto-sub", "--write-description")

            def _extract_subtitle_filename(out):
                for l in out.split("\n"):
                    if "Writing video subtitles to:" in l:
                        return l.split(": ")[1]

            subtitle_filename = _extract_subtitle_filename(write_output)
            if subtitle_filename is not None:
                subtitle_path = os.path.join(video_data_dir, subtitle_filename)
                with open(subtitle_path, encoding="utf8") as f:
                    subtitles = f.read()
            else:
                subtitles = ""

            with open(description_path, encoding="utf8") as f:
                description = f.read()

            filename = [
                name for name in os.listdir(video_data_dir)
                if name != f"{vid}.description" and name != subtitle_filename
            ][0]

            with open(output_yaml_filepath, "w+", encoding="utf8") as f:
                yaml.dump({
                    "id": vid,
                    "title": title,
                    "video_filepath": os.path.join(video_data_dir, filename),
                    "description": description,
                    "subtitles": subtitles,
                }, f)

    def _load(self) -> Dict[str, YouTubeData]:
        parts = {}
        for potential_file in os.listdir(self._path):
            if potential_file.endswith(".yaml"):
                vid, _ = os.path.splitext(potential_file)
                with open(os.path.join(self._path, potential_file)) as f:
                    parts[vid] = YouTubeData(**yaml.load(f, Loader=yaml.FullLoader))
        return parts

    def _describe(self):
        return dict(
            path=self._path,
            data_dir=self._data_dir,
            language=self._language,
        )


class Screenshots(AbstractDataSet):

    def __init__(self, path):
        self._path = os.path.expanduser(path)

    def _save(self, video_screenshots: Dict[str, Dict[str, Image.Image]]) -> None:
        for vid, screenshots in video_screenshots.items():
            video_dir = os.path.join(self._path, vid)
            os.makedirs(video_dir, exist_ok=True)
            for timing, screenshot in screenshots.items():
                if screenshot is None:
                    continue
                screenshot_filepath = os.path.join(video_dir, f"{timing}.png")
                screenshot.save(screenshot_filepath)

    def _load(self) -> Any:
        parts = {}
        vids = os.listdir(self._path)
        for vid in vids:
            vid_path = os.path.join(self._path, vid)
            screenshot_files = os.listdir(os.path.join(self._path, vid))
            screenshots = {}
            for screenshot_file in screenshot_files:
                timing, ext = os.path.splitext(screenshot_file)
                if ext == ".png":
                    def _screenshot_fun():
                        screenshot_path = os.path.join(vid_path, screenshot_file)
                        return Image.open(screenshot_path)
                    screenshots[timing] = _screenshot_fun
            parts[vid] = screenshots
        return parts

    def _describe(self) -> Dict[str, Any]:
        return dict(path=self._path)
