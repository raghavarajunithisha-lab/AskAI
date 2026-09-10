import argparse
import os
from pathlib import Path

import winreg


PROJECT_DIR = Path(__file__).resolve().parent
PYTHON_EXE = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
ASSISTANT = PROJECT_DIR / "assistant_chat.py"

OWNER = "AskAI.LocalFileAssistant.v1"

# These entries belong to the current Windows user.
ENTRIES = [
    (
        r"Software\Classes\*\shell\AskAI_LocalAssistant",
        '"%1"',
    ),
    (
        r"Software\Classes\Directory\shell\AskAI_LocalAssistant",
        r'"%1\."',
    ),
]


def check_ownership(key_path):
    """Avoid replacing an unrelated application's registry entry."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_READ,
        )
    except FileNotFoundError:
        return False

    with key:
        try:
            owner, _ = winreg.QueryValueEx(key, "AskAIOwner")
        except FileNotFoundError:
            owner = None

    if owner != OWNER:
        raise ValueError(
            f"An unrelated entry already exists at:\n{key_path}\n"
            "Setup stopped without replacing it."
        )

    return True


def install():
    if not PYTHON_EXE.is_file():
        raise ValueError(
            f"Virtual-environment Python was not found:\n{PYTHON_EXE}"
        )

    if not ASSISTANT.is_file():
        raise ValueError(
            f"Assistant script was not found:\n{ASSISTANT}"
        )

    # Check both locations before making changes.
    for key_path, _ in ENTRIES:
        check_ownership(key_path)

    for key_path, selected_argument in ENTRIES:
        # Launch Python directly. No cmd.exe or shell command is used.
        # -- separates the selected path from command-line options.
        command = (
            f'"{PYTHON_EXE}" "{ASSISTANT}" '
            f"-- {selected_argument}"
        )

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            key_path,
            0,
            winreg.KEY_WRITE,
        ) as key:
            winreg.SetValueEx(
                key, "AskAIOwner", 0, winreg.REG_SZ, OWNER
            )
            winreg.SetValueEx(
                key, "", 0, winreg.REG_SZ, "Ask AI"
            )
            winreg.SetValueEx(
                key, "Icon", 0, winreg.REG_SZ,
                f'"{PYTHON_EXE}",0'
            )
            winreg.SetValueEx(
                key, "MultiSelectModel", 0, winreg.REG_SZ,
                "Single"
            )

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            key_path + r"\command",
            0,
            winreg.KEY_WRITE,
        ) as key:
            winreg.SetValueEx(
                key, "", 0, winreg.REG_SZ, command
            )

    print("Ask AI was added for files and folders.")
    print("Close any open right-click menu and try again.")
    print("On Windows 11, look under Show more options.")
    print("Select one file or folder at a time.")


def uninstall():
    # Verify ownership before removing any entries.
    existing = [
        key_path
        for key_path, _ in ENTRIES
        if check_ownership(key_path)
    ]

    for key_path in existing:
        try:
            winreg.DeleteKey(
                winreg.HKEY_CURRENT_USER,
                key_path + r"\command",
            )
        except FileNotFoundError:
            pass

        winreg.DeleteKey(
            winreg.HKEY_CURRENT_USER,
            key_path,
        )

    print("Ask AI menu entries were removed.")
    print("Your project, models and personal files were not deleted.")


def main():
    if os.name != "nt":
        raise ValueError("This setup is for Windows only.")

    parser = argparse.ArgumentParser(
        description="Install or remove the Ask AI right-click menu."
    )
    parser.add_argument(
        "action",
        choices=["install", "uninstall"],
    )
    args = parser.parse_args()

    if args.action == "install":
        install()
    else:
        uninstall()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Setup could not finish: {error}")
        raise SystemExit(1)