from pathlib import Path
from zipfile import BadZipFile, ZipFile

from app.core.config import settings


def validate_office_package(path: Path, required_member: str) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    content = path.read_bytes()
    if not content:
        raise ValueError(f"Office file is empty: {path.name}")
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > settings.office_max_archive_entries:
                raise ValueError("Office archive contains too many entries")
            expanded = sum(member.file_size for member in members)
            if expanded > settings.office_max_archive_uncompressed_bytes:
                raise ValueError("Office archive expands beyond the configured limit")
            if required_member not in archive.namelist():
                raise ValueError(f"Malformed Office document: {path.name}")
            if any("vbaProject.bin" in member.filename for member in members):
                raise ValueError("Macro-enabled Office documents are not supported")
    except BadZipFile as exc:
        raise ValueError(f"Malformed Office document: {path.name}") from exc
    return content


def enforce_text_limit(current: int, added: str) -> int:
    total = current + len(added)
    if total > settings.office_max_extracted_chars:
        raise ValueError("Extracted Office document text exceeds the configured limit")
    return total
