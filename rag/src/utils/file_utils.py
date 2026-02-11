import os
import shutil
import tempfile
from pathlib import Path

def ensure_directory(path: str):
    """Ensure directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)

def cleanup_directory(path: str):
    """Remove directory and contents"""
    if os.path.exists(path):
        shutil.rmtree(path)

def create_temp_dir(prefix: str = "rag_") -> str:
    """Create temporary directory"""
    return tempfile.mkdtemp(prefix=prefix)
