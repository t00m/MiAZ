
import pathlib

from MiAZ.backend.extract import extract as _core_extract, ExtractResult

# Re-exported for callers that only need the type.
__all__ = ['ExtractResult', 'extract']


def extract(path: pathlib.Path) -> ExtractResult:
    """Local text extraction: the core formats (pdftotext/tesseract/plain,
    MiAZ.backend.extract) plus .docx via python-docx, which stays plugin-only
    since it is not a core dependency. Caller checks is_useful and may fall
    back to provider file-upload when False."""
    path = pathlib.Path(path)
    if path.suffix.lower() == '.docx':
        return ExtractResult(_docx(path), 'python-docx')
    return _core_extract(path)


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
