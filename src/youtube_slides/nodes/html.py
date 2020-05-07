import base64
from io import BytesIO
from typing import Dict, List, Callable

from PIL import Image

from youtube_slides.io import YouTubeData


def _combine_images_and_subtitles(
        title: str,
        description: str,
        images: Dict[str, Callable],
        subtitles: Dict[str, List[str]]
) -> str:
    keys = subtitles.keys()
    caption_rows = []
    template = """
<div class='.caption-row'>
    %(img)s
    <br/>
    <blockquote>
    <p>
        %(caption)s
    </p>
    </blockquote>
</div>
"""

    def _generate_image_tag(target_key):
        img_template = '<img src="data:image/png;base64, %(b64_image)s" alt="Image" />'
        callable_image = images.get(target_key)
        if callable_image is None:
            return None
        image = callable_image()
        buffered = BytesIO()
        image.save(buffered, format="JPEG")
        b64_image = base64.b64encode(buffered.getvalue()).decode("UTF8")
        image.close()
        return img_template % {"b64_image": b64_image}

    current_caption_list = []
    for key in keys:
        image_tag = _generate_image_tag(key)
        current_caption_list += subtitles[key]
        if image_tag is None:
            continue
        caption = " ".join(current_caption_list)
        output = template % {"img": _generate_image_tag(key), "caption": caption}
        caption_rows.append(output)
        current_caption_list = []
    if len(current_caption_list) > 0:
        caption = " ".join(current_caption_list)
        output = template % {"img": "", "caption": caption}
        caption_rows.append(output)

    body = "\n".join(caption_rows)
    formatted_description = "<br/>".join(description.split("\n"))
    return """
<html>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>%(title)s</title>
<body>
<h1>%(title)s</h1>
    <blockquote>
        %(description)s
    </blockquote>
    %(body)s
</body>
</html>
""" % {"title": title, "body": body, "description": formatted_description}


def combine_images_and_subtitles(
        youtube_dl: Dict[str, YouTubeData],
        screenshots: Dict[str, Dict[str, Image.Image]],
        keyed_subtitles: Dict[str, Dict[str, List[str]]]
) -> Dict[str, str]:
    parts = {}
    for vid, youtube_data in youtube_dl.items():
        combo = _combine_images_and_subtitles(
            youtube_data.title,
            youtube_data.description,
            screenshots[vid],
            keyed_subtitles[vid]
        )
        parts[youtube_data.title] = combo
    return parts
