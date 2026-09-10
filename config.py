"""Adjust these settings deliberately; never take them from model output."""
import os
from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent
MODEL_ROOT = Path(os.environ.get('ASKAI_MODEL_ROOT', r'D:\AskAIModels'))
WORK_DIR = PROJECT_DIR / '.work'
TEXT_MODEL = 'qwen3:1.7b'
VISION_MODEL = 'moondream'
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
MAX_AUDIO_SECONDS = 600
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
READER_TIMEOUT = 120
SPEECH_TIMEOUT = 900
MAX_RESPONSE_BYTES = 2 * 1024 * 1024