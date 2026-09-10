import json
from safety import selected_file


def read_text_file(selected_path, max_characters=12000):
    if not isinstance(max_characters, int) or not 1 <= max_characters <= 12000:
        raise ValueError("Text limit must be between 1 and 12,000 characters.")
    path = selected_file(selected_path)

    if not path.is_file():
        raise ValueError("Select a file, not a folder.")

    # Read a bounded sample, not an unlimited file.
    with path.open("rb") as file:
        raw = file.read(max_characters * 4 + 4)

    # Recognize common Unicode byte-order marks.
    if raw.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        encoding = "utf-32"
    elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        encoding = "utf-16"
    else:
        encoding = "utf-8-sig"

    # Incremental decoding tolerates a sample ending mid-character.
    import codecs

    try:
        decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
        text = decoder.decode(raw, final=len(raw) >= path.stat().st_size)
    except UnicodeDecodeError:
        raise ValueError(
            "This file isn't readable with the supported text encodings. "
            "It may need a document, image, or audio reader."
        )

    # Reject common signs of binary content.
    if any(
        ord(character) < 32 and character not in "\t\n\r"
        for character in text
    ):
        raise ValueError(
            "This appears to contain binary data. "
            "It needs a specialized reader."
        )

    truncated = (
        len(text) > max_characters
        or path.stat().st_size > len(raw)
    )

    return {
        "path": str(path),
        "reader": "plain_text",
        "encoding": encoding,
        "content": text[:max_characters],
        "truncated": truncated,
    }


if __name__ == "__main__":
    selected = input("Paste a text file path: ").strip().strip('"')

    try:
        result = read_text_file(selected)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, ValueError) as error:
        print(f"Could not read the file: {error}")