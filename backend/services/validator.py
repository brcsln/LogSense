from pathlib import Path

ALLOWED_EXTENSIONS = {".log", ".txt"}


def validate_file(filename: str):
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        return False, "Please upload a .log or .txt file."

    return True, None