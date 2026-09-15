"""Local video conversion using imageio-ffmpeg."""

import argparse
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg

from safety import local_path, fingerprint


VIDEO_TIMEOUT = 3600

VIDEO_INPUTS = {
    ".mp4": "mov",
    ".mov": "mov",
    ".mkv": "matroska",
    ".avi": "avi",
    ".webm": "matroska",
}

# Each recipe specifies:
# video encoder, audio encoder, container, encoding options.
VIDEO_RECIPES = {
    "mp4": (
        "libx264",
        "aac",
        "mp4",
        [
            "-preset", "medium",
            "-crf", "20",
            "-b:a", "192k",
            "-movflags", "+faststart",
        ],
    ),
    "mov": (
        "libx264",
        "aac",
        "mov",
        [
            "-preset", "medium",
            "-crf", "20",
            "-b:a", "192k",
            "-movflags", "+faststart",
        ],
    ),
    "mkv": (
        "libx264",
        "aac",
        "matroska",
        [
            "-preset", "medium",
            "-crf", "20",
            "-b:a", "192k",
        ],
    ),
    "avi": (
        "mpeg4",
        "libmp3lame",
        "avi",
        [
            "-q:v", "3",
            "-b:a", "192k",
        ],
    ),
    "webm": (
        "libvpx-vp9",
        "libopus",
        "webm",
        [
            "-crf", "30",
            "-b:v", "0",
            "-deadline", "good",
            "-cpu-used", "4",
            "-b:a", "128k",
        ],
    ),
}


def _ffmpeg(arguments, timeout):
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-nostdin",
        *arguments,
    ]

    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=timeout,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError(
            "FFmpeg timed out; no completed output was saved."
        ) from error

    if result.returncode:
        raise ValueError(
            "FFmpeg failed: "
            + result.stderr[-3000:].strip()
        )

    return result.stdout


@lru_cache(maxsize=1)
def video_formats():
    """Return outputs supported by the installed FFmpeg build."""

    encoders = {
        parts[1]
        for line in _ffmpeg(["-encoders"], 15).splitlines()
        if len(parts := line.split()) >= 2
        and len(parts[0]) == 6
        and parts[0][0] in {"V", "A"}
    }

    muxers = {
        name
        for line in _ffmpeg(["-muxers"], 15).splitlines()
        if len(parts := line.split()) >= 2
        and parts[0] in {"E", "DE"}
        for name in parts[1].split(",")
    }

    return sorted(
        name
        for name, (video, audio, container, _) in VIDEO_RECIPES.items()
        if video in encoders
        and audio in encoders
        and container in muxers
    )


def convert_video(source_path, output_path, output_format="mp4"):
    target = output_format.strip().lower().lstrip(".")

    if target not in video_formats():
        raise ValueError(
            "Unavailable video output. Available: "
            + ", ".join(video_formats())
        )

    source = local_path(source_path)

    if (
        not source.is_file()
        or source.suffix.lower() not in VIDEO_INPUTS
    ):
        raise ValueError(
            "Choose an MP4, MOV, MKV, AVI, or WebM video."
        )

    output = local_path(
        output_path,
        must_exist=False,
    )

    if output.suffix.lower() != "." + target:
        raise ValueError(
            f"The output filename must end in .{target}."
        )

    if output == source or output.exists():
        raise ValueError(
            "Choose a new filename; existing files cannot be overwritten."
        )

    if not output.parent.is_dir():
        raise ValueError(
            "The output folder does not exist."
        )

    before = fingerprint(source)

    video, audio, container, options = VIDEO_RECIPES[target]

    with tempfile.TemporaryDirectory(
        prefix="askai-video-",
        dir=output.parent,
    ) as folder:
        converted = Path(folder) / f"result.{target}"

        _ffmpeg(
            [
                "-loglevel", "error",
                "-n",

                "-protocol_whitelist", "file",
                "-format_whitelist",
                VIDEO_INPUTS[source.suffix.lower()],

                "-i", str(source),

                # First video stream, excluding attached pictures.
                "-map", "0:V:0",

                # First audio stream, if present.
                "-map", "0:a:0?",

                "-map_metadata", "-1",
                "-map_chapters", "-1",

                "-c:v", video,
                "-c:a", audio,

                # Pad odd dimensions for encoder compatibility.
                "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                "-pix_fmt", "yuv420p",

                *options,

                "-f", container,
                str(converted),
            ],
            VIDEO_TIMEOUT,
        )

        if (
            not converted.is_file()
            or converted.stat().st_size == 0
        ):
            raise ValueError(
                "The converter produced no video."
            )

        if fingerprint(source) != before:
            raise ValueError(
                "The source changed during conversion. Please retry."
            )

        # Exclusive creation prevents overwriting another file.
        with output.open("xb") as destination:
            try:
                with converted.open("rb") as content:
                    shutil.copyfileobj(
                        content,
                        destination,
                    )
            except BaseException:
                destination.close()
                output.unlink(missing_ok=True)
                raise

    return str(output)


def main():
    parser = argparse.ArgumentParser(
        description="Convert between supported video formats."
    )

    parser.add_argument(
        "source",
        help="Input video path",
    )

    parser.add_argument(
        "output",
        help="New output path, e.g. output.webm",
    )

    args = parser.parse_args()

    try:
        target = Path(args.output).suffix.lstrip(".")

        print("Converting...")

        saved = convert_video(
            args.source,
            args.output,
            target,
        )

        print("Saved:", saved)

    except (ValueError, OSError) as error:
        parser.exit(
            1,
            f"Conversion failed: {error}\n",
        )


if __name__ == "__main__":
    main()