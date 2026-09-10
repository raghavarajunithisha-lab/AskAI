import io
import shutil
import subprocess
import sys
import tempfile
import warnings
import wave
from functools import lru_cache
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageOps

from config import (
    MAX_AUDIO_SECONDS,
    MAX_OUTPUT_BYTES,
    MAX_DOCUMENT_BYTES,
    MAX_IMAGE_PIXELS,
    READER_TIMEOUT,
)
from safety import selected_file, local_path, fingerprint


# Each output needs a compatible codec and container.
# The AI cannot supply executable commands or codec arguments.
AUDIO_RECIPES = {
    "mp3": ("libmp3lame", "mp3", ["-q:a", "2"]),
    "wav": ("pcm_s16le", "wav", []),
    "flac": ("flac", "flac", []),
    "ogg": ("libvorbis", "ogg", ["-q:a", "5"]),
    "opus": ("libopus", "opus", ["-b:a", "128k"]),
    "m4a": ("aac", "ipod", ["-b:a", "192k"]),
    "aac": ("aac", "adts", ["-b:a", "192k"]),
    "aiff": ("pcm_s16be", "aiff", []),
    "wma": ("wmav2", "asf", ["-b:a", "192k"]),
    "ac3": ("ac3", "ac3", ["-b:a", "192k"]),
    "mp2": ("mp2", "mp2", ["-b:a", "192k"]),
    "caf": ("pcm_s16le", "caf", []),
    "au": ("pcm_s16be", "au", []),
    "w64": ("pcm_s16le", "w64", []),
    "mka": ("flac", "matroska", []),
}

INPUT_FORMATS = {
    ".mp3": "mp3",
    ".mp2": "mp3",
    ".wav": "wav",
    ".w64": "w64",
    ".mp4": "mov",
    ".m4a": "mov",
    ".m4b": "mov",
    ".mov": "mov",
    ".aac": "aac",
    ".flac": "flac",
    ".ogg": "ogg",
    ".oga": "ogg",
    ".opus": "ogg",
    ".mkv": "matroska",
    ".webm": "matroska",
    ".mka": "matroska",
    ".avi": "avi",
    ".aiff": "aiff",
    ".aif": "aiff",
    ".wma": "asf",
    ".ac3": "ac3",
    ".caf": "caf",
    ".au": "au",
}

IMAGE_RECIPES = {
    "png": "PNG",
    "jpg": "JPEG",
    "webp": "WEBP",
    "bmp": "BMP",
    "tiff": "TIFF",
    "gif": "GIF",
    "ico": "ICO",
    "tga": "TGA",
    "ppm": "PPM",
    "pgm": "PPM",
    "pbm": "PPM",
    "pcx": "PCX",
    "qoi": "QOI",
    "avif": "AVIF",
    "jp2": "JPEG2000",
    "pdf": "PDF",
}

ALIASES = {
    "jpeg": "jpg",
    "jpe": "jpg",
    "tif": "tiff",
    "aif": "aiff",
    "oga": "ogg",
}

# Compatibility with modules that import ENCODERS.
ENCODERS = {
    name: ["-c:a", codec, *extra]
    for name, (codec, muxer, extra) in AUDIO_RECIPES.items()
}


def canonical_format(value):
    value = value.strip().lower().lstrip(".")
    return ALIASES.get(value, value)


@lru_cache(maxsize=1)
def audio_formats():
    def inventory(option):
        result = subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-hide_banner",
                option,
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
            creationflags=getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            ),
        )

        if result.returncode:
            raise ValueError(
                "Cannot inspect the installed audio converter."
            )

        return result.stdout.splitlines()

    codecs = {
        parts[1]
        for line in inventory("-encoders")
        if len(parts := line.split()) >= 2
        and len(parts[0]) == 6
        and parts[0].startswith("A")
    }

    muxers = {
        name
        for line in inventory("-muxers")
        if len(parts := line.split()) >= 2
        and parts[0] in {"E", "DE"}
        for name in parts[1].split(",")
    }

    return sorted(
        name
        for name, (codec, muxer, _) in AUDIO_RECIPES.items()
        if codec in codecs and muxer in muxers
    )


