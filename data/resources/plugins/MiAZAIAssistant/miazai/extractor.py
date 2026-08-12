
import pathlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Literal

ExtractMethod = Literal['pdftotext', 'tesseract', 'python-docx', 'plain', 'none']

_MIN_USEFUL_CHARS = 200


@dataclass
class ExtractResult:
    text: str
    method: ExtractMethod

    @property
    def is_useful(self) -> bool:
        return (
            self.method != 'none'
            and len(self.text) >= _MIN_USEFUL_CHARS
            and any(c.isalpha() for c in self.text)
        )


def extract(path: pathlib.Path) -> ExtractResult:
    """Try local text extraction. Caller checks is_useful and may fall
    back to provider file-upload when False."""
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        text = _pdftotext(path)
        if text and len(text) >= _MIN_USEFUL_CHARS:
            return ExtractResult(text, 'pdftotext')
        text = _ocr_pdf(path)
        return ExtractResult(text, 'tesseract' if text else 'none')
    if suffix == '.docx':
        return ExtractResult(_docx(path), 'python-docx')
    if suffix in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.webp'}:
        return ExtractResult(_ocr_image(path), 'tesseract')
    if suffix in {'.txt', '.md', '.markdown'}:
        try:
            return ExtractResult(path.read_text(errors='replace'), 'plain')
        except Exception:
            return ExtractResult('', 'none')
    return ExtractResult('', 'none')


def _pdftotext(path: pathlib.Path) -> str:
    if not shutil.which('pdftotext'):
        return ''
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', '-q', str(path), '-'],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return result.stdout
    except Exception:
        return ''


def _docx(path: pathlib.Path) -> str:
    try:
        import docx
    except ImportError:
        return ''
    try:
        doc = docx.Document(str(path))
        return '\n'.join(p.text for p in doc.paragraphs)
    except Exception:
        return ''


def _ocr_image(path: pathlib.Path) -> str:
    if not shutil.which('tesseract'):
        return ''
    try:
        result = subprocess.run(
            ['tesseract', str(path), '-', '-l', 'eng'],
            capture_output=True, text=True, timeout=60, check=False,
        )
        return result.stdout
    except Exception:
        return ''


def _ocr_pdf(path: pathlib.Path) -> str:
    if not (shutil.which('pdftoppm') and shutil.which('tesseract')):
        return ''
    with tempfile.TemporaryDirectory() as td:
        out_prefix = pathlib.Path(td) / 'page'
        try:
            subprocess.run(
                ['pdftoppm', '-r', '200', str(path), str(out_prefix)],
                timeout=60, check=False,
            )
        except Exception:
            return ''
        pages = sorted(pathlib.Path(td).glob('page-*.ppm'))
        chunks = [_ocr_image(img) for img in pages[:10]]
        return '\n'.join(chunks)
