"""Shared bounded image decoding for OCR and vision."""
import warnings
from PIL import Image, ImageOps
from config import MAX_DOCUMENT_BYTES, MAX_IMAGE_PIXELS
from safety import selected_file

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tif', '.tiff', '.gif'}

def load_image(selected_path, thumbnail=None):
    path = selected_file(selected_path, MAX_DOCUMENT_BYTES)
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(path) as original:
            if getattr(original, 'n_frames', 1) != 1:
                raise ValueError('Choose a single-frame image.')
            width, height = original.size
            if width * height > MAX_IMAGE_PIXELS:
                raise ValueError(f'Image exceeds the {MAX_IMAGE_PIXELS:,} pixel limit. Resize it first.')
            image = ImageOps.exif_transpose(original)
            if thumbnail:
                image.thumbnail(thumbnail)
            image = image.convert('RGBA')
            background = Image.new('RGB', image.size, 'white')
            background.paste(image, mask=image.getchannel('A'))
            return background