def _save_picture(picture, destination, target):
    picture = picture.convert("RGBA")

    if target == "ico":
        picture.thumbnail((256, 256))

        canvas = Image.new(
            "RGBA", (256, 256), (0, 0, 0, 0)
        )

        canvas.paste(
            picture,
            (
                (256 - picture.width) // 2,
                (256 - picture.height) // 2,
            ),
        )

        picture = canvas

    elif target == "gif":
        alpha = picture.getchannel("A")
        picture = picture.convert("RGB").quantize(colors=255)

        picture.paste(
            255,
            mask=alpha.point(
                lambda a: 255 if a < 128 else 0
            ),
        )

        picture.info["transparency"] = 255

    elif target not in {
        "png", "webp", "tiff", "tga", "qoi", "avif"
    }:
        background = Image.new(
            "RGB", picture.size, "white"
        )

        background.paste(
            picture,
            mask=picture.getchannel("A"),
        )

        picture = background

    if target == "pgm":
        picture = picture.convert("L")
    elif target == "pbm":
        picture = picture.convert("1")

    options = {}

    if target in {"jpg", "webp", "avif", "pdf"}:
        options["quality"] = 95

    if target == "pdf":
        options["resolution"] = 150.0

    picture.save(
        destination,
        format=IMAGE_RECIPES[target],
        **options,
    )


@lru_cache(maxsize=1)
def image_formats():
    # Test tiny in-memory images so unavailable encoders are omitted.
    Image.init()
    available = []

    for target, fmt in IMAGE_RECIPES.items():
        if fmt not in Image.SAVE:
            continue

        try:
            _save_picture(
                Image.new("RGBA", (32, 32), "white"),
                io.BytesIO(),
                target,
            )
            available.append(target)

        except (OSError, ValueError, KeyError, ImportError):
            continue

    return sorted(available)


def is_image_file(path):
    Image.init()

    fmt = Image.registered_extensions().get(
        path.suffix.lower()
    )

    return (
        path.is_file()
        and fmt in set(IMAGE_RECIPES.values()) - {"PDF"}
    )


def _run(command, report_error=False):
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=(
                subprocess.PIPE
                if report_error
                else subprocess.DEVNULL
            ),
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=READER_TIMEOUT,
            creationflags=getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            ),
        )

    except subprocess.TimeoutExpired as error:
        raise ValueError(
            "Conversion timed out. Try a smaller file."
        ) from error

    if result.returncode:
        detail = (
            result.stderr.strip()[:800]
            if report_error
            else ""
        )

        raise ValueError(
            detail
            or "Media conversion failed: "
            "unsupported/damaged input or no audio track."
        )


def ffmpeg_run(arguments):
    _run([
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-nostdin",
        "-hide_banner",
        "-loglevel", "error",
        "-n",
        "-threads", "2",
        *arguments,
    ])


def decode_audio(source_path, destination, speech=False):
    source = selected_file(source_path)
    demuxer = INPUT_FORMATS.get(source.suffix.lower())

    if not demuxer:
        raise ValueError(
            "Unsupported media input. "
            "Playlists/URLs are not accepted."
        )

    before = fingerprint(source)
    destination = Path(destination)

    options = [
        "-protocol_whitelist", "file",
        "-format_whitelist", demuxer,
        "-f", demuxer,
    ]

    if demuxer == "mov":
        options += [
            "-enable_drefs", "0",
            "-use_absolute_path", "0",
        ]

    options += [
        "-i", str(source),
        "-map", "0:a:0",
        "-vn",
        "-sn",
        "-dn",
        "-map_metadata", "-1",
        "-map_chapters", "-1",
        "-t", str(MAX_AUDIO_SECONDS + 1),
        "-ac", "1" if speech else "2",
        "-ar", "16000" if speech else "48000",
        "-c:a", "pcm_s16le",
        "-fs", str(MAX_OUTPUT_BYTES),
        "-f", "wav",
        str(destination),
    ]

    ffmpeg_run(options)

    if before != fingerprint(source):
        raise ValueError(
            "Source changed during decoding; retry."
        )

    if (
        not destination.is_file()
        or destination.stat().st_size >= MAX_OUTPUT_BYTES
    ):
        raise ValueError(
            "Decoded audio reached the output-size limit."
        )

    with wave.open(str(destination), "rb") as audio:
        duration = (
            audio.getnframes() / audio.getframerate()
        )

    if duration > MAX_AUDIO_SECONDS:
        raise ValueError(
            f"Audio exceeds {MAX_AUDIO_SECONDS // 60} minutes. "
            "No shortened output was saved."
        )

    if duration <= 0:
        raise ValueError("No audio samples were decoded.")

    return duration


