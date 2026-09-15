# AskAI a local AI assistant for Windows files

Right-click a file or folder → **Show more options → Ask AI** → ask a question or request an action.

AskAI combines local AI models with Python tools to answer questions about selected files, convert images, audio and video, create a PDF from an image, and open a selection in an application after confirmation.

**Status:** personal development project. The current interface is a terminal window, not a packaged desktop installer. Windows setup is required. Models can make mistakes.

## What you can do

| Selection | Examples |
| --- | --- |
| Still image | `What is this image about?`, `Read the text`, `Convert to PNG`, `Convert to PDF` |
| Audio | `Summarize this recording`, `What does the speaker mention?`, `Convert to FLAC` |
| Video | `Convert to MP4`, `Convert to MOV`, `Convert to WebM`; with audio: `Transcribe the speech`, `Extract the audio as MP3` |
| Text file or text-based PDF | `Summarize this file`, `Explain this code` |
| Folder | `What files are in this folder?`, `Open this folder in VS Code` |
| Supported file | `Open this file` or `Open this in a supported application` |

Opening a selection asks you to type **OPEN**. Conversion asks you to choose a new output filename; the original is preserved.

## Advantages

- **Local file processing:** AI requests go to Ollama on the same computer. Files do not need to be uploaded to a conversion or AI website for the implemented workflows.
- **One entry point:** right-click a selection to ask questions, convert it, or open it in an application.
- **Offline operation after setup:** cached models and installed tools can perform the supported tasks without an internet connection.
- **No cloud API key or per-request cloud inference charge:** processing uses the computer's own resources. Downloads, electricity and hardware still have costs.
- **Original files are preserved:** conversion saves a new file and refuses to overwrite an existing output.
- **Explicit format selection:** direct requests such as `convert to mp4` are routed to the requested supported format without asking the language model to choose it.
- **Reusable downloads:** models and conversion tools are reused across sessions. Each question does not download another model.
- **No built-in permanent chat archive:** only a short conversation history is held in application memory during a session.

## Disadvantages and trade-offs

- **Setup is manual:** Python, dependencies, Ollama, model downloads and Windows menu registration are required. There is no packaged installer yet.
- **Local resources carry the workload:** AI inference and media conversion consume CPU, RAM, disk space and sometimes GPU memory. Long jobs can increase battery use and fan noise.
- **Speed depends on hardware:** CPU-only inference can be slow; video encoding and speech transcription in this implementation use CPU processing.
- **Answers are not guaranteed correct:** the local language/vision models, OCR and transcription can miss details or make mistakes. File Q&A reads bounded excerpts rather than every part of a long document.
- **Format support is finite:** only the listed input/output combinations and available encoders are supported. A recognized extension does not guarantee its internal codec is decodable.
- **Conversion can change quality or content:** video is re-encoded; extra tracks, subtitles, chapters and metadata are not retained. Lossy image/audio/video formats can reduce quality. HDR tone mapping is not implemented.
- **Short session memory:** older exchanges are dropped, and conversations cannot be resumed after closing the terminal through a saved-chat feature.
- **One selection at a time:** batch processing and recursive folder-content analysis are not implemented.

## Disk space, downloads and RAM

Disk storage and RAM are different: storage holds installed files and saved outputs; RAM/VRAM holds working data while a task runs. A 531 MB project folder does not mean the project needs only 531 MB of disk space overall or uses 531 MB of RAM.

### Installed size and download size

A measured Windows installation folder at `D:\Projects\AskAI` shows **531 MB of file contents and 541 MB on disk**. This is one installation example, not a fixed download size or a complete inventory. It includes whatever is inside that folder at the time of measurement. Models installed elsewhere, the Ollama application, Python installed elsewhere and external caches are additional. The difference between file size and size on disk reflects filesystem allocation.

