import hashlib
import re
from pathlib import Path

def compute_sha256(file_path: str | Path) -> str:
    """
    Computes the SHA256 hash of a file efficiently using chunks.
    """
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()

def clean_name(s: str) -> str:
    """
    Sanitizes common string identifiers for filesystem use, 
    keeping Vietnamese characters but removing illegal filename characters.
    """
    # Replace slashes with underscores to avoid directory traversal/errors
    s = s.replace("/", "_").replace("\\", "_")
    # Remove characters that are generally illegal in filenames across major OSs
    return re.sub(r'[<>:"|?*]', '', s).strip()
