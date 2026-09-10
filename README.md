# AskAI — a local AI assistant for Windows files

Right-click a file or folder → **Show more options → Ask AI** → ask a question or request an action.

AskAI combines local AI models with Python tools to answer questions about selected files, convert images and audio, create a PDF from an image, and open a selection in an application after confirmation.

**Status:** personal development project. The current interface is a terminal window, not a packaged desktop installer. Windows setup is required. Models can make mistakes.

## What you can do

| Selection | Examples |
| --- | --- |
| Still image | `What is this image about?`, `Read the text`, `Convert to PNG`, `Convert to PDF` |
| Audio | `Summarize this recording`, `What does the speaker mention?`, `Convert to FLAC` |
| Video with audio | `Transcribe the speech`, `Extract the audio as MP3` |
| Text file or text-based PDF | `Summarize this file`, `Explain this code` |
| Folder | `What files are in this folder?`, `Open this folder in VS Code` |
| Supported file | `Open this file` or `Open this in a supported application` |

Opening a selection asks you to type **OPEN**. Conversion asks you to choose a new output filename; the original is preserved.

## Download and install on your laptop

You do **not** need Git or a GitHub account to download the public project.

### 1. Install Python and Ollama

- Use **Windows 10 22H2 or newer, or Windows 11**, on a 64-bit Intel/AMD laptop. Windows ARM and macOS/Linux are not covered by this setup.
- Install **Python 3.14, 64-bit** from [Python for Windows](https://www.python.org/downloads/windows/). This project was developed using Python 3.14. Enable **Add Python to PATH** if offered by your installer.
- Install and open [Ollama for Windows](https://ollama.com/download/windows). Choose local usage if offered; a cloud API key is not required.
- Have several GB of free space for dependencies and models. Ollama documents at least 4 GB for its application, with model storage additional. See [Ollama Windows requirements](https://docs.ollama.com/windows).

A GPU can improve local model response speed. Speech transcription in this project uses the CPU. Memory use depends on the operation; close unnecessary applications on laptops with limited RAM. Hardware minimums for the complete project have not been formally benchmarked.

Open a **new Command Prompt** and check:

```bat
python --version
ollama --version
```

The commands below are for **Command Prompt**, not PowerShell.

### 2. Download and extract the project

1. On this repository page, click the green **Code** button.
2. Click **Download ZIP**.
3. Right-click the downloaded ZIP and choose **Extract All**.
4. Put the extracted project in a permanent folder you can write to, for example `C:\Projects\AskAI` or `D:\Projects\AskAI`.
5. Find the folder that directly contains `assistant_chat.py`, `setup_context_menu.py`, and `requirements.in`. This is the project folder; avoid accidentally choosing its parent folder.

**Do not run the code from inside the ZIP.** Do not place it in `Program Files` or another administrator-protected location.

### 3. Create your Python environment

Open Command Prompt. Replace the first path below with your actual project folder:

```bat
cd /d "C:\Projects\AskAI"
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.in
python -m pip check
```

Run each line in order. A successful final check reports `No broken requirements found`.

Your prompt should now start with `(.venv)`. The environment must be named `.venv` because the menu setup uses `.venv\Scripts\python.exe`.

Dependencies and models are **not** included in the ZIP. `requirements.in` lists direct dependencies; it is not a version-locked environment or a vulnerability report.

### 4. Choose where speech and OCR models are stored

Open `config.py` in a text editor. Find the line beginning `MODEL_ROOT =`.

For a location that works without a D: drive, replace that one line with:

```python
MODEL_ROOT = Path(os.environ.get("ASKAI_MODEL_ROOT", str(Path.home() / "AskAIModels")))
```

Save the file. By default, this stores speech/OCR models inside `C:\Users\YOUR_WINDOWS_USER\AskAIModels`; you do not need to replace the username in the code.

If you prefer a drive with more free space, instead use your chosen path, for example:

```python
MODEL_ROOT = Path(r"D:\AskAIModels")
```

The program creates the model subfolders when needed. These settings control Whisper/OCR models, **not Ollama's models**.

### 5. Download the local chat and vision models

Keep Ollama running and run:

```bat
ollama pull qwen3:1.7b
ollama pull moondream
ollama list
```

Both model names should appear in the list. The first downloads can take several minutes. See the model pages for [Qwen3 1.7b](https://ollama.com/library/qwen3:1.7b) and [Moondream](https://ollama.com/library/moondream).

Whisper and OCR models download separately on their first use. They go into the folder selected in step 4.

<details>
<summary>Optional: store Ollama models on another drive before downloading</summary>

If your system drive has little space, choose a directory on another local drive:

```bat
mkdir "D:\OllamaModels"
setx OLLAMA_MODELS "D:\OllamaModels"
```

Then **quit Ollama from its system-tray icon**, close Command Prompt, and open a new Command Prompt. Run `ollama serve` there to start the server with the new setting; leave that window open. If the port is already in use, an Ollama server is still running—quit that server before starting another.

Open another Command Prompt and run the model download commands above. `setx` changes future processes, not an already-running Ollama server. Existing model files are not automatically moved. See [Ollama's model-location instructions](https://docs.ollama.com/windows).

</details>

### 6. Test AskAI before adding the menu

From the activated project terminal:

```bat
python assistant_chat.py
```

Paste the full path to a small file that you own, for example a JPG in Downloads. Try:

```text
What is this image about?
```

Then:

```text
Convert to PNG
```

Choose a **new** filename in the Save As dialog. Type `/exit` when finished.

For English speech, you can run:

```bat
python assistant_chat.py --speech-model small --language en
```

Omit `--language en` for automatic language detection. `--language` specifies the spoken language; it does not request translation.

### 7. Add the right-click menu

From the project terminal, run:

```bat
python setup_context_menu.py install
```

This adds entries to **your current Windows user's registry** for files and folders. It does not require running the terminal as administrator.

Now right-click **one** file or folder → **Show more options → Ask AI** on Windows 11. A terminal opens with that selection already supplied. On other supported Windows versions, look directly in the context menu.

Keep Ollama running. You do not need to activate the environment manually when launching through the menu; the menu already points to the project's environment.

If the terminal immediately disappears, use Command Prompt to see the error:

```bat
cd /d "C:\Projects\AskAI"
.venv\Scripts\activate
python assistant_chat.py "C:\full\path\to\your\file.jpg"
```

Replace both example paths with yours.

## Supported conversions

The program checks which of its configured encoders are available and displays their output formats at startup. Not every possible file extension is supported.

| Type | Configured outputs, when available |
| --- | --- |
| Single still image | PNG, JPG/JPEG, WebP, BMP, TIFF/TIF, GIF, ICO, TGA, PPM, PGM, PBM, PCX, QOI, AVIF, JP2 |
| Image → document | Single-page PDF containing the image |
| Audio, or audio extracted from video | MP3, WAV, FLAC, OGG, Opus, M4A, AAC, AIFF/AIF, WMA, AC3, MP2, CAF, AU, W64, MKA |

Image conversion corrects orientation and removes embedded metadata. Transparency is retained where implemented; formats without it use white. GIF reduces color/alpha precision, PGM is grayscale, PBM is black-and-white, and ICO fits the image into a 256 × 256 square. Lossy formats can reduce quality. The image PDF is not OCR-generated editable text.

Audio conversion uses intermediate 48 kHz, stereo, 16-bit PCM. Transcription uses 16 kHz mono. Converting to a lossless format cannot recover quality lost in the source.

## Commands

| Command | Effect |
| --- | --- |
| `/clear` | Clears conversation history; retains the selected item and cached content |
| `/refresh` | Clears cached content/history; the next question rereads the selection |
| `/exit` | Closes the conversation |

## Current limits

- Input file: up to 256 MiB; image/PDF readers: up to 25 MiB.
- Image: one frame, up to 12 million pixels.
- Audio: up to 10 minutes. Longer audio is rejected rather than silently shortened.
- Output: below 128 MiB; conversion currently requires a conservative 384 MiB of free output-drive space.
- PDF questions: up to 5 pages and 12,000 extracted characters per read. The final chat prompt uses at most 6,000 content characters.
- Folder questions: up to 50 immediate entries; their file contents are not recursively read.
- Expensive readers/conversions: typically 120-second timeout; speech worker: 900 seconds. First downloads count toward the relevant timeout.

Limits are configured in `config.py`; some explanatory messages use the current default values.

**Not currently implemented:** animated/multipage image conversion, SVG/HEIC conversion, image generation/editing, video visual understanding, video re-encoding, PDF-to-image conversion, recursive folder analysis, or batch selection.

## Privacy and file access

The explicit AI requests in the application go to local Ollama at `127.0.0.1:11434`. Packages and models require internet downloads; normal inference can run locally after the required models are cached. Launched applications can have their own network behavior.

Choosing a file controls what the application normally processes. It does **not** create a per-file Windows permission sandbox: Python, decoders and launched applications retain your account's permissions.

The app validates AI-selected actions, asks for confirmation before launching, blocks ordinary executable/script/shortcut opening, restricts media decoding, and avoids overwriting existing outputs. These protections do not guarantee that untrusted files or dependencies are safe. Do not run AskAI as administrator.

Temporary content is stored under `.work` inside the project. Normal operations clean it up; abrupt termination can leave files there. Remove leftover contents only when AskAI is closed. File paths and answers are visible in terminal scrollback.

## Updating or moving the project

To update code, close AskAI windows and replace the relevant source files. Keep your `.venv`, local configuration and model folders. Install dependencies again only if the dependency list changes.

If you **move the project folder**, create a fresh `.venv` at the new location, install dependencies, and rerun `python setup_context_menu.py install`. Virtual environments should be recreated rather than copied between laptops or locations.

## Remove the right-click menu

In Command Prompt, go to the project folder and activate the environment:

```bat
cd /d "C:\Projects\AskAI"
.venv\Scripts\activate
python setup_context_menu.py uninstall
```

This removes the AskAI menu entries. It does not delete personal files, model downloads, or the project. Uninstall the menu **before** deleting the project folder.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `python` or `ollama` is not recognized | Finish installing it and open a new Command Prompt; check PATH/install-manager configuration. |
| `No module named ...` | Activate this project's `.venv` and run `python -m pip install -r requirements.in`. |
| Connection refused / local AI unavailable | Start Ollama and check `ollama list`. |
| Model not found | Run the two `ollama pull` commands in step 5. |
| A path on D: does not exist | Update `MODEL_ROOT` in `config.py` as described in step 4. |
| Output format not listed | Its encoder is unavailable or the format is not implemented. Use an advertised output. |
| Existing output rejected | Choose a new filename; overwriting is intentionally disabled. |
| First OCR/transcription request times out | Check internet/storage, allow model downloads to finish, then retry. |
| High memory use or slow response | Close unnecessary apps, try a smaller file, or use `--speech-model base` for speech. |
| A new format won't open in Windows | Install/select an application that supports it; a converter doesn't create Windows file associations. |
| Inaccurate transcript or image answer | Verify against the source. Local models and OCR can misread words and visual details. |

## Main components

| Component | Role |
| --- | --- |
| `assistant_chat.py` | Terminal interface, request routing, and selected-file workflow |
| `converter.py` | Image/PDF conversion, restricted audio decoding and audio conversion |
| `app_launcher.py` / `setup_context_menu.py` | Confirmed application launching / Windows menu registration |
| `file_chat.py` and reader modules | File inspection, text/PDF extraction, OCR and transcription |
| `image_chat.py` / `image_reader.py` | OCR/vision question answering |
| `ollama_client.py` | Shared local AI HTTP client |
| `safety.py` / `reader_worker.py` / `config.py` | Validation, stoppable reader processes and settings |

Model backends: Qwen3 through Ollama, Moondream through Ollama, [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and RapidOCR. Conversion uses Pillow and FFmpeg through imageio-ffmpeg.

## Project status

This is a development prototype. The creator has reported working Windows use; not every laptop, codec, or model configuration has been tested. Do not interpret the repository as a security certification or a guarantee of perfect answers.

Model and dependency licenses apply separately. Check the repository's `LICENSE` file, if one is provided, for permission to reuse the project code.
