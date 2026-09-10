"""Application checks, not an operating-system sandbox."""

import os
from pathlib import Path

from config import MAX_FILE_BYTES


VIEW_EXTENSIONS = frozenset(
    (
        ".txt .md .csv .tsv .json .yaml .yml .toml .ini .log .pdf "
        ".png .jpg .jpeg .jpe .webp .bmp .tif .tiff .gif .ico .tga "
        ".ppm .pgm .pbm .pcx .qoi .avif .jp2 .j2k .jpf .jpx "
        ".mp3 .mp2 .wav .w64 .m4a .m4b .aac .flac .ogg .oga .opus "
        ".mp4 .mov .mkv .avi .webm .aiff .aif .wma .ac3 .caf .au .mka"
    ).split()
)

SCRIPT_EXTENSIONS = frozenset(
    (
        ".py .pyw .ps1 .bat .cmd .js .vbs .sh "
        ".exe .com .scr .msi .msix .lnk .url "
        ".hta .reg .cpl .jar"
    ).split()
)


def local_path(value, must_exist=True):
    raw = str(value).strip().strip('"')

    if not raw:
        raise ValueError("Choose a file or folder.")

    if raw.startswith(("\\\\", "//")) or "://" in raw:
        raise ValueError(
            "Use a local drive path, "
            "not a network or device path."
        )

    path = Path(raw).expanduser()

    if os.name == "nt":
        if ":" in str(path)[len(path.drive):]:
            raise ValueError(
                "Alternate data stream paths are not supported."
            )

        if (
            hasattr(os.path, "isreserved")
            and os.path.isreserved(path)
        ):
            raise ValueError(
                "Reserved Windows paths are not supported."
            )

    path = path.resolve(strict=must_exist)

    if str(path).startswith(("\\\\", "//")):
        raise ValueError(
            "Network targets are not supported."
        )

    return path


def selected_file(value, limit=MAX_FILE_BYTES):
    path = local_path(value)

    if not path.is_file():
        raise ValueError("Choose a regular file.")

    if path.stat().st_size > limit:
        raise ValueError(
            f"File exceeds this operation's "
            f"{limit // (1024 * 1024)} MB limit."
        )

    return path


def fingerprint(path):
    info = path.stat()

    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def check_open_target(target, executable=None):
    target = local_path(target)

    if target.is_dir():
        return target

    if not target.is_file():
        raise ValueError(
            "Choose a regular file or folder."
        )

    suffix = target.suffix.lower()

    editor = (
        Path(executable).name.casefold()
        if executable
        else ""
    )

    source_extensions = {
        ".py", ".pyw", ".ps1", ".bat",
        ".cmd", ".js", ".vbs", ".sh",
    }

    if (
        suffix in source_extensions
        and editor in {"code.exe", "notepad.exe"}
    ):
        return target

    if (
        suffix in SCRIPT_EXTENSIONS
        or suffix not in VIEW_EXTENSIONS
    ):
        raise ValueError(
            "Opening this file type is disabled in AskAI. "
            "Use a trusted editor for source code, "
            "or open it manually outside AskAI."
        )

    return target