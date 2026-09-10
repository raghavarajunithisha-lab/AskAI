import json
import os
import subprocess
import winreg
import tempfile
import msvcrt
from safety import local_path, check_open_target, fingerprint
from pathlib import Path
from tkinter import Tk, filedialog


SETTINGS_FILE = Path(__file__).resolve().with_name(
    "saved_applications.json"
)

APP_PATHS_KEY = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
)


def load_saved_apps():
    if not SETTINGS_FILE.exists():
        return {}

    if SETTINGS_FILE.stat().st_size > 65536:
        raise ValueError("Saved application settings exceed 64 KB.")
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        raise ValueError("Cannot read saved_applications.json. Back it up and rename it to reset remembered apps.") from error

    if not isinstance(data, dict) or not all(
        isinstance(name, str) and isinstance(path, str)
        for name, path in data.items()
    ):
        raise ValueError("The saved application settings are invalid.")

    return data


def remember_app(name, executable):
    # A separate lock protects read-modify-write across assistant windows.
    lock_path = SETTINGS_FILE.with_suffix('.lock')
    with lock_path.open('a+b') as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise OSError('Another window is updating application settings. Try again.') from error
        temporary = None
        try:
            saved = load_saved_apps()
            saved[name] = str(executable)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                    dir=SETTINGS_FILE.parent, prefix='saved-apps-', suffix='.tmp',
                    delete=False) as file:
                temporary = Path(file.name)
                json.dump(saved, file, indent=2, ensure_ascii=False)
            temporary.replace(SETTINGS_FILE)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def discover_applications():
    applications = {}

    # Check per-user and machine-wide registrations in both views.
    for hive in (
        winreg.HKEY_CURRENT_USER,
        winreg.HKEY_LOCAL_MACHINE,
    ):
        for view in (
            winreg.KEY_WOW64_64KEY,
            winreg.KEY_WOW64_32KEY,
        ):
            try:
                with winreg.OpenKey(
                    hive,
                    APP_PATHS_KEY,
                    0,
                    winreg.KEY_READ | view,
                ) as root:
                    count = winreg.QueryInfoKey(root)[0]

                    for index in range(count):
                        try:
                            name = winreg.EnumKey(root, index)

                            with winreg.OpenKey(root, name) as entry:
                                value, _ = winreg.QueryValueEx(entry, "")

                            if not isinstance(value, str):
                                continue

                            executable = Path(
                                os.path.expandvars(value.strip().strip('"'))
                            )

                            if (
                                executable.is_file()
                                and executable.suffix.lower() == ".exe"
                            ):
                                applications.setdefault(
                                    str(executable).casefold(),
                                    {
                                        "name": name,
                                        "path": str(executable),
                                    },
                                )

                        except OSError:
                            continue

            except OSError:
                continue

    return sorted(
        applications.values(),
        key=lambda app: app["name"].casefold(),
    )


def find_applications(query):
    query = query.strip().casefold()

    saved_matches = [
        {"name": name, "path": path}
        for name, path in load_saved_apps().items()
        if query in name.casefold() and Path(path).is_file()
    ]

    registered_matches = [
        app
        for app in discover_applications()
        if query in app["name"].casefold()
        or query in Path(app["path"]).parent.name.casefold()
    ]

    # Remove duplicate executable paths.
    unique = {}

    for app in saved_matches + registered_matches:
        unique.setdefault(app["path"].casefold(), app)

    return list(unique.values())


def browse_application():
    window = Tk()
    window.withdraw()

    try:
        selected = filedialog.askopenfilename(
            parent=window,
            title="Choose the application's executable",
            filetypes=[("Windows application", "*.exe")],
        )
    finally:
        window.destroy()

    if not selected:
        return None

    executable = Path(selected).resolve(strict=True)

    if not executable.is_file() or executable.suffix.lower() != ".exe":
        raise ValueError("Choose an application's .exe file.")

    return executable


def open_selection(selected_path, executable=None):
    application = None
    if executable is not None:
        application = local_path(executable)
        if not application.is_file() or application.suffix.lower() != '.exe':
            raise ValueError('Choose an application executable.')
    target = check_open_target(selected_path, application)
    before = fingerprint(target)
    app_before = fingerprint(application) if application else None
    print("\nOpen request awaiting your confirmation:")
    print(f"Selected item: {target}")
    print(f"Application: {application or 'Windows default application'}")
    print("The launched application has its own file permissions and behavior.")
    if target.is_dir() and application:
        print("For an editor, keep unfamiliar folders in restricted/untrusted workspace mode.")
    if input('Type OPEN to launch, or press Enter to cancel: ').strip() != 'OPEN':
        return 'Cancelled. Nothing was opened.'
    if fingerprint(target) != before or (application and fingerprint(application) != app_before):
        raise ValueError('Selection/application changed during confirmation. Please retry.')
    check_open_target(target, application)
    if application:
        os.startfile(str(application), 'open', subprocess.list2cmdline([str(target)]))
    else:
        os.startfile(str(target), 'open')
    return f'Open request sent for: {target}'


def main():
    selected = input(
        "Paste a file or folder path: "
    ).strip().strip('"')

    target = Path(selected).expanduser().resolve(strict=True)

    query = input(
        "Application name, or press Enter for the default app: "
    ).strip()

    if not query:
        print(open_selection(target))
        return

    matches = find_applications(query)

    print("\nMatching registered or remembered applications:")

    for index, app in enumerate(matches, start=1):
        print(f"{index}. {app['name']}\n   {app['path']}")

    if not matches:
        print("No match found.")

    print("B. Browse for an application")
    print("C. Cancel")

    choice = input("\nChoose: ").strip().lower()

    if choice == "c":
        print("Cancelled.")
        return

    if choice == "b":
        executable = browse_application()

        if executable is None:
            print("Cancelled.")
            return

    elif choice.isdigit() and 1 <= int(choice) <= len(matches):
        executable = Path(matches[int(choice) - 1]["path"])

    else:
        raise ValueError("Choose one of the displayed options.")

    print(open_selection(target, executable))

    # Remember the user's chosen application under their search name.
    try:
        remember_app(query, executable)
    except OSError as error:
        print(f"The application choice could not be saved: {error}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
    except Exception as error:
        print(f"Could not complete the request: {error}")