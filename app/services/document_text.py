"""Read the words printed on an uploaded document photo. This is not a PSA check."""

import subprocess
import tempfile
from pathlib import Path

_SOURCE = Path(__file__).with_name("read_document_text.swift")
_BINARY = Path(__file__).resolve().parents[2] / "instance" / "bin" / "read_document_text"


def _reader():
    binary = _BINARY
    binary.parent.mkdir(parents=True, exist_ok=True)
    if not binary.exists() or _SOURCE.stat().st_mtime > binary.stat().st_mtime:
        compiled = subprocess.run(
            ["swiftc", "-O", "-o", str(binary), str(_SOURCE)],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if compiled.returncode != 0 or not binary.exists():
            return None
    return binary


def read_document_text(payload, extension):
    """Return the words visible in a PDF or image, or an error message."""
    reader = _reader()
    if reader is None:
        return "", "The document photo could not be checked on this computer. Try again."
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as handle:
            handle.write(payload)
            temp_path = handle.name
        result = subprocess.run(
            [str(reader), temp_path],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "", "The document photo could not be checked. Upload it again."
    finally:
        if temp_path is not None:
            Path(temp_path).unlink(missing_ok=True)
    if result.returncode != 0:
        return "", (
            "The words on this photo could not be read. Upload a clearer, straight photo "
            "or PDF of the full document, with its title visible."
        )
    return result.stdout or "", None