def _output_path(source, output_path, target):
    output = local_path(output_path, must_exist=False)

    if output == source or output.exists():
        raise ValueError(
            "Choose a NEW filename; "
            "existing files cannot be overwritten."
        )

    if canonical_format(output.suffix) != target:
        raise ValueError(
            f"The output filename must use .{target}."
        )

    if not output.parent.is_dir():
        raise ValueError(
            "Choose an existing output folder."
        )

    if (
        shutil.disk_usage(output.parent).free
        < MAX_OUTPUT_BYTES * 3
    ):
        raise ValueError(
            "At least 384 MB of free output-drive "
            "space is required."
        )

    return output


def _publish(converted, output):
    if not 0 < converted.stat().st_size < MAX_OUTPUT_BYTES:
        raise ValueError(
            "Output is empty or exceeds the size limit."
        )

    with output.open("xb") as destination:
        try:
            with converted.open("rb") as source:
                shutil.copyfileobj(source, destination)

        except BaseException:
            destination.close()
            output.unlink(missing_ok=True)
            raise

    return str(output)


def convert_audio(source_path, output_path, output_format):
    target = canonical_format(output_format)

    if target not in audio_formats():
        raise ValueError(
            "That audio output is unavailable "
            "in the installed FFmpeg."
        )

    source = selected_file(source_path)
    output = _output_path(source, output_path, target)

    with tempfile.TemporaryDirectory(
        prefix="askai-",
        dir=output.parent,
    ) as folder:
        pcm = Path(folder) / "decoded.wav"
        decode_audio(source, pcm)

        converted = pcm

        if target != "wav":
            codec, muxer, extra = AUDIO_RECIPES[target]

            converted = Path(folder) / f"result.{target}"

            ffmpeg_run([
                "-protocol_whitelist", "file",
                "-format_whitelist", "wav",
                "-f", "wav",
                "-i", str(pcm),
                "-map", "0:a:0",
                "-map_metadata", "-1",
                "-c:a", codec,
                *extra,
                "-fs", str(MAX_OUTPUT_BYTES),
                "-f", muxer,
                str(converted),
            ])

        return _publish(converted, output)


def _image_worker(source_path, destination, target):
    source = selected_file(
        source_path,
        MAX_DOCUMENT_BYTES,
    )

    with warnings.catch_warnings():
        warnings.simplefilter(
            "error",
            Image.DecompressionBombWarning,
        )

        with Image.open(source) as original:
            if getattr(original, "n_frames", 1) != 1:
                raise ValueError(
                    "Animated/multipage images are not supported; "
                    "choose a single still image."
                )

            if (
                original.width * original.height
                > MAX_IMAGE_PIXELS
            ):
                raise ValueError(
                    f"Image exceeds {MAX_IMAGE_PIXELS:,} pixels. "
                    "Resize it first."
                )

            picture = ImageOps.exif_transpose(
                original
            ).convert("RGBA")

            picture.info.clear()

            _save_picture(
                picture,
                destination,
                target,
            )


def convert_image(source_path, output_path, output_format):
    target = canonical_format(output_format)

    if target not in image_formats():
        raise ValueError(
            "That image output is unavailable "
            "in the installed Pillow."
        )

    source = selected_file(
        source_path,
        MAX_DOCUMENT_BYTES,
    )

    output = _output_path(source, output_path, target)
    before = fingerprint(source)

    with tempfile.TemporaryDirectory(
        prefix="askai-image-",
        dir=output.parent,
    ) as folder:
        converted = Path(folder) / f"result.{target}"

        _run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--image-worker",
                str(source),
                str(converted),
                target,
            ],
            report_error=True,
        )

        if fingerprint(source) != before:
            raise ValueError(
                "The source image changed; retry."
            )

        return _publish(converted, output)


if __name__ == "__main__":
    if (
        len(sys.argv) == 5
        and sys.argv[1] == "--image-worker"
    ):
        try:
            _image_worker(
                sys.argv[2],
                sys.argv[3],
                sys.argv[4],
            )
        except Exception as error:
            print(str(error)[:800], file=sys.stderr)
            raise SystemExit(1)
    else:
        print(
            "Start assistant_chat.py to use the converter."
        )