import json
import mimetypes
from datetime import datetime
from itertools import islice
from safety import local_path


def inspect_path(selected_path):
    path = local_path(selected_path)

    information = {
        "name": path.name,
        "path": str(path),
    }

    if path.is_dir():
        # List a limited number of immediate children.
        # Do not recursively read the whole folder.
        with_entries = path.iterdir()
        entries = list(islice(with_entries, 51))

        information.update({
            "kind": "folder",
            "entries": [
                {
                    "name": entry.name,
                    "kind": (
                        "symlink" if entry.is_symlink()
                        else "folder" if entry.is_dir()
                        else "file" if entry.is_file()
                        else "other"
                    ),
                }
                for entry in entries[:50]
            ],
            "listing_truncated": len(entries) > 50,
        })

        return information

    if not path.is_file():
        raise ValueError("Select a regular file or folder.")

    details = path.stat()

    # This is a filename-based hint, not verification of file contents.
    mime_type, compression = mimetypes.guess_type(path.name)

    information.update({
        "kind": "file",
        "extension": path.suffix.lower(),
        "size_bytes": details.st_size,
        "modified": datetime.fromtimestamp(
            details.st_mtime
        ).astimezone().isoformat(),
        "mime_type_hint": mime_type,
        "compression_hint": compression,
        "type_verified": False,
    })

    return information


if __name__ == "__main__":
    selected = input("Paste a file or folder path: ").strip().strip('"')

    try:
        result = inspect_path(selected)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, ValueError) as error:
        print(f"Could not inspect the selection: {error}")

