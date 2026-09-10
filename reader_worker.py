"""Run expensive readers in a stoppable process. This is NOT a sandbox."""
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from config import WORK_DIR, READER_TIMEOUT, MAX_RESPONSE_BYTES

TASKS = {
    'pdf': ('pdf_reader', '_read_pdf'),
    'image': ('image_reader', '_prepare_image'),
    'ocr': ('ocr_reader', '_read_image_text'),
    'speech': ('audio_reader', '_transcribe_wav'),
}

def run_reader(task, args, kwargs=None, timeout=READER_TIMEOUT):
    if task not in TASKS:
        raise ValueError('Unknown reader.')
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='reader-', dir=WORK_DIR) as folder:
        result_path = Path(folder) / 'result.json'
        payload = json.dumps({'task': task, 'args': args, 'kwargs': kwargs or {}})
        try:
            process = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), str(result_path)],
                input=payload, text=True, encoding='utf-8',
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired as error:
            raise ValueError(f'Reader stopped after {timeout} seconds. Try a smaller file.') from error
        if process.returncode or not result_path.is_file():
            raise ValueError('Reader process failed. Check dependencies and available memory.')
        if result_path.stat().st_size > MAX_RESPONSE_BYTES:
            raise ValueError('Reader output exceeded its size limit.')
        result = json.loads(result_path.read_text(encoding='utf-8'))
        if 'error' in result:
            raise ValueError(result['error'])
        return result['result']

def main():
    destination = Path(sys.argv[1])
    try:
        request = json.loads(sys.stdin.read(65536))
        module, name = TASKS[request['task']]
        function = getattr(importlib.import_module(module), name)
        value = function(*request['args'], **request['kwargs'])
        result = {'result': value}
        encoded = json.dumps(result, ensure_ascii=False)
        if len(encoded.encode('utf-8')) > MAX_RESPONSE_BYTES:
            raise ValueError('Reader result exceeded the output limit.')
    except Exception as error:
        encoded = json.dumps({'error': f'{type(error).__name__}: {str(error)[:800]}'})
    destination.write_text(encoded, encoding='utf-8')

if __name__ == '__main__':
    main()