"""Decode restricted local media before running speech recognition."""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from config import (
    MODEL_ROOT,
    WORK_DIR,
    SPEECH_TIMEOUT,
    MAX_OUTPUT_BYTES,
)
from converter import decode_audio
from safety import selected_file
from reader_worker import run_reader


def transcribe_file(
    selected_path,
    model_name="base",
    language=None,
    use_vad=True,
):
    path = selected_file(selected_path)

    if model_name not in {"base", "small"}:
        raise ValueError("Choose base or small.")

    if language is not None:
        if (
            not isinstance(language, str)
            or not language.isalpha()
            or not 2 <= len(language) <= 3
        ):
            raise ValueError(
                "Use a language code such as en, te or hi."
            )

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    if shutil.disk_usage(WORK_DIR).free < MAX_OUTPUT_BYTES * 2:
        raise ValueError(
            "At least 256 MB of temporary workspace is required."
        )

    with tempfile.TemporaryDirectory(
        prefix="speech-",
        dir=WORK_DIR,
    ) as folder:
        pcm = Path(folder) / "speech.wav"

        duration = decode_audio(
            path,
            pcm,
            speech=True,
        )

        print(
            f"Loading {model_name} speech model; "
            f"uncached models download to {MODEL_ROOT / 'whisper'}."
        )

        result = run_reader(
            "speech",
            [str(pcm)],
            {
                "model_name": model_name,
                "language": language,
                "use_vad": use_vad,
            },
            timeout=SPEECH_TIMEOUT,
        )

    result["path"] = str(path)
    result["duration_seconds"] = round(duration, 2)

    return result


def _transcribe_wav(
    path,
    model_name="base",
    language=None,
    use_vad=True,
):
    from faster_whisper import WhisperModel

    folder = MODEL_ROOT / "whisper"
    folder.mkdir(parents=True, exist_ok=True)

    model = WhisperModel(
        model_name,
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        download_root=str(folder),
    )

    segments, info = model.transcribe(
        path,
        task="transcribe",
        language=language,
        beam_size=5,
        vad_filter=use_vad,
        condition_on_previous_text=False,
    )

    transcript = []
    characters = 0

    for segment in segments:
        text = segment.text.strip()

        if not text:
            continue

        characters += len(text)

        if characters > 100000 or len(transcript) >= 10000:
            raise ValueError(
                "Transcript exceeded its size limit."
            )

        transcript.append({
            "start_seconds": round(segment.start, 2),
            "end_seconds": round(segment.end, 2),
            "text": text,
        })

    return {
        "reader": "speech_transcription",
        "model": model_name,
        "language": info.language,
        "language_source": (
            "user_selected" if language else "auto_detected"
        ),
        "language_detection_probability": (
            None
            if language
            else round(info.language_probability, 3)
        ),
        "speech_filter_enabled": use_vad,
        "segments": transcript,
        "content": " ".join(
            item["text"] for item in transcript
        ),
        "no_speech_transcribed": not transcript,
        "note": (
            "Automatic transcript; words may be wrong. "
            "Empty output does not prove no speech. "
            "Video visuals are not analyzed."
        ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--model",
        choices=["base", "small"],
        default="base",
    )

    parser.add_argument(
        "--language",
        default=None,
    )

    parser.add_argument(
        "--no-vad",
        action="store_true",
    )

    args = parser.parse_args()

    selected = input(
        "Paste an audio or video path: "
    ).strip().strip('"')

    result = transcribe_file(
        selected,
        model_name=args.model,
        language=args.language,
        use_vad=not args.no_vad,
    )

    print(json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nClosed.")
    except Exception as error:
        print(f"Could not transcribe: {error}")