| Component | Approximate space | Notes |
| --- | --- | --- |
| Project folder in the measured example | 531 MB contents / 541 MB on disk | Includes its existing contents; do not add its virtual environment twice if it is already inside this folder. |
| Qwen3 `1.7b` model | 1.4 GB | Text/chat model; [published model size](https://ollama.com/library/qwen3:1.7b). |
| Moondream model | 1.7 GB | Vision model; [published model size](https://ollama.com/library/moondream). |
| Faster-Whisper `small` model | About 486 MB | Default speech model in the chat interface; [model repository size](https://huggingface.co/Systran/faster-whisper-small/tree/main). Downloading `base` as well adds a separate model. |
| Ollama application | Allow at least 4 GB for installation | Separate from models; [Ollama Windows requirements](https://docs.ollama.com/windows). This is installation space, not the compressed installer download size. |
| Python, OCR models and installation caches | Additional; varies | Exact size depends on installed versions, cached downloads and their locations. |
| Converted files | Additional; varies by media | Each successful conversion leaves a new file beside the original or in the chosen destination. |

The three listed AI models total roughly **3.6 GB**. They are downloaded once and reused unless removed, changed or updated. They are not included in a source ZIP. A ZIP download, an extracted source folder, an installed environment and a complete installation with models have different sizes.

**Planning estimate, not a measured minimum:** reserve around **12 to 15 GB of free disk space for a fresh full setup**, plus space for source files, outputs and temporary conversions. Large videos or extra models can require much more. Existing installations can reuse their models and tools; the video-conversion update itself adds no new AI model.

To measure your own installation, check folder Properties for the project, `MODEL_ROOT`, the active `OLLAMA_MODELS` folder and the Ollama installation. Run `ollama list` to inspect installed Ollama model sizes. Paths can be on different drives; each drive needs enough free space for the files stored there.

### Temporary files and output growth

| Operation | Where extra data goes | Cleanup |
| --- | --- | --- |
| File readers, OCR and transcription | Temporary subfolders under the project's `.work` directory | Normally removed when processing finishes or an exception is handled. |
| Image/audio/video conversion | Temporary subfolders in the chosen output directory | Normally removed after completion or a handled failure. |
| Completed conversion | The chosen output filename | Remains until you delete it; the source remains too. |
| Remembered applications | `saved_applications.json` beside the launcher, plus its lock file | Small persistent settings, not a conversation archive. |

Video conversion first writes a temporary result, then copies it to the final filename. If the output is 500 MB, allow roughly **1 GB of additional free space during that step**, besides the source file and other application needs. After normal cleanup, the new output consumes about 500 MB. Output size cannot be predicted from the extension alone and may exceed the source size. Audio conversion also creates an intermediate WAV.

Forced termination, power loss or cleanup failures can leave temporary files behind. Remove known leftover AskAI temporary directories only after its tasks have stopped. Installation caches and Ollama's own logs/updates are separate from AskAI's temporary files.

### RAM and GPU memory

**RAM use has not been formally benchmarked across machines.** The following is practical planning guidance, not a guaranteed minimum or a claim that AskAI uses all the listed memory:

| Total system RAM | Practical expectation |
| --- | --- |
| 4 GB | Not a practical target for the full Windows + local AI workflow. |
| 8 GB | May handle small tasks one at a time, but AI inference and multitasking can cause memory pressure and paging. |
| 16 GB | A reasonable starting target for the configured small models and everyday tasks. |
| 32 GB or more | More room for concurrent applications and demanding media; does not guarantee every file will process successfully. |

Actual use depends on the loaded model, context length, image/video dimensions, decoder/encoder buffers, worker processes and other applications. Download size is not the same as runtime memory usage. Decoded images and video frames can occupy much more memory than their compressed files.

- **Chat/vision:** Ollama can use a supported GPU, CPU, or a combination. Dedicated VRAM and system RAM are separate resources; integrated GPUs share system memory.
- **Speech:** the current faster-whisper configuration uses CPU inference with `int8` computation and four CPU threads.
- **Video conversion:** the configured encoders are software encoders; a GPU used by Ollama does not automatically accelerate these conversions.
- **Conversation memory:** only the last four messages, usually two question answer exchanges, are retained in the history list. Selected-file content or prepared images can also be cached in RAM for follow-up questions.
- **Model lifetime:** some requests explicitly unload an Ollama model; others use the server's retention settings. Closing AskAI releases its Python session memory but does not necessarily stop Ollama or immediately unload every model. Unloading a model frees runtime memory without deleting its downloaded files.

Use Windows Task Manager to observe Python, reader workers, FFmpeg and Ollama while a task is running. `ollama ps` shows models currently loaded by Ollama. `/clear` removes the application's recent conversation history but retains its cached file content; `/refresh` clears both. Neither command deletes downloaded models.

## Download and install on your laptop

You do **not** need Git or a GitHub account to download the public project.

### 1. Install Python and Ollama

- Use **Windows 10 22H2 or newer, or Windows 11**, on a 64-bit Intel/AMD laptop. Windows ARM and macOS/Linux are not covered by this setup.

- Install **Python 3.14, 64-bit** from [Python for Windows](https://www.python.org/downloads/windows/). This project was developed using Python 3.14. Enable **Add Python to PATH** if offered by your installer.

- Install and open [Ollama for Windows](https://ollama.com/download/windows). Choose local usage if offered; a cloud API key is not required.

- Review **Disk space, downloads and RAM** above before installing. Storage for Ollama, its models, the project environment and temporary output must all be accounted for.

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

Then **quit Ollama from its system-tray icon**, close Command Prompt, and open a new Command Prompt. Run `ollama serve` there to start the server with the new setting; leave that window open. If the port is already in use, an Ollama server is still running, quit that server before starting another.

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
| Video: MP4, MOV, MKV, AVI or WebM input | MP4, MOV, MKV, AVI or WebM output |

Image conversion corrects orientation and removes embedded metadata. Transparency is retained where implemented; formats without it use white. GIF reduces color/alpha precision, PGM is grayscale, PBM is black-and-white, and ICO fits the image into a 256 x 256 square. Lossy formats can reduce quality. The image PDF is not OCR-generated editable text.

Audio conversion uses intermediate 48 kHz, stereo, 16-bit PCM. Transcription uses 16 kHz mono. Converting to a lossless format cannot recover quality lost in the source.

Video conversion re-encodes the first video track and first audio track, if present, for the full duration. Silent videos are supported. MP4/MOV/MKV use H.264 + AAC; AVI uses MPEG-4 Part 2 + MP3; WebM uses VP9 + Opus. Extra tracks, subtitles, chapters and source metadata are not retained. Odd frame dimensions are padded to even values. HDR-specific tone mapping is not implemented.

Examples: MOV → MP4, MP4 → MOV, MKV → WebM, AVI → MP4, WAV → FLAC, JPG → PNG. Video → audio requires an audio track. Audio → video, image → video and PDF → image are not implemented. Animated and multipage images are excluded.

For video conversion without the AI chat interface, use:

```bat
python video_converter.py "C:\Videos\input.mkv" "C:\Videos\output.mp4"
```

## Commands

| Command | Effect |
| --- | --- |
| `/clear` | Clears conversation history; retains the selected item and cached content |
| `/refresh` | Clears cached content/history; the next question rereads the selection |
| `/exit` | Closes the conversation |

## Current limits

| Operation | Default limit |
| --- | --- |
| General file/audio readers and audio conversion inputs | Up to 256 MiB. |
| Image/PDF readers and image conversion inputs | Up to 25 MiB. |
| Still images | One frame; up to 12 million pixels. |
| Audio conversion/transcription | Up to 10 minutes; longer audio is rejected rather than silently shortened. |
| Image/audio conversion output | Below 128 MiB; these converters require a conservative 384 MiB of free output-drive space. |
| Speech temporary workspace | At least 256 MiB free in the project's workspace. |
| Video conversion | Separate pipeline: no configured 256 MiB input, 128 MiB output or 10-minute duration cap. Limited by available resources and a one-hour conversion timeout. |
| PDF questions | Up to 5 pages and 12,000 extracted characters per read; the final file-chat prompt uses at most 6,000 content characters. |
| Folder questions | Up to 50 immediate entries; contents are not recursively read. |
| Reader/image/audio conversion processes | Typically 120-second timeout; speech worker: 900 seconds. First downloads count toward the relevant timeout. |
| Chat history | Last four messages, usually two question to answer exchanges. |

Most limits are configured in `config.py`; the video timeout is `VIDEO_TIMEOUT` in `video_converter.py`. Some messages use the current default limits. Converting a long video does not make its full audio eligible for transcription: the transcription limits still apply.

**Not currently implemented:** animated/multipage image conversion, SVG/HEIC conversion, image generation/editing, video visual understanding, PDF-to-image conversion, recursive folder analysis, or batch selection.

## Privacy and file access

The explicit AI requests in the application go to local Ollama at `127.0.0.1:11434`. Packages and models require internet downloads; normal inference can run locally after the required models are cached. Launched applications can have their own network behavior.

Choosing a file controls what the application normally processes. It does **not** create a per-file Windows permission sandbox: Python, decoders and launched applications retain your account's permissions.

The app validates AI-selected actions, asks for confirmation before launching, blocks ordinary executable/script/shortcut opening, restricts media decoding, and avoids overwriting existing outputs. These protections do not guarantee that untrusted files or dependencies are safe. Do not run AskAI as administrator.

The application does not write a permanent conversation archive. It keeps recent messages and selected-file content in memory; some reader results and decoded media are written to temporary files during processing. Those files are normally cleaned up, as described in the storage section. Closing the session discards its Python-held conversation history. Sending requests to the local model does not train it or create another downloaded model copy.

File paths and answers can remain visible in terminal scrollback. Windows paging, external logging tools and Ollama's own logs have separate behavior; this is not a guarantee that no traces can exist on disk. Launched applications manage their own files, history and permissions.

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
| `video_converter.py` | Video encoder discovery and conversion between MP4, MOV, MKV, AVI and WebM |
| `app_launcher.py` / `setup_context_menu.py` | Confirmed application launching / Windows menu registration |
| `file_chat.py` and reader modules | File inspection, text/PDF extraction, OCR and transcription |
| `image_chat.py` / `image_reader.py` | OCR/vision question answering |
| `ollama_client.py` | Shared local AI HTTP client |
| `safety.py` / `reader_worker.py` / `config.py` | Validation, stoppable reader processes and settings |

Model backends: Qwen3 through Ollama, Moondream through Ollama, [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and RapidOCR. Conversion uses Pillow and FFmpeg through imageio-ffmpeg.

## Project status

AskAI works as a local Windows assistant that connects a selected file or folder to Python tools and locally running AI models. It supports file questions, image/audio/video conversion and confirmed application launching through a terminal opened from the right-click menu.

The project is a working development prototype, not a packaged desktop release. Compatibility and performance depend on the computer, installed dependencies, model versions and media codecs; not every configuration has been tested. AI answers should be checked against the source, and the project does not claim security certification or guaranteed accuracy.

